"""CNF Encoder

Quy ước: clause = list[int] (literal dương/âm), CNF = list[clause].
Biến primary = board.var_of(cell, n); biến phụ bắt đầu từ n*n + 1.

Các encoding (đều tự động, không viết tay CNF cho từng puzzle):
      FACT              : [[±Ci]]
      SAME_STATUS       : (¬Ci ∨ Cj) ∧ (Ci ∨ ¬Cj)
      DIFFERENT_STATUS  : (Ci ∨ Cj) ∧ (¬Ci ∨ ¬Cj)
      AT_MOST k         : mọi tập (k+1) literal: ít nhất một literal False  -> C(m, k+1) clause
      AT_LEAST k        : mọi tập (m-k+1) literal: ít nhất một literal True -> C(m, m-k+1) clause
      EXACTLY k         : AT_MOST k ∧ AT_LEAST k
      PARITY            : chuỗi XOR (Tseitin), m-2 biến phụ, 4m-6 clause
      COMPARE           : hai bộ đếm unary rồi nối, |R|(|R|+1)/2 biến phụ mỗi vùng
      build_kb          : CNF(clue đã lật) ∧ unit clause ô đã chứng minh; đếm lại biến phụ mỗi lần

status = INNOCENT thì đảo cực literal của các ô trong vùng.
"""
from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from engine import board
from engine.clue import Clue, clue_status, resolve_region, validate_clue
from engine.constants import CRIMINAL, INNOCENT, STATUSES

if TYPE_CHECKING:
    from engine.game_state import PublicKB

Clause = List[int]
Lit = Union[int, bool]


