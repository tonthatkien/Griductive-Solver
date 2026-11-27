"""Đối chiếu encoder ↔ semantic evaluator. Với mỗi loại clue, duyệt mọi assignment của các ô
clue nhắc tới và so `evaluate(...)` với việc CNF có thỏa hay không (kiểm bằng DPLL,
assumptions = giá trị primary, biến phụ để DPLL tự tìm)."""
import itertools
import unittest
from typing import List, Tuple

from engine import board
from engine.clue import Clue, clue_cells
from engine.constants import CRIMINAL, INNOCENT
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver
from logic.semantic import evaluate

N = 3
STATUSES = (CRIMINAL, INNOCENT)
ROW1 = {"type": "row", "number": 1}
ROW2 = {"type": "row", "number": 2}
ROW3 = {"type": "row", "number": 3}
COLA = {"type": "col", "letter": "A"}
NEI_A1 = {"type": "neighbors", "cell": "A1"}
NEI_B2 = {"type": "neighbors", "cell": "B2"}
ONE_CELL = {"type": "list", "cells": ["C3"]}
LIST_3 = {"type": "list", "cells": ["C3", "A1", "B2"]}


def mk(clue_type: str, **params) -> Clue:
    return Clue(id="clue_A1", owner="A1", type=clue_type, params=params)


def mismatches(clue: Clue, n: int = N, clauses=None) -> List[Tuple[bool, ...]]:
    """Các assignment (của ô clue nhắc tới) mà evaluate và CNF cho kết quả khác nhau."""
    enc = Encoder(n)
    if clauses is None:
        clauses = enc.encode_clue(clue)
        num_vars = n * n + enc.num_aux
    else:
        max_var = max((abs(lit) for c in clauses for lit in c), default=0)
        num_vars = max(n * n, max_var)
    cells = clue_cells(clue, n)
    solver = DPLLSolver()
    bad = []
    for bits in itertools.product([False, True], repeat=len(cells)):
        values = dict(zip(cells, bits))
        assumptions = [
            board.var_of(c, n) if v else -board.var_of(c, n) for c, v in values.items()
        ]
        result = solver.solve(clauses, num_vars, assumptions=assumptions)
        if result.timed_out or result.sat != evaluate(clue, values, n):
            bad.append(bits)
    return bad


