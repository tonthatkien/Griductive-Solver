"""Deductive Logic Agent. (Scope E)

Agent CHỈ nhận PublicKB (không nhận GameEngine, không đọc nhãn ẩn).

TODO(Scope E):
  classify(public_kb, cell) -> CRIMINAL | INNOCENT | UNKNOWN | INCONSISTENT
      kb = Encoder.build_kb(public_kb)
      KB không SAT                    -> INCONSISTENT
      KB ∧ ¬Ci UNSAT                  -> CRIMINAL
      KB ∧  Ci UNSAT                  -> INNOCENT
      cả hai SAT                      -> UNKNOWN
      (ghi lại số SAT calls + stats của từng lần gọi DPLL)

  next_forced(public_kb) -> (cell, verdict) | None
      duyệt ô chưa giải theo thứ tự row-major, trả ô forced đầu tiên (deterministic)

  hint(public_kb) -> (cell, verdict, clue_ids_liên_quan) | None
      không đọc hidden solution

  auto_solve(engine) -> list[TraceEntry]
      vòng lặp: next_forced -> engine.submit_verdict -> cập nhật KB_{t+1} -> lặp
      dừng khi: solved / không còn ô forced (stuck) / INCONSISTENT

  TraceEntry: step, active_clue_ids, sat_queries (vd [("¬C_B2", "UNSAT"), ...]),
              verdict, cell, newly_revealed_clue_id

  uniqueness_check(all_clues, n) -> (is_unique, num_models_capped_at_2)
      dùng TOÀN BỘ clue của puzzle (dành cho tooling/kiểm tra puzzle,
      KHÔNG gọi từ agent lúc chơi vì sẽ đọc clue chưa lật).
      Cách: giải -> thêm blocking clause của model -> giải lại.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class TraceEntry:
    step: int
    active_clue_ids: List[str]
    sat_queries: List[tuple] = field(default_factory=list)
    cell: str = ""
    verdict: str = ""
    newly_revealed_clue_id: str = ""


class LogicAgent:
    def __init__(self):
        self.sat_calls = 0
        self.total_decisions = 0
        self.total_propagations = 0
        self.total_backtracks = 0

    def classify(self, public_kb, cell: str) -> str:
        raise NotImplementedError

    def next_forced(self, public_kb):
        raise NotImplementedError

    def hint(self, public_kb):
        raise NotImplementedError

    def auto_solve(self, engine) -> List[TraceEntry]:
        raise NotImplementedError


def uniqueness_check(all_clues, n: int):
    raise NotImplementedError
