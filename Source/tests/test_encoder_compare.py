"""Test cho encode COMPARE: CNF phải khớp semantic.evaluate trên mọi phép gán."""
import itertools
import random
import unittest

from engine import board
from engine.clue import Clue
from logic.cnf_encoder import Encoder
from logic.semantic import evaluate

N = 3
OPS = ("GT", "GE", "EQ", "LE", "LT")
REGIONS = {
    "row1": {"type": "row", "number": 1},
    "colA": {"type": "col", "letter": "A"},
    "nei_B2": {"type": "neighbors", "cell": "B2"},
    "nei_A1": {"type": "neighbors", "cell": "A1"},
    "one_cell": {"type": "list", "cells": ["C3"]},
}
EMPTY_REGION = {"type": "list", "cells": []}     # không hợp lệ, chỉ dùng test bị từ chối

PAIRS = [("row1", "colA"), ("nei_B2", "row1"), ("nei_A1", "nei_B2"),
         ("one_cell", "colA"), ("row1", "row1"), # biên: hai vùng giống hệt, EQ luôn đúng
         ("one_cell", "one_cell"),               # biên: hai vùng 1 ô, EQ với chính nó
         ("row1", "one_cell")]                   # biên: vùng 1 ô làm vế phải


def make_compare(r1: str, r2: str, op: str, status: str) -> Clue:
    params = dict(region1=REGIONS[r1], region2=REGIONS[r2], op=op, status=status)
    return Clue(id="clue_A1", owner="A1", type="COMPARE", params=params)


def propagate(clauses, fixed):
    """Lan truyền unit từ phép gán primary. Trả (ok, assignment đã lan truyền).

    ok=False: gặp clause bị vi phạm hoàn toàn -> CNF chắc chắn UNSAT với phép gán này.
    ok=True : không xung đột; test gọi phải tự kiểm tra mọi biến đã bị ép
              (nếu còn biến phụ tự do thì kết luận SAT chưa chắc đúng).
    Không gọi DPLL, để test này độc lập với logic/dpll.py.
    """
    assignment = dict(fixed)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            if any(assignment.get(abs(lit)) == (lit > 0) for lit in clause):
                continue
            free = [lit for lit in clause if abs(lit) not in assignment]
            if not free:
                return False, assignment
            if len(free) == 1:
                assignment[abs(free[0])] = free[0] > 0
                changed = True
    return True, assignment


