"""DPLL SAT solver. (Scope D)
"""
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class SolverStats:
    """Thống kê chi tiết trong quá trình giải bài toán SAT.

    Thuộc tính:
        decisions: Số lần chọn biến để rẽ nhánh (Scope D2).
        propagations: Số literal được suy ra từ các unit clause (Scope D1).
        backtracks: Số lần quay lui sau khi một nhánh dẫn tới mâu thuẫn (Scope D2).
        runtime: Tổng thời gian thực thi của thuật toán tính bằng giây (time.perf_counter).
    """

    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    runtime: float = 0.0


@dataclass
class SolveResult:
    """Kết quả trả về của bộ giải DPLL.

    Thuộc tính:
        sat: True nếu công thức CNF thỏa mãn, False nếu mâu thuẫn (UNSAT) hoặc quá thời gian.
        model: Bảng gán đầy đủ {var: bool} cho mọi biến từ 1 đến num_vars nếu SAT,
            hoặc None nếu UNSAT.
        stats: Thống kê chi tiết quá trình giải (decisions, propagations, backtracks, runtime).
        timed_out: True nếu quá trình giải bị dừng do vượt quá thời gian timeout, ngược lại False.
    """

    sat: bool
    model: Optional[Dict[int, bool]]
    stats: SolverStats
    timed_out: bool = False


class _TimeoutException(Exception):
    """Ngoại lệ nội bộ dùng để ngắt tìm kiếm ngay lập tức khi vượt quá giới hạn thời gian."""

    pass


