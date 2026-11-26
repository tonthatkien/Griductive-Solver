"""Chạy LogicAgent.auto_solve trên bộ puzzle trong data/ và ghi results.csv.

Chạy từ thư mục Source/:
    python experiments/run_tests.py

Tham số `--timeout` giới hạn thời gian (giây) cho từng truy vấn DPLL; mỗi bài
có thể gọi DPLL nhiều lần. Cột `status` ghi một trong năm giá trị: `SOLVED`,
`STUCK`, `INCONSISTENT`, `TIMEOUT`, `ERROR`. Khi một bài gặp lỗi hoặc hết giờ,
script ghi dòng kết quả đó rồi chạy tiếp các bài sau. Trên dòng `TIMEOUT`,
`sat_calls` và các bộ đếm DPLL vẫn tính cả truy vấn bị timeout. Các cột chưa
thu thập (`unique`, `primary_vars`, `aux_vars`, `clauses`, `reveal_waves`) giữ
giá trị rỗng.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from pathlib import Path
from typing import Sequence

SOURCE_DIR = Path(__file__).resolve().parent.parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from engine.game_state import GameEngine  # noqa: E402
from logic.agent import LogicAgent, RevealEngine, TIMEOUT  # noqa: E402

DEFAULT_DATA_DIR = SOURCE_DIR / "data"
DEFAULT_OUT_PATH = SOURCE_DIR / "experiments" / "results.csv"
DEFAULT_TIMEOUT = 30.0
ERROR = "ERROR"

FIELDNAMES = (
    "puzzle",
    "size",
    "status",
    "unique",
    "primary_vars",
    "aux_vars",
    "clauses",
    "sat_calls",
    "decisions",
    "propagations",
    "backtracks",
    "deduction_steps",
    "reveal_waves",
    "runtime_sec",
)


def _puzzle_sort_key(path: Path) -> tuple[int, int, str, str]:
    folder = path.parent.name
    prefix = folder.removeprefix("puzzles_").split("x", 1)[0]
    if prefix.isdigit():
        return (0, int(prefix), path.name, folder)
    return (1, 0, path.name, folder)


def discover(data_dir: Path | str) -> list[Path]:
    """Trả danh sách file puzzle sắp theo kích thước rồi theo tên file."""
    paths = [p for p in Path(data_dir).glob("puzzles_*/*.json") if p.is_file()]
    return sorted(paths, key=_puzzle_sort_key)


def _parse_timeout(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"timeout phải là số >= 0, nhận {raw!r}") from exc
    if math.isnan(value) or value < 0:
        raise argparse.ArgumentTypeError(f"timeout phải >= 0, nhận {raw!r}")
    return value


def run_one(
    path: Path | str,
    timeout: float | None = DEFAULT_TIMEOUT,
    *,
    engine: RevealEngine | None = None,
) -> dict[str, object]:
    """Giải một puzzle từ file hoặc engine đã nạp, trả về một dòng thống kê CSV."""
    if timeout is not None and (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or math.isnan(timeout)
        or timeout < 0
    ):
        raise ValueError(f"timeout phải >= 0 hoặc None, nhận {timeout!r}")
    agent = LogicAgent(timeout=timeout)

    puzzle_path = Path(path)
    puzzle_name = f"{puzzle_path.parent.name}/{puzzle_path.name}"
    size: int | str = ""
    status = ERROR
    start = time.perf_counter()
    try:
        if engine is None:
            loaded = GameEngine()
            loaded.load_puzzle(puzzle_path)
            engine = loaded
        size = engine.get_public_kb().n
        agent.auto_solve(engine)
        status = agent.solve_status or ""
    except TimeoutError:
        status = agent.solve_status or TIMEOUT
    except Exception as exc:
        detail = f": {exc}" if str(exc) else ""
        print(f"ERROR {puzzle_name}: {type(exc).__name__}{detail}", file=sys.stderr)
    return {
        "puzzle": puzzle_name,
        "size": size,
        "status": status,
        "sat_calls": agent.sat_calls,
        "decisions": agent.total_decisions,
        "propagations": agent.total_propagations,
        "backtracks": agent.total_backtracks,
        "deduction_steps": len(agent.trace),
        "runtime_sec": round(time.perf_counter() - start, 6),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy toàn bộ puzzle tìm được, ghi CSV và in tóm tắt từng bài."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Chạy thực nghiệm solver trên bộ puzzle.")
    parser.add_argument(
        "--data", type=Path, default=DEFAULT_DATA_DIR, help="Thư mục chứa puzzles_*"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT_PATH, help="Đường dẫn file CSV kết quả"
    )
    parser.add_argument(
        "--timeout",
        type=_parse_timeout,
        default=DEFAULT_TIMEOUT,
        help="Giới hạn giây cho mỗi truy vấn DPLL (0 = timeout ngay)",
    )
    args = parser.parse_args(argv)
    if not args.data.is_dir():
        parser.error(f"Thư mục dữ liệu không tồn tại: {args.data}")

    paths = discover(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, restval="")
        writer.writeheader()
        for path in paths:
            row = run_one(path, args.timeout)
            writer.writerow(row)
            print(
                f"{row['puzzle']} | {row['status']} | "
                f"steps={row['deduction_steps']} sat={row['sat_calls']} "
                f"time={row['runtime_sec']:.3f}s"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
