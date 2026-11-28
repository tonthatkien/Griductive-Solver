"""Kiểm thử cho experiments/plots.py: đọc CSV, gộp lượt chạy, tổng hợp và bảng Markdown."""
from __future__ import annotations

import csv
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from statistics import fmean
from unittest.mock import patch

from experiments.plots import (
    DEFAULT_DEMO_PATH,
    DEFAULT_RUN_PATHS,
    FIGURE_NAMES,
    failure_rows,
    load_rows,
    main,
    merge_runs,
    plot_all,
    summary_by_size,
    to_markdown,
)
from experiments.run_tests import FIELDNAMES

EXPERIMENTS_DIR = Path(__file__).resolve().parents[1] / "experiments"
HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


def _make_row(
    puzzle: str = "puzzles_3x3/p01.json",
    size: int | str = 3,
    status: str = "SOLVED",
    unique: str = "UNIQUE",
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "puzzle": puzzle,
        "size": size,
        "status": status,
        "unique": unique,
        "primary_vars": 9,
        "aux_vars": 0,
        "clauses": 30,
        "sat_calls": 49,
        "trace_sat_calls": 30,
        "untraced_sat_calls": 19,
        "decisions": 0,
        "propagations": 271,
        "backtracks": 0,
        "deduction_steps": 7,
        "runtime_sec": 0.012,
    }
    row.update(overrides)
    return row


def _write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, restval="")
        writer.writeheader()
        writer.writerows(rows)
    return path


