"""CNF Encoder. (Scope C)

Quy ước: clause = list[int] (literal dương/âm), CNF = list[clause].
Biến primary = board.var_of(cell, n); biến phụ bắt đầu từ n*n + 1.

TODO(Scope C):
  - Encoder(n): cấp biến phụ qua new_aux()
  - encode_clue(clue) -> list[clause]   (tự động, KHÔNG viết tay CNF cho từng puzzle)
      FACT       : [[±Ci]]
      SAME       : (¬Ci ∨ Cj) ∧ (Ci ∨ ¬Cj)
      DIFFERENT  : (Ci ∨ Cj) ∧ (¬Ci ∨ ¬Cj)
      AT_MOST k  : mọi tập (k+1) biến: ít nhất một biến False  -> C(m, k+1) clause
      AT_LEAST k : mọi tập (m-k+1) biến: ít nhất một biến True -> C(m, m-k+1) clause
      EXACTLY k  : AT_MOST k ∧ AT_LEAST k
      (xử lý biên: k=0, k=|R|, k>|R|)
      Extension 1 (PARITY), Extension 2 (COMPARE): tự chọn encoding (có thể dùng biến phụ)
  - build_kb(public_kb) -> KB(clauses, num_primary, num_aux)
        KB_t = CNF(revealed clues) ∧ unit clause cho mỗi verdict đã chứng minh
        TUYỆT ĐỐI không đưa nhãn ẩn / clue chưa lật vào.
  - thống kê: số primary, số aux, số clause (cho experiments)
  - validate tham số clue (có thể gọi engine.clue.validate_clue)

Report cần: suy ra công thức cho 1 clue nhị phân (SAME/DIFFERENT) và 1 clue đếm (EXACTLY).
"""
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

from engine import board
from engine.clue import Clue
from engine.constants import CRIMINAL, INNOCENT

if TYPE_CHECKING:
    from engine.game_state import PublicKB

Clause = List[int]


@dataclass
class KB:
    """Cơ sở tri thức dạng CNF kèm thống kê số biến"""
    clauses: List[Clause]
    num_primary: int
    num_aux: int

    @property
    def num_vars(self) -> int:
        """Tổng số biến (primary + phụ), dùng làm num_vars khi gọi DPLL"""
        return self.num_primary + self.num_aux

    @property
    def num_clauses(self) -> int:
        """Số clause của KB"""
        return len(self.clauses)


class Encoder:
    """Đổi clue sang CNF; biến phụ được cấp tách riêng khỏi biến primary"""

    def __init__(self, n: int):
        self.n = n
        self._next_aux = board.first_aux_var(n)
        self.num_aux = 0

    @property
    def num_primary(self) -> int:
        """Số biến primary (mỗi ô một biến) = N*N"""
        return self.n * self.n

    def new_aux(self) -> int:
        """Cấp một biến phụ mới"""
        v = self._next_aux
        self._next_aux += 1
        self.num_aux += 1
        return v

    def literal_of(self, cell: str, status: str) -> int:
        """Literal của ô: +var nếu status là CRIMINAL, -var nếu là INNOCENT"""
        if not board.is_valid_cell(cell, self.n):
            raise ValueError(f"Cell is not valid: {cell!r}")
        var = board.var_of(cell, self.n)
        if status == CRIMINAL:
            return var
        if status == INNOCENT:
            return -var
        raise ValueError(f"Status is not valid: {status!r}")

    def encode_clue(self, clue: Clue) -> List[Clause]:
        raise NotImplementedError("C2-C5")

    def build_kb(self, public_kb: "PublicKB") -> KB:
        raise NotImplementedError("C6")
