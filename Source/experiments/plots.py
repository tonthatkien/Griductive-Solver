"""Tổng hợp bảng thực nghiệm từ các file CSV do run_tests.py tạo ra.

Chạy từ thư mục Source/:
    python experiments/plots.py --tables
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from statistics import fmean, median
from typing import Sequence

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_PATHS = tuple(EXPERIMENTS_DIR / "runs" / f"run_{i}.csv" for i in range(1, 6))
DEFAULT_DEMO_PATH = EXPERIMENTS_DIR / "results_demo.csv"

SOLVED = "SOLVED"

INT_COLS = frozenset({
    "size",
    "primary_vars",
    "aux_vars",
    "clauses",
    "sat_calls",
    "trace_sat_calls",
    "untraced_sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "deduction_steps",
})
FLOAT_COLS = frozenset({"runtime_sec"})

COUNT_COLS = (
    "primary_vars",
    "aux_vars",
    "clauses",
    "sat_calls",
    "trace_sat_calls",
    "untraced_sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "deduction_steps",
)

DETAIL_COLUMNS = (
    "puzzle",
    "size",
    "status",
    "unique",
    *COUNT_COLS,
    "runtime_median",
    "runtime_min",
    "runtime_max",
)
SUMMARY_COLUMNS = ("size", "status", *COUNT_COLS, "runtime_sec")
FAILURE_COLUMNS = ("puzzle", "size", "status", "unique", *COUNT_COLS, "runtime_sec")


def load_rows(path: Path | str) -> list[dict[str, object]]:
    """Đọc một file CSV kết quả, đổi cột số sang int hoặc float và giữ nguyên ô trống."""
    rows: list[dict[str, object]] = []
    with Path(path).open(encoding="utf-8", newline="") as fh:
        for raw_row in csv.DictReader(fh):
            if None in raw_row:
                raise ValueError(f"Dòng CSV thừa cột trong {path}: {raw_row[None]!r}")
            row: dict[str, object] = {}
            for key, raw_val in raw_row.items():
                value = "" if raw_val is None else raw_val
                if value == "":
                    row[key] = ""
                elif key in INT_COLS:
                    row[key] = int(value)
                elif key in FLOAT_COLS:
                    row[key] = float(value)
                else:
                    row[key] = value
            rows.append(row)
    return rows


def _index_by_puzzle(
    path: Path | str,
) -> tuple[list[dict[str, object]], dict[object, dict[str, object]]]:
    rows = load_rows(path)
    by_puzzle = {row["puzzle"]: row for row in rows}
    if len(by_puzzle) != len(rows):
        raise ValueError(f"Trùng tên bài trong {path}")
    return rows, by_puzzle


def merge_runs(run_paths: Sequence[Path | str]) -> list[dict[str, object]]:
    """Gộp nhiều lần chạy theo puzzle; báo ValueError nếu cột đếm hoặc status bị lệch."""
    if not run_paths:
        raise ValueError("Cần ít nhất một file CSV để gộp.")

    base_rows, base_index = _index_by_puzzle(run_paths[0])
    expected = set(base_index)
    lookups: list[dict[object, dict[str, object]]] = []
    for path in run_paths[1:]:
        _, by_puzzle = _index_by_puzzle(path)
        if set(by_puzzle) != expected:
            raise ValueError(f"Danh sách bài trong {path} không khớp {run_paths[0]}")
        lookups.append(by_puzzle)

    merged: list[dict[str, object]] = []
    for base in base_rows:
        puzzle = base["puzzle"]
        matched = [base]
        for path, by_puzzle in zip(run_paths[1:], lookups):
            other = by_puzzle[puzzle]
            if set(other) != set(base):
                raise ValueError(f"Bài {puzzle} khác tập cột trong {path}")
            for col in base:
                if col not in ("puzzle", "runtime_sec") and other[col] != base[col]:
                    raise ValueError(
                        f"Bài {puzzle} lệch cột {col}: {base[col]!r} != {other[col]!r}"
                    )
            matched.append(other)

        item = {k: v for k, v in base.items() if k != "runtime_sec"}
        runtimes = [float(r["runtime_sec"]) for r in matched if r.get("runtime_sec", "") != ""]
        item["runtime_median"] = median(runtimes) if runtimes else ""
        item["runtime_min"] = min(runtimes) if runtimes else ""
        item["runtime_max"] = max(runtimes) if runtimes else ""
        merged.append(item)
    return merged


def _numeric_stats(
    values: Sequence[int | float],
) -> tuple[float | str, int | float | str, int | float | str]:
    if not values:
        return "", "", ""
    return fmean(values), min(values), max(values)


def _size_sort_key(size: object) -> tuple[int, int, str]:
    if isinstance(size, int) and not isinstance(size, bool):
        return (0, size, "")
    return (1, 0, str(size))


def summary_by_size(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Nhóm các dòng theo kích thước lưới, tính trung bình và min-max bỏ qua ô trống."""
    grouped: dict[object, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(row.get("size", ""), []).append(row)

    summaries: list[dict[str, object]] = []
    for size in sorted(grouped, key=_size_sort_key):
        group = grouped[size]
        status_counts: dict[str, int] = {}
        for row in group:
            status = str(row.get("status", ""))
            status_counts[status] = status_counts.get(status, 0) + 1

        item: dict[str, object] = {
            "size": size,
            "count": len(group),
            "status_counts": status_counts,
        }
        for col in COUNT_COLS:
            vals = [row[col] for row in group if row.get(col, "") != ""]
            mean_val, min_val, max_val = _numeric_stats(vals)
            item[f"{col}_mean"] = mean_val
            item[f"{col}_min"] = min_val
            item[f"{col}_max"] = max_val

        rt_vals = [
            row["runtime_median"] if "runtime_median" in row else row.get("runtime_sec", "")
            for row in group
        ]
        rt_nums = [v for v in rt_vals if v != ""]
        item["runtime_mean"], item["runtime_min"], item["runtime_max"] = _numeric_stats(rt_nums)
        summaries.append(item)
    return summaries


def failure_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Lọc giữ mọi dòng có status khác SOLVED."""
    return [dict(row) for row in rows if row.get("status") != SOLVED]


def _format_cell(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value).replace("|", "\\|")


def to_markdown(rows: Sequence[dict[str, object]], columns: Sequence[str]) -> str:
    """Chuyển danh sách dòng thành bảng Markdown, làm tròn số thực đến 3 chữ số."""
    if not columns:
        return ""
    header = "| " + " | ".join(_format_cell(col) for col in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def _format_summary_rows(groups: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    formatted: list[dict[str, object]] = []
    for g in groups:
        status_counts = g["status_counts"]
        assert isinstance(status_counts, dict)
        size = g["size"]
        row: dict[str, object] = {
            "size": f"{size}x{size}" if isinstance(size, int) else size,
            "status": ", ".join(f"{k}={v}" for k, v in status_counts.items()),
        }
        for col in COUNT_COLS:
            mean_val = g[f"{col}_mean"]
            row[col] = (
                ""
                if mean_val == ""
                else f"{mean_val:.3f} ({g[f'{col}_min']}-{g[f'{col}_max']})"
            )
        rt_mean = g["runtime_mean"]
        row["runtime_sec"] = (
            ""
            if rt_mean == ""
            else f"{rt_mean:.3f} ({g['runtime_min']:.3f}-{g['runtime_max']:.3f})"
        )
        formatted.append(row)
    return formatted


def render_tables(
    run_paths: Sequence[Path | str] | None = None,
    demo_path: Path | str | None = None,
) -> str:
    """Tạo chuỗi chứa 3 bảng Markdown: chi tiết từng bài, tổng hợp theo kích thước và failure."""
    resolved_runs = DEFAULT_RUN_PATHS if run_paths is None else run_paths
    resolved_demo = DEFAULT_DEMO_PATH if demo_path is None else demo_path
    detail = merge_runs(resolved_runs)
    summary = _format_summary_rows(summary_by_size(detail))
    failures = failure_rows(load_rows(resolved_demo))
    sections = [
        ("Chi tiết từng bài (5 lần chạy)", to_markdown(detail, DETAIL_COLUMNS)),
        ("Tổng hợp theo kích thước", to_markdown(summary, SUMMARY_COLUMNS)),
        ("Failure cases", to_markdown(failures, FAILURE_COLUMNS)),
    ]
    return "\n\n".join(f"### {title}\n\n{table}" for title, table in sections)


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy CLI in các bảng tổng hợp thực nghiệm từ CSV."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Tổng hợp bảng thực nghiệm từ các file CSV.")
    parser.add_argument(
        "--tables",
        action="store_true",
        help="In ra 3 bảng Markdown: chi tiết từng bài, tổng hợp theo kích thước và failure cases",
    )
    parser.parse_args(argv)
    print(render_tables())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
