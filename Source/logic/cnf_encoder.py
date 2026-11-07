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
from typing import List

Clause = List[int]


@dataclass
class KB:
    clauses: List[Clause]
    num_primary: int
    num_aux: int

    @property
    def num_vars(self) -> int:
        return self.num_primary + self.num_aux


class Encoder:
    def __init__(self, n: int):
        self.n = n
        self._next_aux = n * n + 1
        self.num_aux = 0

    def new_aux(self) -> int:
        v = self._next_aux
        self._next_aux += 1
        self.num_aux += 1
        return v

    def encode_clue(self, clue) -> List[Clause]:
        raise NotImplementedError

    def build_kb(self, public_kb) -> KB:
        raise NotImplementedError
