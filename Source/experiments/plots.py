"""Tổng hợp bảng và biểu đồ thực nghiệm từ các file CSV do run_tests.py tạo ra.

Chạy từ thư mục Source/:
    python experiments/plots.py
    python experiments/plots.py --tables
    python experiments/plots.py --figures --image-dir ../docs/image
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from statistics import fmean, median
from typing import Any, Sequence

EXPERIMENTS_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_PATHS = tuple(EXPERIMENTS_DIR / "runs" / f"run_{i}.csv" for i in range(1, 6))
DEFAULT_DEMO_PATH = EXPERIMENTS_DIR / "results_demo.csv"
DEFAULT_IMAGE_DIR = EXPERIMENTS_DIR.parent.parent / "docs" / "image"

SOLVED = "SOLVED"

SIZE_COLORS = {
    3: "#0072B2",
    4: "#009E73",
    5: "#D55E00",
}
SIZE_MARKERS = {
    3: "o",
    4: "s",
    5: "^",
}
FIGURE_NAMES = (
    "runtime_vs_clauses.png",
    "sat_calls.png",
    "dpll_counters.png",
)

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
SUMMARY_COLUMNS = ("size", "status", *COUNT_COLS, "runtime_median_mean")
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


def _format_count_mean(value: float) -> str:
    rounded = round(value, 1)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.1f}"


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
            if mean_val == "":
                row[col] = ""
            else:
                assert isinstance(mean_val, (int, float))
                mean_str = _format_count_mean(float(mean_val))
                row[col] = f"{mean_str} ({g[f'{col}_min']}-{g[f'{col}_max']})"
        rt_mean = g["runtime_mean"]
        row["runtime_median_mean"] = (
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


def _short_puzzle_name(puzzle: object) -> str:
    return str(puzzle).removeprefix("puzzles_").removesuffix(".json")


def _style_axes(ax: Any, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, axis=grid_axis, which="major", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)


def _runtime_bounds(row: dict[str, object]) -> tuple[float, float, float] | None:
    rt = row["runtime_median"] if "runtime_median" in row else row.get("runtime_sec", "")
    if rt == "":
        return None
    rt_val = float(rt)
    lo = float(row["runtime_min"]) if row.get("runtime_min", "") != "" else rt_val
    hi = float(row["runtime_max"]) if row.get("runtime_max", "") != "" else rt_val
    return rt_val, max(0.0, rt_val - lo), max(0.0, hi - rt_val)


def _annotate_scatter(ax: Any, points: Sequence[tuple[int, float, str]]) -> None:
    ordered = sorted(points, key=lambda p: (p[0], p[1]))
    for idx, (x, y, label) in enumerate(ordered):
        dy = 6 if idx % 2 == 0 else -11
        dx, ha = (-5, "right") if len(ordered) > 1 and idx == len(ordered) - 1 else (5, "left")
        ax.annotate(label, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8)


def _plot_runtime_vs_clauses(
    plt: Any,
    ticker: Any,
    rows: Sequence[dict[str, object]],
    out_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.8), constrained_layout=True)
    sizes = sorted({int(r["size"]) for r in rows if isinstance(r.get("size"), int)})
    all_points: list[tuple[int, float, str]] = []
    for size in sizes:
        pts = [r for r in rows if r.get("size") == size and r.get("clauses", "") != ""]
        xs, ys, err_lo, err_hi = [], [], [], []
        for r in pts:
            bounds = _runtime_bounds(r)
            if bounds is None or bounds[0] <= 0:
                continue
            x_val = int(r["clauses"])
            xs.append(x_val)
            ys.append(bounds[0])
            err_lo.append(bounds[1])
            err_hi.append(bounds[2])
            all_points.append((x_val, bounds[0], _short_puzzle_name(r["puzzle"]).split("/")[-1]))
        if not xs:
            continue
        ax.errorbar(
            xs, ys, yerr=[err_lo, err_hi], fmt=SIZE_MARKERS.get(size, "o"),
            color=SIZE_COLORS.get(size, "#555555"), capsize=3, markersize=6,
            linewidth=1.2, label=f"{size}×{size}",
        )

    _annotate_scatter(ax, all_points)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_title("Thời gian chạy theo số mệnh đề CNF")
    ax.set_xlabel("Số mệnh đề CNF (clauses)")
    ax.set_ylabel("Thời gian chạy trung vị (giây, thang log)")
    ax.legend(title="Kích thước (thanh lỗi: min-max)", frameon=True)
    _style_axes(ax, grid_axis="both")
    fig.savefig(out_path, dpi=150, facecolor="white")
    plt.close(fig)


def _plot_sat_calls(
    plt: Any,
    patch_cls: Any,
    rows: Sequence[dict[str, object]],
    out_path: Path,
) -> None:
    valid = [
        r for r in rows
        if r.get("trace_sat_calls", "") != "" and r.get("untraced_sat_calls", "") != ""
    ]
    labels = [_short_puzzle_name(r["puzzle"]) for r in valid]
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    max_total = 0
    for idx, row in enumerate(valid):
        color = SIZE_COLORS.get(int(row["size"]) if isinstance(row.get("size"), int) else 0, "#555")
        traced = int(row["trace_sat_calls"])
        untraced = int(row["untraced_sat_calls"])
        total = traced + untraced
        max_total = max(max_total, total)
        ax.bar(idx, traced, width=0.64, color=color, alpha=0.9, edgecolor=color)
        ax.bar(
            idx, untraced, bottom=traced, width=0.64, color=color,
            alpha=0.28, edgecolor=color, hatch="///",
        )
        ax.text(idx, total + 6, str(total), ha="center", va="bottom", fontsize=8)

    ax.set_xticks(range(len(labels)), labels, rotation=25, ha="right")
    ax.set_ylim(0, max_total * 1.14 if max_total else 1)
    ax.set_title("Số lần gọi SAT trong và ngoài trace theo từng bài")
    ax.set_xlabel("Bài toán")
    ax.set_ylabel("Số lần gọi DPLL (lần)")
    handles = [patch_cls(facecolor=c, label=f"{s}×{s}") for s, c in SIZE_COLORS.items()]
    handles.extend([
        patch_cls(facecolor="#666666", alpha=0.9, label="Trong trace (trace_sat_calls)"),
        patch_cls(facecolor="#666666", alpha=0.28, edgecolor="#444444", hatch="///",
                  label="Ngoài trace (untraced_sat_calls)"),
    ])
    ax.legend(handles=handles, frameon=True, loc="upper left", fontsize=8.5)
    _style_axes(ax, grid_axis="y")
    fig.savefig(out_path, dpi=150, facecolor="white")
    plt.close(fig)


def _plot_dpll_counters(
    plt: Any,
    patch_cls: Any,
    rows: Sequence[dict[str, object]],
    out_path: Path,
) -> None:
    panels = (
        ("decisions", "Rẽ nhánh (decisions)"),
        ("propagations", "Lan truyền đơn vị (propagations)"),
        ("backtracks", "Quay lui (backtracks)"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), constrained_layout=True, sharex=True)
    labels = [_short_puzzle_name(r["puzzle"]) for r in rows]
    colors = [
        SIZE_COLORS.get(int(r["size"]) if isinstance(r.get("size"), int) else 0, "#555555")
        for r in rows
    ]
    for ax, (col, title) in zip(axes, panels):
        raw_vals = [r.get(col, "") for r in rows]
        num_vals = [int(v) for v in raw_vals if v != ""]
        top = max(num_vals) if num_vals else 1
        ax.set_yscale("symlog", linthresh=1)
        ax.set_ylim(0, max(top * 2.4, 10))
        for idx, (raw, color) in enumerate(zip(raw_vals, colors)):
            if raw == "":
                ax.text(idx, 0.12, "—", ha="center", va="bottom", fontsize=8, color="#777777")
                continue
            val = int(raw)
            ax.bar(idx, val, width=0.66, color=color, alpha=0.9)
            if val == 0:
                ax.text(idx, 0.12, "0", ha="center", va="bottom", fontsize=7.5, color="#444444")
        ax.set_title(title)
        ax.set_xticks(range(len(labels)), labels, rotation=35, ha="right", fontsize=8)
        _style_axes(ax, grid_axis="y")

    axes[0].set_ylabel("Số lần (thang symlog)")
    handles = [patch_cls(facecolor=c, label=f"{s}×{s}") for s, c in SIZE_COLORS.items()]
    axes[0].legend(handles=handles, loc="upper left", ncol=3, frameon=True, fontsize=8.5)
    fig.suptitle("Các bộ đếm DPLL theo từng bài (thang symlog)")
    fig.savefig(out_path, dpi=150, facecolor="white")
    plt.close(fig)


def plot_all(
    rows: Sequence[dict[str, object]],
    out_dir: Path | str | None = None,
) -> list[Path]:
    """Vẽ 3 biểu đồ thực nghiệm PNG (150 dpi) bằng backend Agg của matplotlib."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    target_dir = Path(DEFAULT_IMAGE_DIR if out_dir is None else out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = [target_dir / name for name in FIGURE_NAMES]
    _plot_runtime_vs_clauses(plt, ticker, rows, paths[0])
    _plot_sat_calls(plt, mpatches.Patch, rows, paths[1])
    _plot_dpll_counters(plt, mpatches.Patch, rows, paths[2])
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy CLI in bảng tổng hợp và xuất biểu đồ thực nghiệm từ CSV."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Tổng hợp bảng và biểu đồ thực nghiệm từ CSV.")
    parser.add_argument(
        "--tables",
        action="store_true",
        help="In ra 3 bảng Markdown: chi tiết từng bài, tổng hợp theo kích thước và failure cases",
    )
    parser.add_argument(
        "--figures",
        action="store_true",
        help="Vẽ 3 biểu đồ PNG vào thư mục --image-dir",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=None,
        help="Thư mục lưu file PNG (mặc định docs/image/ ở gốc repo)",
    )
    args = parser.parse_args(argv)
    run_all = not (args.tables or args.figures)
    if args.tables or run_all:
        print(render_tables())
    if args.figures or run_all:
        saved = plot_all(merge_runs(DEFAULT_RUN_PATHS), args.image_dir)
        for path in saved:
            print(f"Đã lưu: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
