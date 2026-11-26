"""Kiểm thử cho experiments/run_tests.py: CSV, trạng thái dừng, unique và tách SAT calls."""
from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from engine.character import parse_character
from engine.constants import CRIMINAL, INNOCENT, NOT_PROVABLE
from engine.game_state import GameEngine, PublicKB
from experiments.run_tests import FIELDNAMES, _puzzle_clues, discover, main, run_one
from logic.agent import LogicAgent, uniqueness_check
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver, SolveResult, SolverStats
from tests.test_agent_loop import SnapshotEngine, ambiguous_puzzle, chain_puzzle, fact

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


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
        self.assertEqual(row["unique"], "UNIQUE")
        self.assertEqual(row["deduction_steps"], "8")
        sat_calls = int(row["sat_calls"])
        trace_calls = int(row["trace_sat_calls"])
        untraced_calls = int(row["untraced_sat_calls"])
        self.assertGreater(trace_calls, 0)
        self.assertGreater(untraced_calls, 0)
        self.assertEqual(sat_calls, trace_calls + untraced_calls)
        self.assertGreaterEqual(float(row["runtime_sec"]), 0.0)
        self.assertEqual(row["primary_vars"], "9")
        self.assertEqual(row["aux_vars"], "0")
        self.assertEqual(row["clauses"], "18")
        self.assertEqual(row["reveal_waves"], "8")

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
            self.assertEqual(row["unique"], "TIMEOUT")
            self.assertEqual(row["primary_vars"], "9")
            self.assertEqual(row["aux_vars"], "0")
            self.assertEqual(row["clauses"], "2")
            self.assertEqual(row["deduction_steps"], "0")
            self.assertEqual(row["reveal_waves"], "TIMEOUT")
            self.assertEqual(row["sat_calls"], "1")
            self.assertEqual(row["trace_sat_calls"], "0")
            self.assertEqual(row["untraced_sat_calls"], "1")

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
        self.assertEqual(row["primary_vars"], 9)
        self.assertEqual(row["aux_vars"], 0)
        self.assertEqual(row["clauses"], 4)
        self.assertEqual(row["deduction_steps"], 1)
        self.assertEqual(row["reveal_waves"], "")
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
        self.assertEqual(rows[0]["primary_vars"], "9")
        self.assertEqual(rows[0]["aux_vars"], "0")
        self.assertEqual(rows[0]["clauses"], "2")
        self.assertEqual(rows[0]["deduction_steps"], "0")
        self.assertEqual(rows[0]["reveal_waves"], "0")
        self.assertGreater(int(rows[0]["sat_calls"]), 0)
        self.assertEqual(rows[0]["trace_sat_calls"], "0")
        self.assertEqual(rows[0]["untraced_sat_calls"], rows[0]["sat_calls"])

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
        self.assertEqual(rows[0]["primary_vars"], "")
        self.assertEqual(rows[0]["aux_vars"], "")
        self.assertEqual(rows[0]["clauses"], "")
        self.assertEqual(rows[0]["reveal_waves"], "")
        self.assertEqual(rows[0]["sat_calls"], "0")
        self.assertEqual(rows[1]["puzzle"], "puzzles_3x3/b_valid.json")
        self.assertEqual(rows[1]["status"], "SOLVED")
        self.assertEqual(rows[1]["primary_vars"], "9")
        self.assertEqual(rows[1]["aux_vars"], "0")
        self.assertEqual(rows[1]["clauses"], "18")
        self.assertEqual(rows[1]["reveal_waves"], "8")

    def test_inconsistent_snapshot_engine_writes_inconsistent_row(self) -> None:
        public = PublicKB(3, (fact("A1", INNOCENT),), {"A1": CRIMINAL})
        row = run_one(
            "puzzles_3x3/inconsistent.json",
            timeout=10,
            engine=SnapshotEngine(public, public),
        )
        self.assertEqual(row["status"], "INCONSISTENT")
        self.assertEqual(row["size"], 3)
        self.assertEqual(row["primary_vars"], 9)
        self.assertEqual(row["aux_vars"], 0)
        self.assertEqual(row["clauses"], 2)
        self.assertEqual(row["sat_calls"], 1)
        self.assertEqual(row["deduction_steps"], 0)
        self.assertEqual(row["reveal_waves"], "")

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
        self.assertEqual(rejected["primary_vars"], 9)
        self.assertEqual(rejected["aux_vars"], 0)
        self.assertEqual(rejected["clauses"], 1)
        self.assertEqual(rejected["reveal_waves"], "")
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
        self.assertEqual(rows[0]["primary_vars"], "9")
        self.assertEqual(rows[0]["aux_vars"], "0")
        self.assertEqual(rows[0]["clauses"], "2")
        self.assertEqual(rows[0]["reveal_waves"], "ERROR")

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
        for col in (
            "sat_calls",
            "trace_sat_calls",
            "untraced_sat_calls",
            "decisions",
            "propagations",
            "backtracks",
            "deduction_steps",
        ):
            self.assertEqual(rows[0][col], rows[1][col])

    def test_uniqueness_outcomes_and_initial_fact_inclusion(self) -> None:
        unsat_data = chain_puzzle()
        unsat_data["characters"][0]["clue"] = {
            "type": "FACT", "target": "A1", "status": INNOCENT
        }
        # Thiếu FACT cho initially_revealed (A1) thì chain_puzzle có ít nhất 2 nghiệm.
        clues_no_init = [parse_character(c, 3)[2] for c in chain_puzzle()["characters"]]
        self.assertEqual(uniqueness_check(clues_no_init, 3), (False, 2))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unique_path = _write_json(root / "puzzles_3x3/p01_unique.json", chain_puzzle())
            _write_json(root / "puzzles_3x3/p02_multi.json", ambiguous_puzzle())
            _write_json(root / "puzzles_3x3/p03_unsat.json", unsat_data)
            clues, _ = _puzzle_clues(unique_path)
            self.assertEqual(len({c.id for c in clues}), len(clues))
            self.assertIn("init_A1", [c.id for c in clues])
            out_csv = root / "results.csv"
            code, _, stderr = _run_cli(root, out_csv, "--timeout", "10")
            rows = _read_csv(out_csv)
            self.assertEqual(run_one(unique_path, timeout=10)["unique"], "UNIQUE")

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            [(r["puzzle"], r["status"], r["unique"]) for r in rows],
            [
                ("puzzles_3x3/p01_unique.json", "SOLVED", "UNIQUE"),
                ("puzzles_3x3/p02_multi.json", "STUCK", "MULTIPLE"),
                ("puzzles_3x3/p03_unsat.json", "INCONSISTENT", "UNSAT"),
            ],
        )
        for row in rows:
            self.assertEqual(
                int(row["sat_calls"]),
                int(row["trace_sat_calls"]) + int(row["untraced_sat_calls"]),
            )

    def test_uniqueness_timeout_does_not_change_solve_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            puzzle_path = _write_json(root / "puzzles_3x3/p01.json", chain_puzzle())
            with patch("experiments.run_tests.uniqueness_check", side_effect=TimeoutError):
                row = run_one(puzzle_path, timeout=10)

        self.assertEqual(row["status"], "SOLVED")
        self.assertEqual(row["unique"], "TIMEOUT")
        self.assertEqual(row["sat_calls"], row["trace_sat_calls"] + row["untraced_sat_calls"])

    def test_uniqueness_excluded_from_sat_calls_and_split_matches_trace(self) -> None:
        puzzle_path = DATA_DIR / "puzzles_3x3/p01.json"
        engine = GameEngine()
        engine.load_puzzle(puzzle_path)
        agent = LogicAgent(timeout=10)
        agent.auto_solve(engine)

        row = run_one(puzzle_path, timeout=10)
        self.assertEqual(row["status"], "SOLVED")
        self.assertEqual(row["unique"], "UNIQUE")
        self.assertEqual(row["sat_calls"], agent.sat_calls)
        self.assertEqual(row["trace_sat_calls"], 30)
        self.assertEqual(row["untraced_sat_calls"], 19)
        self.assertEqual(row["sat_calls"], row["trace_sat_calls"] + row["untraced_sat_calls"])
        self.assertEqual(row["reveal_waves"], 3)

    def test_real_p01_initial_and_final_kb_counts(self) -> None:
        puzzle_path = DATA_DIR / "puzzles_3x3/p01.json"
        solved = run_one(puzzle_path, timeout=10)
        timed_out = run_one(puzzle_path, timeout=0)

        self.assertEqual(solved["status"], "SOLVED")
        self.assertEqual(
            (solved["primary_vars"], solved["aux_vars"], solved["clauses"]),
            (9, 0, 37),
        )
        self.assertEqual(solved["reveal_waves"], 3)
        self.assertEqual(timed_out["status"], "TIMEOUT")
        self.assertEqual(
            (timed_out["primary_vars"], timed_out["aux_vars"], timed_out["clauses"]),
            (9, 0, 7),
        )
        self.assertEqual(timed_out["reveal_waves"], "TIMEOUT")

    def test_solved_puzzles_match_full_clue_kb_clauses_and_aux_vars(self) -> None:
        for folder in ("puzzles_3x3", "puzzles_4x4", "puzzles_5x5"):
            for puzzle_path in sorted((DATA_DIR / folder).glob("*.json")):
                with self.subTest(puzzle=f"{folder}/{puzzle_path.name}"):
                    row = run_one(puzzle_path, timeout=30)
                    clues, n = _puzzle_clues(puzzle_path)
                    full_kb = Encoder(n).build_kb(PublicKB(n, tuple(clues)))
                    self.assertEqual(row["status"], "SOLVED")
                    self.assertEqual(row["primary_vars"], full_kb.num_primary)
                    self.assertEqual(row["aux_vars"], full_kb.num_aux)
                    self.assertEqual(
                        row["clauses"],
                        full_kb.num_clauses + int(row["deduction_steps"]),
                    )
                    self.assertGreaterEqual(int(row["reveal_waves"]), 1)
                    self.assertLessEqual(int(row["reveal_waves"]), int(row["deduction_steps"]))

    def test_kb_count_error_leaves_columns_blank_without_changing_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            puzzle_path = _write_json(Path(tmp) / "puzzles_3x3/p01.json", chain_puzzle())
            stderr = io.StringIO()
            with patch("experiments.run_tests.Encoder", side_effect=ValueError("bad kb")):
                with redirect_stderr(stderr):
                    row = run_one(puzzle_path, timeout=10)

        self.assertEqual(row["status"], "SOLVED")
        self.assertEqual((row["primary_vars"], row["aux_vars"], row["clauses"]), ("", "", ""))
        self.assertIn("ERROR puzzles_3x3/p01.json (kb): ValueError: bad kb", stderr.getvalue())

    def test_reveal_waves_partial_stuck_inconsistent_and_pass_errors(self) -> None:
        partial_stuck = chain_puzzle()
        partial_stuck["characters"][1]["clue"] = {
            "type": "FACT", "target": "A1", "status": CRIMINAL,
        }
        unsat_data = chain_puzzle()
        unsat_data["characters"][0]["clue"] = {
            "type": "FACT", "target": "A1", "status": INNOCENT,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            partial_path = _write_json(root / "puzzles_3x3/partial.json", partial_stuck)
            unsat_path = _write_json(root / "puzzles_3x3/unsat.json", unsat_data)
            solved_path = _write_json(root / "puzzles_3x3/solved.json", chain_puzzle())

            partial_row = run_one(partial_path, timeout=10)
            unsat_row = run_one(unsat_path, timeout=10)

            self.assertEqual(partial_row["status"], "STUCK")
            self.assertEqual(partial_row["reveal_waves"], 1)
            self.assertEqual(unsat_row["status"], "INCONSISTENT")
            self.assertEqual(unsat_row["reveal_waves"], 0)

            for exc, expected, err_text in (
                (TimeoutError("wave timeout"), "TIMEOUT", ""),
                (RuntimeError("wave crash"), "ERROR", "ERROR puzzles_3x3/solved.json (waves): "),
            ):
                with self.subTest(exc=type(exc).__name__):
                    solve_agent = LogicAgent(timeout=10)
                    wave_agent = LogicAgent(timeout=10)
                    stderr = io.StringIO()
                    with patch.object(wave_agent, "classify", side_effect=exc):
                        with patch(
                            "experiments.run_tests.LogicAgent",
                            side_effect=[solve_agent, wave_agent],
                        ):
                            with redirect_stderr(stderr):
                                row = run_one(solved_path, timeout=10)
                    self.assertEqual(row["status"], "SOLVED")
                    self.assertEqual(row["reveal_waves"], expected)
                    self.assertEqual(row["sat_calls"], solve_agent.sat_calls)
                    self.assertIn(err_text, stderr.getvalue())

    def test_dpll_counters_match_solver_stats_and_exclude_extra_passes(self) -> None:
        cases = (
            ("puzzles_3x3/p02.json", False),
            ("puzzles_4x4/p03.json", True),
        )
        for rel_path, expect_backtracks in cases:
            with self.subTest(puzzle=rel_path):
                puzzle_path = DATA_DIR / rel_path
                engine = GameEngine()
                engine.load_puzzle(puzzle_path)
                agent = LogicAgent(timeout=10)
                agent.auto_solve(engine)

                row = run_one(puzzle_path, timeout=10)
                self.assertGreater(row["decisions"], 0)
                self.assertGreater(row["propagations"], 0)
                if expect_backtracks:
                    self.assertGreater(row["backtracks"], 0)
                self.assertEqual(len(agent.sat_queries), row["sat_calls"])
                self.assertEqual(
                    row["decisions"],
                    sum(q.stats.decisions for q in agent.sat_queries),
                )
                self.assertEqual(
                    row["propagations"],
                    sum(q.stats.propagations for q in agent.sat_queries),
                )
                self.assertEqual(
                    row["backtracks"],
                    sum(q.stats.backtracks for q in agent.sat_queries),
                )


if __name__ == "__main__":
    unittest.main()