class PlotsCsvAndMergeTests(unittest.TestCase):
    """Kiểm tra đọc CSV, tính median/min/max runtime và bắt sai lệch giữa các lần chạy."""

    def test_load_rows_parses_numbers_and_preserves_blanks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(
                Path(tmp) / "sample.csv",
                [_make_row(status="ERROR", size="", primary_vars="", runtime_sec=0.25)],
            )
            rows = load_rows(csv_path)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["size"], "")
        self.assertEqual(row["primary_vars"], "")
        self.assertIs(type(row["clauses"]), int)
        self.assertEqual(row["clauses"], 30)
        self.assertIs(type(row["runtime_sec"]), float)
        self.assertAlmostEqual(float(row["runtime_sec"]), 0.25)

    def test_merge_runs_computes_runtime_median_min_and_max(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtimes = (0.50, 0.10, 0.90, 0.20, 0.30)
            paths = [
                _write_csv(root / f"run_{i}.csv", [_make_row(runtime_sec=rt)])
                for i, rt in enumerate(runtimes, 1)
            ]
            merged = merge_runs(paths)

        self.assertEqual(len(merged), 1)
        row = merged[0]
        self.assertAlmostEqual(float(row["runtime_median"]), 0.30)
        self.assertAlmostEqual(float(row["runtime_min"]), 0.10)
        self.assertAlmostEqual(float(row["runtime_max"]), 0.90)
        self.assertNotIn("runtime_sec", row)

    def test_merge_runs_raises_when_decisions_differ_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p1 = _write_csv(
                root / "run_1.csv",
                [_make_row(puzzle="puzzles_4x4/p01.json", size=4, decisions=358)],
            )
            p2 = _write_csv(
                root / "run_2.csv",
                [_make_row(puzzle="puzzles_4x4/p01.json", size=4, decisions=359)],
            )
            with self.assertRaises(ValueError) as ctx:
                merge_runs([p1, p2])

        msg = str(ctx.exception)
        self.assertIn("puzzles_4x4/p01.json", msg)
        self.assertIn("decisions", msg)


class PlotsSummaryFailureAndMarkdownTests(unittest.TestCase):
    """Kiểm tra tổng hợp theo kích thước, lọc failure và xuất bảng Markdown."""

    def test_summary_by_size_on_real_results_csv(self) -> None:
        rows = load_rows(EXPERIMENTS_DIR / "results.csv")
        groups = summary_by_size(rows)

        self.assertEqual([g["size"] for g in groups], [3, 4, 5])
        self.assertEqual([g["count"] for g in groups], [3, 3, 3])
        size3_clauses = [int(r["clauses"]) for r in rows if r["size"] == 3]
        self.assertAlmostEqual(float(groups[0]["clauses_mean"]), fmean(size3_clauses))
        self.assertEqual(groups[0]["status_counts"], {"SOLVED": 3})

    def test_summary_by_size_counts_timeout_with_blank_cells_without_breaking_mean(self) -> None:
        rows = [
            _make_row(puzzle="p1.json", size=4, clauses=100, decisions=10, runtime_sec=0.4),
            _make_row(puzzle="p2.json", size=4, clauses=200, decisions=20, runtime_sec=0.6),
            _make_row(
                puzzle="p3.json",
                size=4,
                status="TIMEOUT",
                unique="TIMEOUT",
                primary_vars="",
                aux_vars="",
                clauses="",
                decisions="",
                propagations="",
                backtracks="",
                deduction_steps="",
                runtime_sec="",
            ),
        ]
        groups = summary_by_size(rows)

        self.assertEqual(len(groups), 1)
        g = groups[0]
        self.assertEqual(g["count"], 3)
        self.assertEqual(g["status_counts"], {"SOLVED": 2, "TIMEOUT": 1})
        self.assertAlmostEqual(float(g["clauses_mean"]), 150.0)
        self.assertEqual((g["clauses_min"], g["clauses_max"]), (100, 200))
        self.assertAlmostEqual(float(g["decisions_mean"]), 15.0)
        self.assertAlmostEqual(float(g["runtime_mean"]), 0.5)

    def test_failure_rows_keeps_every_non_solved_row(self) -> None:
        rows = [
            _make_row(puzzle="puzzles_3x3/p01.json", status="SOLVED"),
            _make_row(puzzle="demo_cases/ambiguous.json", status="STUCK", unique="MULTIPLE"),
            _make_row(puzzle="demo_cases/inconsistent.json", status="INCONSISTENT", unique="UNSAT"),
            _make_row(puzzle="puzzles_4x4/p01.json", status="TIMEOUT", unique="TIMEOUT"),
            _make_row(puzzle="puzzles_5x5/broken.json", status="ERROR", unique=""),
        ]
        kept = failure_rows(rows)

        self.assertEqual(
            [r["puzzle"] for r in kept],
            [
                "demo_cases/ambiguous.json",
                "demo_cases/inconsistent.json",
                "puzzles_4x4/p01.json",
                "puzzles_5x5/broken.json",
            ],
        )

    def test_to_markdown_rounds_floats_to_three_decimals(self) -> None:
        md = to_markdown(
            [{"puzzle": "p01", "size": 3, "runtime_median": 0.123456, "note": ""}],
            ["puzzle", "size", "runtime_median", "note"],
        )
        lines = md.splitlines()
        self.assertEqual(lines[0], "| puzzle | size | runtime_median | note |")
        self.assertEqual(lines[1], "| --- | --- | --- | --- |")
        self.assertEqual(lines[2], "| p01 | 3 | 0.123 |  |")

    def test_cli_tables_prints_three_markdown_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run1 = _write_csv(root / "run_1.csv", [_make_row(runtime_sec=0.100)])
            run2 = _write_csv(root / "run_2.csv", [_make_row(runtime_sec=0.200)])
            demo = _write_csv(
                root / "demo.csv",
                [
                    _make_row(status="SOLVED"),
                    _make_row(
                        puzzle="demo_cases/ambiguous.json",
                        status="STUCK",
                        unique="MULTIPLE",
                        deduction_steps=0,
                    ),
                ],
            )
            stdout = io.StringIO()
            with (
                patch("experiments.plots.DEFAULT_RUN_PATHS", (run1, run2)),
                patch("experiments.plots.DEFAULT_DEMO_PATH", demo),
                patch("experiments.plots.plot_all") as mock_plot,
                redirect_stdout(stdout),
            ):
                code = main(["--tables"])

        output = stdout.getvalue()
        self.assertEqual(code, 0)
        mock_plot.assert_not_called()
        self.assertIn("### Chi tiết từng bài", output)
        self.assertIn("### Tổng hợp theo kích thước", output)
        self.assertIn("### Failure cases", output)
        self.assertIn("runtime_median_mean", output)
        self.assertIn("9 (9-9)", output)
        self.assertIn("0 (0-0)", output)
        self.assertIn("demo_cases/ambiguous.json", output)
        self.assertIn("0.150", output)

    def test_cli_without_flags_runs_both_tables_and_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run1 = _write_csv(root / "run_1.csv", [_make_row(runtime_sec=0.100)])
            demo = _write_csv(root / "demo.csv", [_make_row(status="SOLVED")])
            stdout = io.StringIO()
            with (
                patch("experiments.plots.DEFAULT_RUN_PATHS", (run1,)),
                patch("experiments.plots.DEFAULT_DEMO_PATH", demo),
                patch("experiments.plots.plot_all", return_value=[]) as mock_plot,
                redirect_stdout(stdout),
            ):
                code = main([])

        self.assertEqual(code, 0)
        self.assertIn("### Tổng hợp theo kích thước", stdout.getvalue())
        mock_plot.assert_called_once()
        self.assertIsNone(mock_plot.call_args.args[1])

    def test_cli_figures_only_passes_image_dir_and_skips_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run1 = _write_csv(root / "run_1.csv", [_make_row(runtime_sec=0.100)])
            img_dir = root / "imgs"
            fake_paths = [img_dir / name for name in FIGURE_NAMES]
            stdout = io.StringIO()
            with (
                patch("experiments.plots.DEFAULT_RUN_PATHS", (run1,)),
                patch("experiments.plots.plot_all", return_value=fake_paths) as mock_plot,
                redirect_stdout(stdout),
            ):
                code = main(["--figures", "--image-dir", str(img_dir)])

        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertNotIn("### Chi tiết từng bài", output)
        mock_plot.assert_called_once()
        self.assertEqual(mock_plot.call_args.args[1], img_dir)

    @unittest.skipUnless(HAS_MATPLOTLIB, "matplotlib chưa được cài đặt")
    def test_plot_all_writes_three_png_files(self) -> None:
        rows = merge_runs(DEFAULT_RUN_PATHS)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "figures"
            paths = plot_all(rows, out_dir)
            self.assertEqual([p.name for p in paths], list(FIGURE_NAMES))
            for path in paths:
                self.assertTrue(path.is_file(), f"Thiếu file {path}")
                raw = path.read_bytes()
                self.assertTrue(raw.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(len(raw), 1000)

    def test_cli_tables_on_repo_csvs(self) -> None:
        self.assertTrue(all(Path(p).is_file() for p in DEFAULT_RUN_PATHS))
        self.assertTrue(Path(DEFAULT_DEMO_PATH).is_file())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["--tables"])
        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("puzzles_5x5/p03.json", output)
        self.assertIn("11.7 (0-18)", output)
        self.assertIn("demo_cases/ambiguous.json", output)
        self.assertIn("demo_cases/inconsistent.json", output)


if __name__ == "__main__":
    unittest.main()
