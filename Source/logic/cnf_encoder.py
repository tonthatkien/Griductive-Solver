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

    @staticmethod
    def _xor_gate(t: int, a: int, b: int) -> List[Clause]:
        """Bốn clause của t <-> (a XOR b); t được xác định duy nhất bởi a, b"""
        return [[-t, a, b], [-t, -a, -b], [t, -a, b], [t, a, -b]]

    @staticmethod
    def _xor_constraint(a: int, b: int, want_odd: bool) -> List[Clause]:
        """Hai clause ép (a XOR b) = 1 nếu want_odd, ngược lại ép (a XOR b) = 0"""
        if want_odd:
            return [[a, b], [-a, -b]]
        return [[-a, b], [a, -b]]

    def encode_parity(self, clue: Clue) -> List[Clause]:
        """Encode PARITY: số ô có trạng thái `status` trong vùng là chẵn/lẻ (Extension 1)

        Dùng chuỗi XOR (Tseitin): acc_1 = l_1, acc_i <-> acc_{i-1} XOR l_i, rồi ép acc_m
        theo parity. Bước cuối ép trực tiếp nên không cần biến phụ riêng.
        Với m ô trong vùng (m >= 2): m - 2 biến phụ, 4(m - 2) + 2 = 4m - 6 clause.
        m = 1: 0 biến phụ, 1 clause. m = 8 (neighbors giữa lưới): 6 biến phụ, 26 clause.
        Mỗi cổng XOR có đủ 4 clause nên biến phụ bị xác định duy nhất bởi biến primary,
        không làm tăng số model của KB (uniqueness_check không bị ảnh hưởng).
        count = 0 được coi là chẵn. status = INNOCENT thì literal bị đảo cực.
        """
        if clue.type != "PARITY":
            raise ValueError(f"encode_parity chỉ nhận PARITY, nhận {clue.type!r}")
        validate_clue(clue, self.n)
        cells = resolve_region(clue.params["region"], self.n)  # row-major, không trùng
        status = clue_status(clue)
        lits = [self.literal_of(cell, status) for cell in cells]
        want_odd = clue.params["parity"] == "ODD"

        if len(lits) == 1:
            return [[lits[0]]] if want_odd else [[-lits[0]]]

        clauses: List[Clause] = []
        acc = lits[0]
        for lit in lits[1:-1]:
            t = self.new_aux()
            clauses.extend(self._xor_gate(t, acc, lit))
            acc = t
        clauses.extend(self._xor_constraint(acc, lits[-1], want_odd))
        return clauses

    def encode_clue(self, clue: Clue) -> List[Clause]:
        """
        Đổi một clue sang CNF (FACT, SAME_STATUS, DIFFERENT_STATUS,
                                  EXACTLY, AT_LEAST, AT_MOST, PARITY)
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
        if clue.type == "PARITY":
            return self.encode_parity(clue)
        raise NotImplementedError("C5")

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
