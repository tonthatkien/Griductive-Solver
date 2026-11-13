"""CNF Encoder. (Scope C)

Quy ước: clause = list[int] (literal dương/âm), CNF = list[clause].
Biến primary = board.var_of(cell, n); biến phụ bắt đầu từ n*n + 1.

Đã xong: C1 (khung), C2 (FACT, SAME_STATUS, DIFFERENT_STATUS), C3 (EXACTLY, AT_LEAST, AT_MOST).

TODO(Scope C):
  - encode_clue: Extension 1 (PARITY, C4), Extension 2 (COMPARE, C5): tự chọn encoding
    (có thể dùng biến phụ), ghi rõ encoding và số clause trong docstring
  - build_kb(public_kb) -> KB(clauses, num_primary, num_aux)   (C6)
        KB_t = CNF(revealed clues) ∧ unit clause cho mỗi verdict đã chứng minh
        TUYỆT ĐỐI không đưa nhãn ẩn / clue chưa lật vào.

Các encoding đã cài (đều tự động, KHÔNG viết tay CNF cho từng puzzle, 0 biến phụ):
      FACT              : [[±Ci]]
      SAME_STATUS       : (¬Ci ∨ Cj) ∧ (Ci ∨ ¬Cj)
      DIFFERENT_STATUS  : (Ci ∨ Cj) ∧ (¬Ci ∨ ¬Cj)
      AT_MOST k         : mọi tập (k+1) literal: ít nhất một literal False  -> C(m, k+1) clause
      AT_LEAST k        : mọi tập (m-k+1) literal: ít nhất một literal True -> C(m, m-k+1) clause
      EXACTLY k         : AT_MOST k ∧ AT_LEAST k
      status = INNOCENT thì đảo cực literal của các ô trong vùng.

Report cần: suy ra công thức cho 1 clue nhị phân (SAME/DIFFERENT) và 1 clue đếm (EXACTLY).
"""
from dataclasses import dataclass
from typing import List, TYPE_CHECKING, Tuple
from itertools import combinations

from engine import board
from engine.clue import Clue, clue_status, resolve_region, validate_clue
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
        """
        Đổi một clue sang CNF (FACT, SAME_STATUS, DIFFERENT_STATUS,
                                  EXACTLY, AT_LEAST, AT_MOST)
        """
        validate_clue(clue, self.n)
        if clue.type == "FACT":
            return self._encode_fact(clue)
        if clue.type == "SAME_STATUS":
            return self._encode_same(clue)
        if clue.type == "DIFFERENT_STATUS":
            return self._encode_different(clue)
        if clue.type == "AT_MOST":
            return self._encode_at_most(clue)
        if clue.type == "AT_LEAST":
            return self._encode_at_least(clue)
        if clue.type == "EXACTLY":
            return self._encode_exactly(clue)
        raise NotImplementedError("C4-C5")

    def _encode_fact(self, clue: Clue) -> List[Clause]:
        """FACT: ô target có trạng thái status  ->  unit clause [±Ci], 0 biến phụ"""
        return [[self.literal_of(clue.params["target"], clue_status(clue))]]

    def _encode_same(self, clue: Clue) -> List[Clause]:
        """SAME_STATUS: Ci <-> Cj

        Ci <-> Cj  =  (Ci -> Cj) ∧ (Cj -> Ci)
                   =  (¬Ci ∨ Cj) ∧ (¬Cj ∨ Ci)
        Sinh 2 clause, 0 biến phụ.
        """
        ci, cj = self._pair_literals(clue)
        return [[-ci, cj], [ci, -cj]]

    def _encode_different(self, clue: Clue) -> List[Clause]:
        """DIFFERENT_STATUS: Ci xor Cj

        Ci xor Cj  =  (Ci ∨ Cj) ∧ ¬(Ci ∧ Cj)
                   =  (Ci ∨ Cj) ∧ (¬Ci ∨ ¬Cj)
        Sinh 2 clause, 0 biến phụ.
        """
        ci, cj = self._pair_literals(clue)
        return [[ci, cj], [-ci, -cj]]

    def _pair_literals(self, clue: Clue) -> Tuple[int, int]:
        """Literal dương của cell1, cell2 (hai ô phải khác nhau)"""
        cell1, cell2 = clue.params["cell1"], clue.params["cell2"]
        if cell1 == cell2:
            raise ValueError(f"cell1 and cell2 must differ: {cell1!r}")
        return self.literal_of(cell1, CRIMINAL), self.literal_of(cell2, CRIMINAL)

    def _count_literals(self, clue: Clue) -> Tuple[List[int], int]:
        """Literal của các ô trong vùng (row-major) và k.

        status = INNOCENT thì literal là âm, nên "đếm Innocent" chỉ là đếm literal đúng
        theo cực đã đảo, các công thức bên dưới không cần phân biệt status.
        """
        cells = resolve_region(clue.params["region"], self.n)
        status = clue_status(clue)
        return [self.literal_of(c, status) for c in cells], clue.params["k"]

    @staticmethod
    def _at_most_clauses(lits: List[int], k: int) -> List[Clause]:
        """Sum <= k  <=>  mọi tập (k+1) literal có ít nhất một literal False.

        Mỗi tập S (|S| = k+1) cho clause (OR của ¬l với l trong S): C(m, k+1) clause.
        k = 0 cho m unit clause ¬l; k >= m không có tập nào nên không sinh clause.
        """
        return [[-lit for lit in subset] for subset in combinations(lits, k + 1)]

    @staticmethod
    def _at_least_clauses(lits: List[int], k: int) -> List[Clause]:
        """Sum >= k  <=>  mọi tập (m-k+1) literal có ít nhất một literal True.

        Mỗi tập S (|S| = m-k+1) cho clause (OR của l với l trong S): C(m, m-k+1) clause.
        k = m cho m unit clause l; k = 0 không có tập nào (m+1 > m) nên không sinh clause.
        """
        return [list(subset) for subset in combinations(lits, len(lits) - k + 1)]

    def _encode_at_most(self, clue: Clue) -> List[Clause]:
        """AT_MOST k: C(m, k+1) clause, 0 biến phụ"""
        lits, k = self._count_literals(clue)
        return self._at_most_clauses(lits, k)

    def _encode_at_least(self, clue: Clue) -> List[Clause]:
        """AT_LEAST k: C(m, m-k+1) clause, 0 biến phụ"""
        lits, k = self._count_literals(clue)
        return self._at_least_clauses(lits, k)

    def _encode_exactly(self, clue: Clue) -> List[Clause]:
        """EXACTLY k = AT_MOST k ∧ AT_LEAST k: C(m, k+1) + C(m, m-k+1) clause, 0 biến phụ"""
        lits, k = self._count_literals(clue)
        return self._at_most_clauses(lits, k) + self._at_least_clauses(lits, k)

    def build_kb(self, public_kb: "PublicKB") -> KB:
        raise NotImplementedError("C6")