class EncoderVsSemanticTest(unittest.TestCase):
    def assert_agree(self, clue: Clue, n: int = N) -> None:
        self.assertEqual(mismatches(clue, n), [], msg=f"{clue.type} {clue.params}")

    def test_fact(self):
        for status in STATUSES:
            self.assert_agree(mk("FACT", target="B2", status=status))

    def test_same_and_different_status(self):
        for clue_type in ("SAME_STATUS", "DIFFERENT_STATUS"):
            with self.subTest(type=clue_type):
                self.assert_agree(mk(clue_type, cell1="A1", cell2="C2"))
                self.assert_agree(mk(clue_type, cell1="C2", cell2="A1"))  # đảo thứ tự ô

    def test_counting_clues_every_k(self):
        for clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            for status in STATUSES:
                for region, size in ((LIST_3, 3), (NEI_A1, 3), (ONE_CELL, 1)):
                    for k in range(size + 1):  # gồm biên k = 0 và k = |R|
                        with self.subTest(type=clue_type, status=status, region=region, k=k):
                            self.assert_agree(mk(clue_type, region=region, k=k, status=status))

    def test_counting_clues_large_region_selected_k(self):
        for clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            for status in STATUSES:
                for k in (0, 3, 4, 8):  # láng giềng ô giữa có 8 ô
                    with self.subTest(type=clue_type, status=status, k=k):
                        self.assert_agree(mk(clue_type, region=NEI_B2, k=k, status=status))

    def test_counting_status_defaults_to_criminal(self):
        for clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            with self.subTest(type=clue_type):
                self.assert_agree(mk(clue_type, region=ROW1, k=1))  # không có status

    def test_counting_clues_on_4x4(self):
        for clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            for region in ({"type": "row", "number": 4}, {"type": "col", "letter": "C"}):
                for k in range(5):
                    with self.subTest(type=clue_type, region=region, k=k):
                        self.assert_agree(mk(clue_type, region=region, k=k), n=4)

    def test_parity_and_compare_on_4x4(self):
        nei_a1 = {"type": "neighbors", "cell": "A1"}  # 3 ô
        row4 = {"type": "row", "number": 4}  # 4 ô
        self.assert_agree(mk("PARITY", region=row4, parity="ODD"), n=4)
        for op in ("GT", "EQ"):
            clue = mk("COMPARE", region1=nei_a1, region2=row4, op=op)
            self.assert_agree(clue, n=4)

    def test_parity_every_region_and_status(self):
        for parity in ("EVEN", "ODD"):
            for status in STATUSES:
                for region in (ONE_CELL, NEI_A1, ROW1, NEI_B2):
                    with self.subTest(parity=parity, status=status, region=region):
                        clue = mk("PARITY", region=region, parity=parity, status=status)
                        self.assert_agree(clue)

    def test_parity_zero_count_is_even(self):
        # assignment toàn Innocent: số Criminal = 0 -> EVEN đúng, ODD sai
        values = {c: False for c in clue_cells(mk("PARITY", region=ROW1, parity="EVEN"), N)}
        for parity, expected in (("EVEN", True), ("ODD", False)):
            clue = mk("PARITY", region=ROW1, parity=parity)
            self.assertEqual(evaluate(clue, values, N), expected)
            self.assertNotIn(tuple(values.values()), mismatches(clue))

    def test_compare_all_operators_and_statuses(self):
        pairs = (
            (ROW1, COLA),  # hai vùng chồng nhau ở A1
            (NEI_A1, ROW3),  # hai vùng rời nhau
            (ONE_CELL, COLA),  # biên: vùng 1 ô
            (COLA, ONE_CELL),  # biên: vùng lớn so với vùng 1 ô
            (ROW2, ROW2),  # biên: hai vùng giống hệt
        )
        for index, (region1, region2) in enumerate(pairs):
            # cặp đầu thử cả hai status, các cặp còn lại chỉ cần CRIMINAL
            statuses = STATUSES if index == 0 else (CRIMINAL,)
            for op in ("GT", "GE", "EQ", "LE", "LT"):
                for status in statuses:
                    with self.subTest(r1=region1, r2=region2, op=op, status=status):
                        clue = mk("COMPARE", region1=region1, region2=region2,
                                  op=op, status=status)
                        self.assert_agree(clue)

    def test_compare_status_defaults_to_criminal(self):
        for op in ("GT", "GE", "EQ", "LE", "LT"):
            with self.subTest(op=op):
                self.assert_agree(mk("COMPARE", region1=ROW1, region2=COLA, op=op))


class HarnessSanityTest(unittest.TestCase):
    """Chứng minh test đối chiếu thật sự bắt được lỗi."""

    def test_dropping_a_clause_is_detected(self):
        clue = mk("EXACTLY", region=ROW2, k=1)  # 4 clause
        for dropped in range(4):
            clauses = Encoder(N).encode_clue(clue)
            del clauses[dropped]
            with self.subTest(dropped=dropped):
                self.assertNotEqual(mismatches(clue, clauses=clauses), [])

    def test_harness_handles_external_clauses_with_aux_vars(self):
        clue = mk("PARITY", region=ROW1, parity="ODD")
        clauses = Encoder(N).encode_clue(clue)   # có 1 biến phụ (var 10)
        self.assertEqual(mismatches(clue, clauses=clauses), [])
        del clauses[0]
        self.assertNotEqual(mismatches(clue, clauses=clauses), [])


if __name__ == "__main__":
    unittest.main()
