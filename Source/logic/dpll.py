"""DPLL SAT solver. (Scope D)

Giao diện (giữ nguyên chữ ký để Scope C/D/E ghép được):

    solver = DPLLSolver()
    result = solver.solve(clauses, num_vars, assumptions=[-3, 5])
    result.sat    -> bool
    result.model  -> dict var -> bool (đầy đủ nếu SAT), None nếu UNSAT
    result.stats  -> SolverStats(decisions, propagations, backtracks, runtime)

TODO(D1-D4):
  [ ] Unit propagation
  [ ] Conflict detection (clause rỗng)
  [ ] Chọn biến deterministic (vd: biến nhỏ nhất chưa gán xuất hiện trong clause ngắn nhất)
  [ ] Đệ quy branching + backtracking
  [ ] assumptions: xử lý như unit clause tạm thời (không sửa danh sách clause gốc của KB)
  [ ] Đếm decisions, propagations, backtracks, runtime (time.perf_counter)
  [ ] Phải tự cài DPLL, không dùng thư viện SAT có sẵn
  [ ] (Tùy chọn) pure-literal elimination
  [ ] Timeout/giới hạn decision để experiments ghi nhận TIMEOUT
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass
class SolverStats:
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime: float = 0.0


@dataclass
class SolveResult:
    sat: bool
    model: Optional[Dict[int, bool]]
    stats: SolverStats


class DPLLSolver:
    def solve(self, clauses: List[List[int]], num_vars: int,
              assumptions: Sequence[int] = (), timeout: Optional[float] = None) -> SolveResult:
        raise NotImplementedError