def _neg(x: Lit) -> Lit:
    """Phủ định literal hoặc hằng."""
    return (not x) if isinstance(x, bool) else -x


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
    """Đổi clue sang CNF; biến phụ được cấp tách riêng khỏi biến primary.

    encode_clue cộng dồn biến phụ qua các lần gọi trên cùng một Encoder.
    build_kb thì đánh số lại biến phụ từ N*N + 1 mỗi lần gọi.
    Encoder không kiểm tra n; caller phải đảm bảo n hợp lệ.
    """
    _COMPARE_PLAN = {
        "GE": [(False, False)],
        "GT": [(False, True)],
        "LE": [(True, False)],
        "LT": [(True, True)],
        "EQ": [(False, False), (True, False)],
    }

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
        if not isinstance(cell, str) or not board.is_valid_cell(cell, self.n):
            raise ValueError(f"Cell không hợp lệ: {cell!r}")
        var = board.var_of(cell, self.n)
        if status == CRIMINAL:
            return var
        if status == INNOCENT:
            return -var
        raise ValueError(f"Status không hợp lệ: {status!r}")

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
        """Encode PARITY: số ô có trạng thái `status` trong vùng là chẵn/lẻ

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
        """Đổi một clue sang CNF (6 loại core và PARITY, COMPARE).

        Raises:
            ValueError: clue không hợp lệ (sai kiểu, ô ngoài lưới, k ngoài [0, |R|], …).
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
        if clue.type == "COMPARE":
            return self._encode_compare(clue)
        raise ValueError(f"Kiểu clue không hợp lệ: {clue.type!r}")

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
        """Literal dương của cell1, cell2 (validate_clue đã đảm bảo hai ô khác nhau)."""
        return (self.literal_of(clue.params["cell1"], CRIMINAL),
                self.literal_of(clue.params["cell2"], CRIMINAL))
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
        Số clause tăng theo tổ hợp: vùng 8 ô (tối đa của neighbors) thì nhỏ, nhưng vùng
        `list` rất dài (vd 25 ô) có thể sinh hàng triệu clause.
        """
        return [[-lit for lit in subset] for subset in combinations(lits, k + 1)]

    @staticmethod
    def _at_least_clauses(lits: List[int], k: int) -> List[Clause]:
        """Sum >= k  <=>  mọi tập (m-k+1) literal có ít nhất một literal True.

        Mỗi tập S (|S| = m-k+1) cho clause (OR của l với l trong S): C(m, m-k+1) clause.
        k = m cho m unit clause l; k = 0 không có tập nào (m+1 > m) nên không sinh clause.
        Số clause tăng theo tổ hợp: vùng 8 ô (tối đa của neighbors) thì nhỏ, nhưng vùng
        `list` rất dài (vd 25 ô) có thể sinh hàng triệu clause.
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

    def _encode_compare(self, clue: Clue) -> List[Clause]:
        """COMPARE: count(region1) op count(region2), đếm các ô có trạng thái `status`.

        Encoding bộ đếm unary (sequential counter, tương đương hai chiều) rồi nối hai bộ đếm:
          1. Mỗi vùng R có bộ đếm out[j] <=> "ít nhất j ô của R có trạng thái status" (j = 1..|R|).
             Dùng s[i][j] <=> s[i-1][j] v (x_i ^ s[i-1][j-1]), s[0][0] = True, s[i][j>i] = False.
             Biến phụ: i*(i+1)/2 cho mỗi vùng (i chạy 1..|R|)  -> |R|(|R|+1)/2.
          2. GE: mọi j: (count2 >= j) -> (count1 >= j).
             GT: mọi j >= 0: (count2 >= j) -> (count1 >= j+1).
             LE, LT: đổi chỗ hai vùng. EQ = GE ^ LE.
        Số clause: đúng 2|R|² cho mỗi bộ đếm (sau khi rút gọn hằng), cộng clause nối.
        Với _at_least_as_many, GE có |small| clause nối, GT có |small| + 1
        (big/small là bộ đếm của vế lớn/vế nhỏ sau khi đổi chỗ hai vùng nếu cần); EQ = GE + LE.
        Hai vùng chồng nhau vẫn đúng vì mỗi bộ đếm đếm riêng theo literal của ô.
        """
        validate_clue(clue, self.n)
        plan = self._COMPARE_PLAN[clue.params["op"]]
        status = clue_status(clue)
        out1, clauses1 = self._unary_counter(self._region_literals(clue.params["region1"], status))
        out2, clauses2 = self._unary_counter(self._region_literals(clue.params["region2"], status))
        clauses = clauses1 + clauses2
        for swap, strict in plan:
            big, small = (out2, out1) if swap else (out1, out2)
            clauses += self._at_least_as_many(big, small, strict)
        return clauses

    def _region_literals(self, region: dict, status: str) -> List[int]:
        """Literal của các ô trong vùng (row-major): +var nếu CRIMINAL, -var nếu INNOCENT."""
        return [self.literal_of(c, status) for c in resolve_region(region, self.n)]

    @staticmethod
    def _make_clause(items: List[Lit]) -> Optional[Clause]:
        """Rút gọn hằng: có True -> clause luôn đúng (None); bỏ False; còn lại là clause."""
        if any(x is True for x in items):
            return None
        return [x for x in items if x is not False]

    def _unary_counter(self, lits: List[int]) -> Tuple[List[int], List[Clause]]:
        """Bộ đếm unary: trả (out, clauses) với out[j-1] <=> có ít nhất j literal trong lits đúng"""
        clauses: List[Clause] = []
        prev: List[int] = []          # prev[j-1] = s[i-1][j]
        for i, x in enumerate(lits, start=1):
            cur = [self.new_aux() for _ in range(i)]          # s[i][1..i]
            for j in range(1, i + 1):
                s = cur[j - 1]
                above = prev[j - 1] if j <= len(prev) else False    # s[i-1][j]
                below = True if j == 1 else prev[j - 2]             # s[i-1][j-1]
                for items in ([_neg(above), s], [-x, _neg(below), s],
                              [-s, above, x], [-s, above, below]):
                    clause = self._make_clause(items)
                    if clause is not None:
                        clauses.append(clause)
            prev = cur
        return prev, clauses

    def _at_least_as_many(self, big: List[int], small: List[int], strict: bool) -> List[Clause]:
        """Clause nối: count(big) >= count(small) (strict: count(big) > count(small))."""
        clauses: List[Clause] = []
        m = len(big)

        def ge(j: int) -> Lit:                       # count(big) >= j
            if j <= 0:
                return True
            return big[j - 1] if j <= m else False

        for j in range(0 if strict else 1, len(small) + 1):
            target = ge(j + 1 if strict else j)
            premise: Lit = True if j == 0 else small[j - 1]
            clause = self._make_clause([_neg(premise), target])
            if clause is not None:
                clauses.append(clause)
        return clauses

    def build_kb(self, public_kb: "PublicKB") -> KB:
        """KB_t = CNF(clue đã lật) ∧ unit clause của các ô đã chứng minh.

        Chỉ đọc `public_kb`, nên nhãn ẩn và clue chưa lật không thể lọt vào KB.
        Thứ tự clause xác định: clue theo thứ tự trong `public_kb.revealed_clues`,
        rồi unit clause của `proved` theo row-major.
        Mỗi lần gọi đánh số lại biến phụ từ N*N + 1 và đếm lại `num_aux`, nên gọi
        nhiều lần trên cùng một Encoder vẫn cho cùng một KB (không cộng dồn biến phụ).

        Raises:
            ValueError: `public_kb.n` khác n của Encoder, ô trong `proved` sai/ngoài lưới,
                verdict không thuộc {CRIMINAL, INNOCENT}, hoặc clue không hợp lệ.
        """
        if public_kb.n != self.n:
            raise ValueError(f"PublicKB có n={public_kb.n}, Encoder có n={self.n}")
        for cell, verdict in public_kb.proved.items():
            if not isinstance(cell, str) or not board.is_valid_cell(cell, self.n):
                raise ValueError(f"Ô đã chứng minh không hợp lệ: {cell!r}")
            if verdict not in STATUSES:
                raise ValueError(f"Verdict không hợp lệ ở ô {cell}: {verdict!r}")
        self._next_aux = board.first_aux_var(self.n)
        self.num_aux = 0

        clauses: List[Clause] = []
        for clue in public_kb.revealed_clues:
            clauses.extend(self.encode_clue(clue))
        for cell in sorted(public_kb.proved, key=lambda c: board.cell_index(c, self.n)):
            clauses.append([self.literal_of(cell, public_kb.proved[cell])])
        return KB(clauses=clauses, num_primary=self.num_primary, num_aux=self.num_aux)