class DPLLSolver:
    """Bộ giải SAT sử dụng thuật toán DPLL thuần Python (Scope D - Task D1)."""

    def __init__(self) -> None:
        self.stats = SolverStats()

    def get_clause_status(
        self,
        clause: Sequence[int],
        assignment: Dict[int, bool],
        deadline: Optional[float] = None,
    ) -> Tuple[str, Optional[int]]:
        """Xác định trạng thái của một mệnh đề dưới phép gán hiện tại.

        Trạng thái trả về:
        - "SATISFIED": Có ít nhất một literal nhận giá trị True.
        - "CONFLICT": Mọi literal đều nhận giá trị False (mệnh đề rỗng / mâu thuẫn).
        - "UNIT": Chưa thỏa mãn và chỉ còn duy nhất 1 literal chưa gán.
        - "UNRESOLVED": Chưa thỏa mãn và còn từ 2 literal chưa gán trở lên.
        """
        unassigned_lits = set()

        for lit_idx, lit in enumerate(clause):
            if (
                deadline is not None
                and (lit_idx & 127 == 0)
                and time.perf_counter() >= deadline
            ):
                raise _TimeoutException()

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

        # Mệnh đề chứa đồng thời x và ¬x (tautology) luôn thỏa mãn với mọi phép gán
        for lit_idx, lit in enumerate(unassigned_lits):
            if (
                deadline is not None
                and (lit_idx & 127 == 0)
                and time.perf_counter() >= deadline
            ):
                raise _TimeoutException()
            if -lit in unassigned_lits:
                return "SATISFIED", None

        if len(unassigned_lits) == 1:
            return "UNIT", next(iter(unassigned_lits))

        return "UNRESOLVED", None

    def is_clause_satisfied(
        self,
        clause: Sequence[int],
        assignment: Dict[int, bool],
        deadline: Optional[float] = None,
    ) -> bool:
        """Kiểm tra xem mệnh đề đã được thỏa mãn bởi phép gán hay chưa."""
        status, _ = self.get_clause_status(clause, assignment, deadline=deadline)
        return status == "SATISFIED"

    def is_conflict(
        self,
        clauses: Sequence[Sequence[int]],
        assignment: Dict[int, bool],
        deadline: Optional[float] = None,
    ) -> bool:
        """Kiểm tra sự tồn tại của bất kỳ mệnh đề rỗng nào dưới phép gán hiện tại."""
        return any(
            self.get_clause_status(clause, assignment, deadline=deadline)[0] == "CONFLICT"
            for clause in clauses
        )

    def unit_propagate(
        self,
        clauses: Sequence[Sequence[int]],
        assignment: Dict[int, bool],
        deadline: Optional[float] = None,
    ) -> Tuple[bool, Optional[List[int]]]:
        """Lan truyền mệnh đề đơn đến khi hết unit clause hoặc phát hiện mâu thuẫn.

        Args:
            clauses: Danh sách các mệnh đề CNF (không bị biến đổi danh sách gốc).
            assignment: Từ điển phép gán biến (được cập nhật trực tiếp).
            deadline: Mốc thời gian giới hạn (time.perf_counter), ném ngoại lệ nếu vượt quá.

        Returns:
            Tuple (is_conflict, conflict_clause).
        """
        while True:
            if deadline is not None and time.perf_counter() >= deadline:
                raise _TimeoutException()

            first_unit_lit: Optional[int] = None

            for idx, clause in enumerate(clauses):
                if deadline is not None and (idx & 63 == 0) and time.perf_counter() >= deadline:
                    raise _TimeoutException()
                status, unit_lit = self.get_clause_status(clause, assignment, deadline=deadline)
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

    def _build_full_model(
        self,
        assignment: Dict[int, bool],
        num_vars: int,
        deadline: Optional[float] = None,
    ) -> Dict[int, bool]:
        """Xây dựng bảng gán hoàn chỉnh cho mọi biến từ 1 đến num_vars có kiểm tra deadline."""
        full_model: Dict[int, bool] = {}
        for v in range(1, num_vars + 1):
            if deadline is not None and (v & 1023 == 0) and time.perf_counter() >= deadline:
                raise _TimeoutException()
            full_model[v] = assignment.get(v, False)
        return full_model

    def solve(
        self,
        clauses: Sequence[Sequence[int]],
        num_vars: int,
        assumptions: Sequence[int] = (),
        timeout: Optional[float] = None,
    ) -> SolveResult:
        """Giải bài toán SAT bằng DPLL hỗ trợ assumptions và thống kê.

        Trong phạm vi Task D1:
        - Thực hiện lan truyền mệnh đề đơn (Unit Propagation) và phát hiện mâu thuẫn (Conflict).
        - Nếu công thức thỏa mãn hoàn toàn qua Unit Propagation -> trả về SAT cùng model hợp lệ.
        - Nếu phát hiện mâu thuẫn -> trả về UNSAT (sat=False, model=None).
        - Nếu chưa thể giải quyết chỉ bằng Unit Propagation -> ném NotImplementedError (thuộc D2).
        """
        start_time = time.perf_counter()
        self.stats = SolverStats()

        if not isinstance(num_vars, int) or isinstance(num_vars, bool):
            raise TypeError(f"num_vars phải là số nguyên (int), nhận được: {num_vars!r}")
        if num_vars < 0:
            raise ValueError(f"num_vars không hợp lệ (phải >= 0): {num_vars}")

        if timeout is not None:
            if (not isinstance(timeout, (int, float))) or isinstance(timeout, bool):
                raise TypeError(f"timeout phải là số thực hoặc int, nhận được: {timeout!r}")
            if math.isnan(timeout):
                raise ValueError(f"timeout không hợp lệ (NaN): {timeout!r}")
            if timeout <= 0:
                self.stats.runtime = time.perf_counter() - start_time
                return SolveResult(sat=False, model=None, stats=self.stats, timed_out=True)

        deadline = (start_time + timeout) if timeout is not None else None

        if isinstance(clauses, (str, bytes)) or not hasattr(clauses, "__iter__"):
            raise TypeError(f"clauses phải là tập hợp các mệnh đề, nhận được: {clauses!r}")

        # Chuẩn hóa clauses thành list các tuple để hỗ trợ cả iterator/generator
        # và bảo đảm kiểm tra deadline trong từng vòng lặp
        clauses_list: List[Tuple[int, ...]] = []
        assumptions_list: List[int] = []
        assignment: Dict[int, bool] = {}

        try:
            for idx, clause in enumerate(clauses):
                if deadline is not None and (idx & 63 == 0) and time.perf_counter() >= deadline:
                    raise _TimeoutException()

                if isinstance(clause, (str, bytes)) or not hasattr(clause, "__iter__"):
                    raise TypeError(
                        f"Mệnh đề phải là danh sách các literal, nhận được: {clause!r}"
                    )

                c_lits: List[int] = []
                for lit_idx, lit in enumerate(clause):
                    if (
                        deadline is not None
                        and (lit_idx & 63 == 0)
                        and time.perf_counter() >= deadline
                    ):
                        raise _TimeoutException()
                    if not isinstance(lit, int) or isinstance(lit, bool):
                        raise TypeError(f"Literal phải là số nguyên (int), nhận được: {lit!r}")
                    if lit == 0:
                        raise ValueError("Literal trong mệnh đề không được bằng 0")
                    if abs(lit) > num_vars:
                        raise ValueError(
                            f"Literal {lit} có biến {abs(lit)} vượt quá num_vars={num_vars}"
                        )
                    c_lits.append(lit)
                clauses_list.append(tuple(c_lits))

            if isinstance(assumptions, (str, bytes)) or not hasattr(assumptions, "__iter__"):
                raise TypeError(
                    f"assumptions phải là danh sách các literal, nhận được: {assumptions!r}"
                )

            # Chuẩn hóa assumptions thành list có kiểm tra deadline
            for a_idx, lit in enumerate(assumptions):
                if (
                    deadline is not None
                    and (a_idx & 63 == 0)
                    and time.perf_counter() >= deadline
                ):
                    raise _TimeoutException()
                if not isinstance(lit, int) or isinstance(lit, bool):
                    raise TypeError(
                        f"Assumption literal phải là số nguyên (int), nhận được: {lit!r}"
                    )
                if lit == 0:
                    raise ValueError("Literal trong assumptions không được bằng 0")
                if abs(lit) > num_vars:
                    raise ValueError(
                        f"Assumption {lit} có biến {abs(lit)} vượt quá num_vars={num_vars}"
                    )
                assumptions_list.append(lit)

            # Xử lý các giả định ban đầu như unit clause tạm thời
            for idx, lit in enumerate(assumptions_list):
                if deadline is not None and (idx & 63 == 0) and time.perf_counter() >= deadline:
                    raise _TimeoutException()
                var = abs(lit)
                val = (lit > 0)
                if var in assignment and assignment[var] != val:
                    self.stats.runtime = time.perf_counter() - start_time
                    return SolveResult(sat=False, model=None, stats=self.stats)
                assignment[var] = val

            # 1. Lan truyền mệnh đề đơn (Unit Propagation - Scope D1)
            is_conf, _ = self.unit_propagate(clauses_list, assignment, deadline=deadline)
            if is_conf:
                self.stats.runtime = time.perf_counter() - start_time
                return SolveResult(sat=False, model=None, stats=self.stats)

            # 2. Kiểm tra nếu toàn bộ mệnh đề đã được thỏa mãn qua Unit Propagation
            all_sat = True
            for idx, c in enumerate(clauses_list):
                if deadline is not None and (idx & 63 == 0) and time.perf_counter() >= deadline:
                    raise _TimeoutException()
                if not self.is_clause_satisfied(c, assignment, deadline=deadline):
                    all_sat = False
                    break

            if all_sat:
                full_model = self._build_full_model(assignment, num_vars, deadline=deadline)
                self.stats.runtime = time.perf_counter() - start_time
                return SolveResult(sat=True, model=full_model, stats=self.stats)

            # 3. Chưa thể kết luận bằng Unit Propagation: cần branching & backtracking (D2)
            self.stats.runtime = time.perf_counter() - start_time
            raise NotImplementedError(
                "Công thức chưa thể kết luận chỉ bằng Unit Propagation. "
                "Cần branching và backtracking."
            )
        except _TimeoutException:
            self.stats.runtime = time.perf_counter() - start_time
            return SolveResult(sat=False, model=None, stats=self.stats, timed_out=True)
