"""DPLL SAT solver. (Scope D)
"""
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class SolverStats:
    """Thống kê chi tiết trong quá trình giải bài toán SAT."""

    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime: float = 0.0


@dataclass
class SolveResult:
    """Kết quả trả về của bộ giải DPLL."""

    sat: bool
    model: Optional[Dict[int, bool]]
    stats: SolverStats


class DPLLSolver:
    """Bộ giải SAT sử dụng thuật toán DPLL thuần Python."""

    def __init__(self) -> None:
        self.stats = SolverStats()

    def get_clause_status(
        self, clause: Sequence[int], assignment: Dict[int, bool]
    ) -> Tuple[str, Optional[int]]:
        """Xác định trạng thái của một mệnh đề dưới phép gán hiện tại.

        Trạng thái trả về:
        - "SATISFIED": Có ít nhất một literal nhận giá trị True.
        - "CONFLICT": Mọi literal đều nhận giá trị False (mệnh đề rỗng / mâu thuẫn).
        - "UNIT": Chưa thỏa mãn và chỉ còn duy nhất 1 literal chưa gán.
        - "UNRESOLVED": Chưa thỏa mãn và còn từ 2 literal chưa gán trở lên.
        """
        unassigned_lits = set()

        for lit in clause:
            var = abs(lit)
            if var in assignment:
                # Giá trị literal đúng khi biến dương gán True hoặc biến âm gán False
                lit_val = assignment[var] if lit > 0 else not assignment[var]
                if lit_val:
                    return "SATISFIED", None
            else:
                unassigned_lits.add(lit)

        if not unassigned_lits:
            return "CONFLICT", None

        if len(unassigned_lits) == 1:
            return "UNIT", next(iter(unassigned_lits))

        return "UNRESOLVED", None

    def is_clause_satisfied(
        self, clause: Sequence[int], assignment: Dict[int, bool]
    ) -> bool:
        """Kiểm tra xem mệnh đề đã được thỏa mãn bởi phép gán hay chưa."""
        status, _ = self.get_clause_status(clause, assignment)
        return status == "SATISFIED"

    def is_conflict(
        self, clauses: Sequence[Sequence[int]], assignment: Dict[int, bool]
    ) -> bool:
        """Kiểm tra sự tồn tại của bất kỳ mệnh đề rỗng nào dưới phép gán hiện tại."""
        return any(
            self.get_clause_status(clause, assignment)[0] == "CONFLICT"
            for clause in clauses
        )

    def unit_propagate(
        self, clauses: Sequence[Sequence[int]], assignment: Dict[int, bool]
    ) -> Tuple[bool, Optional[List[int]]]:
        """Lan truyền mệnh đề đơn đến khi hết unit clause hoặc phát hiện mâu thuẫn.
        """
        while True:
            first_unit_lit: Optional[int] = None

            for clause in clauses:
                status, unit_lit = self.get_clause_status(clause, assignment)
                if status == "CONFLICT":
                    return True, list(clause)
                if status == "UNIT" and first_unit_lit is None:
                    first_unit_lit = unit_lit

            # Không còn unit clause nào để lan truyền
            if first_unit_lit is None:
                return False, None

            # Gán giá trị ép buộc cho literal đơn vị
            var = abs(first_unit_lit)
            assignment[var] = (first_unit_lit > 0)
            self.stats.propagations += 1

    def solve(
        self,
        clauses: List[List[int]],
        num_vars: int,
        assumptions: Sequence[int] = (),
        timeout: Optional[float] = None,
    ) -> SolveResult:
        """Giải bài toán SAT bằng DPLL hỗ trợ assumptions và thống kê."""
        start_time = time.perf_counter()
        self.stats = SolverStats()
        assignment: Dict[int, bool] = {}

        # Xử lý các giả định ban đầu như unit clause tạm thời
        for lit in assumptions:
            var = abs(lit)
            val = (lit > 0)
            if var in assignment and assignment[var] != val:
                self.stats.runtime = time.perf_counter() - start_time
                return SolveResult(sat=False, model=None, stats=self.stats)
            assignment[var] = val

        is_conf, _ = self.unit_propagate(clauses, assignment)
        if is_conf:
            self.stats.runtime = time.perf_counter() - start_time
            return SolveResult(sat=False, model=None, stats=self.stats)

        # Kiểm tra nếu toàn bộ clauses đã thỏa mãn qua Unit Propagation
        if all(self.is_clause_satisfied(c, assignment) for c in clauses):
            full_model = {v: assignment.get(v, False) for v in range(1, num_vars + 1)}
            self.stats.runtime = time.perf_counter() - start_time
            return SolveResult(sat=True, model=full_model, stats=self.stats)

        # Không thể suy luận trực tiếp, cần branching và backtracking
        raise NotImplementedError(
            "Công thức chưa thể kết luận chỉ bằng Unit Propagation. "
            "branching và backtracking - D2-D3."
        )
