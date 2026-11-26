"""Chạy LogicAgent.auto_solve trên bộ puzzle trong data/ và ghi results.csv.

Chạy từ thư mục Source/:
    python experiments/run_tests.py

Tham số `--timeout` giới hạn thời gian (giây) cho từng truy vấn DPLL; mỗi bài
có thể gọi DPLL nhiều lần. Cột `status` ghi một trong năm giá trị: `SOLVED`,
`STUCK`, `INCONSISTENT`, `TIMEOUT`, `ERROR`. Khi một bài gặp lỗi hoặc hết giờ,
script ghi dòng kết quả đó rồi chạy tiếp các bài sau.

Cách đếm các cột kết quả:
- `unique`: kiểm tra bằng `uniqueness_check` trên toàn bộ clue của file JSON
  kèm `FACT` cho các ô `initially_revealed`, ghi `UNIQUE`, `MULTIPLE`, `UNSAT`
  hoặc `TIMEOUT` (hết giờ ở bước này không đổi `status`). Bước này chạy tách
  biệt, không cộng vào `sat_calls` và `runtime_sec`.
- `sat_calls`: tổng số lần `LogicAgent` gọi `DPLLSolver.solve`, gồm truy vấn
  kiểm chứng của engine, lần kiểm tra KB cuối và truy vấn bị timeout.
- `trace_sat_calls`: tổng `len(entry.sat_queries)` qua các bước `ACCEPTED`
  trong `agent.trace`.
- `untraced_sat_calls`: `sat_calls - trace_sat_calls` (các truy vấn ngoài
  `agent.trace`: kiểm chứng của engine, lượt quét cuối khi dừng và lượt quét
  dở trước khi timeout).
- `decisions`, `propagations`, `backtracks`: cộng từ `SolverStats` (D4) qua mọi
  truy vấn trong `sat_calls`, gồm cả truy vấn kiểm chứng của engine và truy vấn
  bị timeout, không gồm `uniqueness_check` và lượt đếm `reveal_waves`:
  `decisions` là số lần chọn biến rẽ nhánh trong `_dpll`, `propagations` là số
  literal gán qua unit clause (không tính `assumptions`), `backtracks` là số
  nhánh trả `UNSAT`.
- `primary_vars`, `aux_vars`, `clauses`: đếm bằng `Encoder.build_kb` trên
  `PublicKB` lúc dừng (lượt quét cuối, hoặc lúc timeout/lỗi); để trống nếu
  chưa có engine hoặc `build_kb` lỗi.
- `reveal_waves`: số lượt gom và nộp toàn bộ ô bị ép từ `PublicKB` hiện tại
  trong một lượt chạy riêng bằng `LogicAgent.classify`; không cộng vào
  `sat_calls`, các bộ đếm DPLL hay `runtime_sec`, và để trống khi truyền sẵn
  `engine` hoặc chưa nạp được file.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Sequence

SOURCE_DIR = Path(__file__).resolve().parent.parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from engine import board  # noqa: E402
from engine.character import parse_character  # noqa: E402
from engine.clue import Clue  # noqa: E402
from engine.constants import (  # noqa: E402
    ACCEPTED,
    CRIMINAL,
    INCONSISTENT,
    INNOCENT,
    UNKNOWN,
)
from engine.game_state import GameEngine  # noqa: E402
from logic.agent import (  # noqa: E402
    LogicAgent,
    RevealEngine,
    TIMEOUT,
    UNSAT,
    uniqueness_check,
)
from logic.cnf_encoder import Encoder  # noqa: E402

DEFAULT_DATA_DIR = SOURCE_DIR / "data"
DEFAULT_OUT_PATH = SOURCE_DIR / "experiments" / "results.csv"
DEFAULT_TIMEOUT = 30.0
ERROR = "ERROR"
UNIQUE, MULTIPLE = "UNIQUE", "MULTIPLE"

FIELDNAMES = (
    "puzzle",
    "size",
    "status",
    "unique",
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


def _puzzle_clues(path: Path) -> tuple[list[Clue], int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    n = data["n"]
    revealed = set(data["initially_revealed"])
    clues: list[Clue] = []
    for item in data["characters"]:
        char, is_criminal, clue = parse_character(item, n)
        clues.append(clue)
        if char.cell in revealed:
            clues.append(Clue(
                id=f"init_{char.cell}",
                owner=char.cell,
                type="FACT",
                params={
                    "target": char.cell,
                    "status": CRIMINAL if is_criminal else INNOCENT,
                },
            ))
    return clues, n


def _log_error(puzzle_name: str, exc: Exception, stage: str = "") -> None:
    detail = f": {exc}" if str(exc) else ""
    suffix = f" ({stage})" if stage else ""
    print(f"ERROR {puzzle_name}{suffix}: {type(exc).__name__}{detail}", file=sys.stderr)


def _check_uniqueness(path: Path, timeout: float | None) -> str:
    try:
        clues, n = _puzzle_clues(path)
        is_unique, count = uniqueness_check(clues, n, timeout=timeout)
    except TimeoutError:
        return TIMEOUT
    except Exception as exc:
        _log_error(f"{path.parent.name}/{path.name}", exc, "unique")
        return ERROR
    if is_unique:
        return UNIQUE
    return UNSAT if count == 0 else MULTIPLE


def _count_reveal_waves(path: Path, timeout: float | None) -> int | str:
    """Đếm số wave lật thẻ qua một lượt chạy riêng bằng `LogicAgent.classify`.

    Mỗi wave gom mọi ô chưa chứng minh đã bị KB hiện tại ép trạng thái, rồi nộp
    hết qua `submit_verdict` để mở clue cho wave sau. Hàm tự tạo `GameEngine` và
    `LogicAgent` riêng nên không cộng vào bộ đếm của `run_one`; trả `TIMEOUT` khi
    quá giờ hoặc `ERROR` khi gặp lỗi.
    """
    try:
        engine = GameEngine()
        engine.load_puzzle(path)
        agent = LogicAgent(timeout=timeout)
        waves = 0
        while True:
            public_kb = engine.get_public_kb()
            forced: list[tuple[str, str]] = []
            for cell in board.all_cells(public_kb.n):
                if cell in public_kb.proved:
                    continue
                verdict = agent.classify(public_kb, cell)
                if verdict == INCONSISTENT:
                    return waves
                if verdict in (CRIMINAL, INNOCENT):
                    forced.append((cell, verdict))
                elif verdict != UNKNOWN:
                    raise RuntimeError(f"classify trả trạng thái không hợp lệ: {verdict!r}")
            if not forced:
                return waves
            for cell, verdict in forced:
                if engine.submit_verdict(cell, verdict, agent.classify) != ACCEPTED:
                    raise RuntimeError(
                        f"Engine từ chối verdict đã chứng minh: {cell} {verdict}"
                    )
            waves += 1
    except TimeoutError:
        return TIMEOUT
    except Exception as exc:
        _log_error(f"{path.parent.name}/{path.name}", exc, "waves")
        return ERROR


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
    check_unique = False
    size: int | str = ""
    status = ERROR
    start = time.perf_counter()
    try:
        if engine is None:
            loaded = GameEngine()
            loaded.load_puzzle(puzzle_path)
            engine = loaded
            check_unique = True
        size = engine.get_public_kb().n
        agent.auto_solve(engine)
        status = agent.solve_status or ""
    except TimeoutError:
        status = agent.solve_status or TIMEOUT
    except Exception as exc:
        _log_error(puzzle_name, exc)
    runtime_sec = round(time.perf_counter() - start, 6)

    primary_vars: int | str = ""
    aux_vars: int | str = ""
    clauses: int | str = ""
    if engine is not None:
        try:
            public_kb = engine.get_public_kb()
            kb = Encoder(public_kb.n).build_kb(public_kb)
            primary_vars = kb.num_primary
            aux_vars = kb.num_aux
            clauses = kb.num_clauses
        except Exception as exc:
            _log_error(puzzle_name, exc, "kb")

    unique = _check_uniqueness(puzzle_path, timeout) if check_unique else ""
    reveal_waves = _count_reveal_waves(puzzle_path, timeout) if check_unique else ""
    trace_sat_calls = sum(len(entry.sat_queries) for entry in agent.trace)
    return {
        "puzzle": puzzle_name,
        "size": size,
        "status": status,
        "unique": unique,
        "primary_vars": primary_vars,
        "aux_vars": aux_vars,
        "clauses": clauses,
        "sat_calls": agent.sat_calls,
        "trace_sat_calls": trace_sat_calls,
        "untraced_sat_calls": agent.sat_calls - trace_sat_calls,
        "decisions": agent.total_decisions,
        "propagations": agent.total_propagations,
        "backtracks": agent.total_backtracks,
        "deduction_steps": len(agent.trace),
        "reveal_waves": reveal_waves,
        "runtime_sec": runtime_sec,
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
                f"{row['puzzle']} | {row['status']} | unique={row['unique'] or '-'} | "
                f"steps={row['deduction_steps']} sat={row['sat_calls']} "
                f"time={row['runtime_sec']:.3f}s"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
