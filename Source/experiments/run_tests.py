"""Chạy LogicAgent.auto_solve trên bộ puzzle trong data/ và ghi results.csv.

Chạy từ thư mục Source/:
    python experiments/run_tests.py

Tham số `--timeout` đặt giới hạn giây cho mỗi truy vấn DPLL. Các cột chưa thu
thập (`unique`, `primary_vars`, `aux_vars`, `clauses`, `reveal_waves`) giữ giá
trị rỗng.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Sequence

SOURCE_DIR = Path(__file__).resolve().parent.parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from engine.game_state import GameEngine  # noqa: E402
from logic.agent import LogicAgent  # noqa: E402

DEFAULT_DATA_DIR = SOURCE_DIR / "data"
DEFAULT_OUT_PATH = SOURCE_DIR / "experiments" / "results.csv"
DEFAULT_TIMEOUT = 30.0

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


def run_one(path: Path | str, timeout: float | None = DEFAULT_TIMEOUT) -> dict[str, object]:
    """Giải một puzzle bằng engine và agent mới, trả về một dòng thống kê CSV."""
    puzzle_path = Path(path)
    engine = GameEngine()
    engine.load_puzzle(puzzle_path)
    agent = LogicAgent(timeout=timeout)
    start = time.perf_counter()
    agent.auto_solve(engine)
    runtime_sec = time.perf_counter() - start
    return {
        "puzzle": f"{puzzle_path.parent.name}/{puzzle_path.name}",
        "size": engine.n,
        "status": agent.solve_status or "",
        "sat_calls": agent.sat_calls,
        "decisions": agent.total_decisions,
        "propagations": agent.total_propagations,
        "backtracks": agent.total_backtracks,
        "deduction_steps": len(agent.trace),
        "runtime_sec": round(runtime_sec, 6),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy toàn bộ puzzle tìm được, ghi CSV và in tóm tắt từng bài."""
    parser = argparse.ArgumentParser(description="Chạy thực nghiệm solver trên bộ puzzle.")
    parser.add_argument(
        "--data", type=Path, default=DEFAULT_DATA_DIR, help="Thư mục chứa puzzles_*"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT_PATH, help="Đường dẫn file CSV kết quả"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Giới hạn giây cho mỗi truy vấn DPLL",
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