class TestEncodeCompare(unittest.TestCase):
    def test_cnf_matches_semantic_on_all_assignments(self):
        cells = board.all_cells(N)
        for (r1, r2), op, status in itertools.product(PAIRS, OPS, ("CRIMINAL", "INNOCENT")):
            clue = make_compare(r1, r2, op, status)
            enc = Encoder(N)
            clauses = enc._encode_compare(clue)
            all_vars = set(range(1, N * N + enc.num_aux + 1))
            for bits in itertools.product((False, True), repeat=len(cells)):
                assignment = dict(zip(cells, bits))
                fixed = {board.var_of(c, N): v for c, v in assignment.items()}
                with self.subTest(r1=r1, r2=r2, op=op, status=status, bits=bits):
                    ok, full = propagate(clauses, fixed)
                    self.assertEqual(ok, evaluate(clue, assignment, N))
                    if ok:
                        # mọi biến phụ bị ép -> chỉ có đúng 1 mở rộng
                        self.assertEqual(set(full), all_vars)

    def test_status_defaults_to_criminal(self):
        with_status = make_compare("row1", "colA", "GT", "CRIMINAL")
        params = {k: v for k, v in with_status.params.items() if k != "status"}
        no_status = Clue(id="clue_A1", owner="A1", type="COMPARE", params=params)
        self.assertEqual(Encoder(N)._encode_compare(no_status),
                         Encoder(N)._encode_compare(with_status))

    def test_aux_vars_come_after_primary_and_are_counted(self):
        enc = Encoder(N)
        clauses = enc._encode_compare(make_compare("row1", "colA", "GT", "CRIMINAL"))
        # mỗi vùng |R| ô dùng |R|(|R|+1)/2 biến phụ: 2 vùng x (3*4/2) = 12
        self.assertEqual(enc.num_aux, 2 * (3 * 4 // 2))
        used = {abs(lit) for clause in clauses for lit in clause}
        aux_used = {v for v in used if v > N * N}
        self.assertEqual(aux_used, set(range(board.first_aux_var(N), board.first_aux_var(N) + 12)))
        self.assertTrue(used - aux_used <= set(range(1, N * N + 1)))

    def test_encoding_is_deterministic(self):
        clue = make_compare("nei_B2", "row1", "EQ", "INNOCENT")
        self.assertEqual(Encoder(N)._encode_compare(clue), Encoder(N)._encode_compare(clue))

    def test_invalid_op_raises_before_allocating_aux(self):
        clue = make_compare("row1", "colA", "GT", "CRIMINAL")
        bad = Clue(id=clue.id, owner=clue.owner, type="COMPARE",
                   params={**clue.params, "op": "NE"})
        enc = Encoder(N)
        with self.assertRaises(ValueError):
            enc._encode_compare(bad)
        self.assertEqual(enc.num_aux, 0)

    def test_encode_clue_dispatches_compare(self):
        clue = make_compare("row1", "colA", "GT", "CRIMINAL")
        self.assertEqual(Encoder(N).encode_clue(clue), Encoder(N)._encode_compare(clue))

    def test_encode_clue_rejects_bad_op_without_allocating_aux(self):
        good = make_compare("row1", "colA", "GT", "CRIMINAL")
        bad = Clue(id=good.id, owner=good.owner, type="COMPARE",
                   params={**good.params, "op": "NE"})
        enc = Encoder(N)
        with self.assertRaises(ValueError):
            enc.encode_clue(bad)
        self.assertEqual(enc.num_aux, 0)

    def test_encode_clue_rejects_region_outside_grid(self):
        good = make_compare("row1", "colA", "GT", "CRIMINAL")
        bad = Clue(id=good.id, owner=good.owner, type="COMPARE",
                   params={**good.params, "region2": {"type": "row", "number": 9}})
        with self.assertRaises(ValueError):
            Encoder(N).encode_clue(bad)

    def test_cnf_matches_semantic_n4_random_assignments(self):
        n = 4
        cells = board.all_cells(n)
        regions = {"row": {"type": "row", "number": 1},
                   "col": {"type": "col", "letter": "B"},
                   "nei": {"type": "neighbors", "cell": "B2"}}
        rng = random.Random(0)
        for (r1, r2), op, status in itertools.product(
                (("row", "col"), ("nei", "row")), OPS, ("CRIMINAL", "INNOCENT")):
            clue = Clue(id="clue_A1", owner="A1", type="COMPARE",
                        params=dict(region1=regions[r1], region2=regions[r2],
                                    op=op, status=status))
            enc = Encoder(n)  # tạo ngoài vòng 200 lần
            clauses = enc._encode_compare(clue)
            all_vars = set(range(1, n * n + enc.num_aux + 1))
            for _ in range(200):
                assignment = {c: rng.random() < 0.5 for c in cells}
                fixed = {board.var_of(c, n): v for c, v in assignment.items()}
                with self.subTest(r1=r1, r2=r2, op=op, status=status):
                    ok, full = propagate(clauses, fixed)
                    self.assertEqual(ok, evaluate(clue, assignment, n))
                    if ok:
                        self.assertEqual(set(full), all_vars)

    def test_empty_region_is_rejected_without_allocating_aux(self):
        for side in ("region1", "region2"):
            with self.subTest(side=side):
                good = make_compare("row1", "colA", "GT", "CRIMINAL")
                bad = Clue(id=good.id, owner=good.owner, type="COMPARE",
                           params={**good.params, side: EMPTY_REGION})
                enc = Encoder(N)
                with self.assertRaises(ValueError):
                    enc.encode_clue(bad)
                self.assertEqual(enc.num_aux, 0)


if __name__ == "__main__":
    unittest.main()
