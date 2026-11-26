"""Kiểm thử G1 cho experiments/run_tests.py: CSV, TIMEOUT, STUCK, INCONSISTENT và ERROR."""
from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from engine.constants import CRIMINAL, INNOCENT, NOT_PROVABLE
from engine.game_state import GameEngine, PublicKB
from experiments.run_tests import FIELDNAMES, discover, main, run_one
from logic.dpll import DPLLSolver, SolveResult, SolverStats
from tests.test_agent_loop import SnapshotEngine, ambiguous_puzzle, chain_puzzle, fact


def _write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _run_cli(data_dir: Path, out_csv: Path, *extra: str) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--data", str(data_dir), "--out", str(out_csv), *extra])
    return code, stdout.getvalue(), stderr.getvalue()


class RunTestsDiscoveryAndValidationTests(unittest.TestCase):
    """Kiểm tra sắp xếp puzzle và chặn tham số timeout không hợp lệ."""

    def test_discover_orders_by_size_then_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (
                "puzzles_10x10/a.json",
                "puzzles_3x3/b.json",
                "puzzles_4x4/a.json",
                "puzzles_3x3/a.json",
            ):
                _write_json(root / rel, {})
            got = [f"{p.parent.name}/{p.name}" for p in discover(root)]
        self.assertEqual(
            got,
            [
                "puzzles_3x3/a.json",
                "puzzles_3x3/b.json",
                "puzzles_4x4/a.json",
                "puzzles_10x10/a.json",
            ],
        )

    def test_negative_and_nan_timeout_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            puzzle_path = _write_json(root / "puzzles_3x3/p01.json", chain_puzzle())
            out_csv = root / "results.csv"
            for bad in ("-1", "nan"):
                with self.subTest(cli_timeout=bad):
                    stderr = io.StringIO()
                    with redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
                        main(["--data", str(root), "--out", str(out_csv), "--timeout", bad])
                    self.assertEqual(ctx.exception.code, 2)
                    self.assertIn("timeout", stderr.getvalue())
            for bad_val in (-1.0, float("nan"), True, "bad"):
                with self.subTest(api_timeout=bad_val), self.assertRaises(ValueError):
                    run_one(puzzle_path, bad_val)


class RunTestsStatusRowsTests(unittest.TestCase):
    """Kiểm tra ghi đủ các trạng thái SOLVED, TIMEOUT, STUCK, INCONSISTENT và ERROR."""

    def test_solved_puzzle_writes_expected_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/p01.json", chain_puzzle())
            out_csv = root / "out/results.csv"
            code, stdout, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("puzzles_3x3/p01.json | SOLVED", stdout)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(tuple(row.keys()), FIELDNAMES)
        self.assertEqual(row["puzzle"], "puzzles_3x3/p01.json")
        self.assertEqual(row["size"], "3")
        self.assertEqual(row["status"], "SOLVED")
        self.assertEqual(row["deduction_steps"], "8")
        self.assertGreater(int(row["sat_calls"]), 0)
        self.assertGreaterEqual(float(row["runtime_sec"]), 0.0)
        for blank in ("unique", "primary_vars", "aux_vars", "clauses", "reveal_waves"):
            self.assertEqual(row[blank], "")

    def test_timeout_zero_writes_timeout_rows_for_all_puzzles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/p01.json", chain_puzzle())
            _write_json(root / "puzzles_3x3/p02.json", chain_puzzle())
            out_csv = root / "results.csv"
            code, _, stderr = _run_cli(root, out_csv, "--timeout", "0")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual([r["puzzle"] for r in rows], [
            "puzzles_3x3/p01.json",
            "puzzles_3x3/p02.json",
        ])
        for row in rows:
            self.assertEqual(row["status"], "TIMEOUT")
            self.assertEqual(row["deduction_steps"], "0")
            self.assertEqual(row["sat_calls"], "1")

    def test_timeout_after_accepted_step_preserves_partial_progress(self) -> None:
        engine = GameEngine()
        engine.load_puzzle(chain_puzzle())
        real_submit = engine.submit_verdict
        real_solve = DPLLSolver.solve
        timed_out_now = False

        def submit_once(cell: str, verdict: str, classify) -> str:
            nonlocal timed_out_now
            res = real_submit(cell, verdict, classify)
            timed_out_now = True
            return res

        def solve_or_timeout(self, clauses, num_vars, assumptions=(), timeout=None):
            if timed_out_now:
                return SolveResult(False, None, SolverStats(), timed_out=True)
            return real_solve(self, clauses, num_vars, assumptions=assumptions, timeout=timeout)

        with patch.object(engine, "submit_verdict", side_effect=submit_once):
            with patch.object(DPLLSolver, "solve", autospec=True, side_effect=solve_or_timeout):
                row = run_one("puzzles_3x3/p01.json", timeout=10, engine=engine)

        self.assertEqual(row["status"], "TIMEOUT")
        self.assertEqual(row["deduction_steps"], 1)
        self.assertGreater(row["sat_calls"], 1)

    def test_ambiguous_puzzle_writes_stuck_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/ambig.json", ambiguous_puzzle())
            out_csv = root / "results.csv"
            code, _, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "STUCK")
        self.assertEqual(rows[0]["deduction_steps"], "0")
        self.assertGreater(int(rows[0]["sat_calls"]), 0)

    def test_broken_json_writes_error_row_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            broken = root / "puzzles_3x3/a_broken.json"
            broken.parent.mkdir(parents=True, exist_ok=True)
            broken.write_text("{not valid json", encoding="utf-8")
            _write_json(root / "puzzles_3x3/b_valid.json", chain_puzzle())
            out_csv = root / "results.csv"
            code, _, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertIn("ERROR puzzles_3x3/a_broken.json", stderr)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["puzzle"], "puzzles_3x3/a_broken.json")
        self.assertEqual(rows[0]["status"], "ERROR")
        self.assertEqual(rows[0]["size"], "")
        self.assertEqual(rows[0]["sat_calls"], "0")
        self.assertEqual(rows[1]["puzzle"], "puzzles_3x3/b_valid.json")
        self.assertEqual(rows[1]["status"], "SOLVED")

    def test_inconsistent_snapshot_engine_writes_inconsistent_row(self) -> None:
        public = PublicKB(3, (fact("A1", INNOCENT),), {"A1": CRIMINAL})
        row = run_one(
            "puzzles_3x3/inconsistent.json",
            timeout=10,
            engine=SnapshotEngine(public, public),
        )
        self.assertEqual(row["status"], "INCONSISTENT")
        self.assertEqual(row["size"], 3)
        self.assertEqual(row["sat_calls"], 1)
        self.assertEqual(row["deduction_steps"], 0)

    def test_engine_rejection_and_assertion_write_error_rows(self) -> None:
        public = PublicKB(3, (fact("A1", CRIMINAL),))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            rejected = run_one(
                "puzzles_3x3/rejected.json",
                timeout=10,
                engine=SnapshotEngine(public, public, NOT_PROVABLE),
            )
        self.assertEqual(rejected["status"], "ERROR")
        self.assertIn("ERROR puzzles_3x3/rejected.json: RuntimeError", stderr.getvalue())

        bad_data = chain_puzzle()
        bad_data["characters"][1]["criminal"] = not bad_data["characters"][1]["criminal"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/bad_label.json", bad_data)
            out_csv = root / "results.csv"
            code, _, err = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertIn("ERROR puzzles_3x3/bad_label.json: AssertionError", err)
        self.assertEqual(rows[0]["status"], "ERROR")
        self.assertEqual(rows[0]["size"], "3")

    def test_unexpected_exception_writes_error_row_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/a_crash.json", chain_puzzle())
            _write_json(root / "puzzles_3x3/b_valid.json", chain_puzzle())
            out_csv = root / "results.csv"
            real_load = GameEngine.load_puzzle

            def load_with_key_error(self, source):
                if Path(source).name == "a_crash.json":
                    raise KeyError("missing")
                return real_load(self, source)

            with patch.object(
                GameEngine, "load_puzzle", autospec=True, side_effect=load_with_key_error
            ):
                code, _, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertIn("ERROR puzzles_3x3/a_crash.json: KeyError", stderr)
        self.assertEqual([(r["puzzle"], r["status"]) for r in rows], [
            ("puzzles_3x3/a_crash.json", "ERROR"),
            ("puzzles_3x3/b_valid.json", "SOLVED"),
        ])

    def test_consecutive_puzzles_do_not_accumulate_sat_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "puzzles_3x3/p01.json", chain_puzzle())
            _write_json(root / "puzzles_3x3/p02.json", chain_puzzle())
            out_csv = root / "results.csv"
            code, _, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(len(rows), 2)
        for col in ("sat_calls", "decisions", "propagations", "backtracks", "deduction_steps"):
            self.assertEqual(rows[0][col], rows[1][col])


if __name__ == "__main__":
    unittest.main()
