"""Test C4: encode PARITY. Duyệt mọi assignment của vùng, đếm số cách gán biến phụ thỏa CNF"""
import itertools
import unittest

from engine import board
from engine.clue import Clue, clue_cells
from logic.cnf_encoder import Encoder

N = 3
ROW1 = {"type": "row", "number": 1}
COLB = {"type": "col", "letter": "B"}
NEI_B2 = {"type": "neighbors", "cell": "B2"}
NEI_A1 = {"type": "neighbors", "cell": "A1"}
ONE_CELL = {"type": "list", "cells": ["B2"]}


def mk(parity: str, region: dict, **extra) -> Clue:
    params = {"region": region, "parity": parity, **extra}
    return Clue(id="clue_A1", owner="A1", type="PARITY", params=params)


def count_extensions(clauses, fixed, aux_vars) -> int:
    """Số cách gán biến phụ để (fixed + aux) thỏa mọi clause"""
    total = 0
    for values in itertools.product([False, True], repeat=len(aux_vars)):
        assign = dict(fixed)
        assign.update(zip(aux_vars, values))
        if all(any(assign[abs(l)] == (l > 0) for l in c) for c in clauses):
            total += 1
    return total


class TestEncodeParity(unittest.TestCase):
    def check_all_assignments(self, clue: Clue) -> None:
        """Với mọi assignment của vùng: thỏa parity <=> đúng 1 cách gán biến phụ, ngược lại 0.
        Chạy qua cả encode_parity (trực tiếp) và encode_clue (qua dispatch)"""
        cells = clue_cells(clue, N)
        target = clue.params.get("status", "CRIMINAL") == "CRIMINAL"
        for method in ("encode_parity", "encode_clue"):
            enc = Encoder(N)
            clauses = getattr(enc, method)(clue)
            aux_vars = list(range(board.first_aux_var(N), board.first_aux_var(N) + enc.num_aux))
            for values in itertools.product([False, True], repeat=len(cells)):
                fixed = {board.var_of(c, N): v for c, v in zip(cells, values)}
                count = sum(1 for v in values if v == target)
                ok = count % 2 == 1 if clue.params["parity"] == "ODD" else count % 2 == 0
                with self.subTest(method=method, values=values):
                    self.assertEqual(count_extensions(clauses, fixed, aux_vars), 1 if ok else 0)

    def test_odd_on_row_matches_parity_for_every_assignment(self):
        self.check_all_assignments(mk("ODD", ROW1))

    def test_even_on_row_matches_parity_for_every_assignment(self):
        self.check_all_assignments(mk("EVEN", ROW1))

    def test_even_and_odd_on_eight_neighbors(self):
        for parity in ("EVEN", "ODD"):
            with self.subTest(parity=parity):
                self.check_all_assignments(mk(parity, NEI_B2))

    def test_two_cell_region_needs_no_aux(self):
        clue = mk("ODD", {"type": "list", "cells": ["A1", "C3"]})
        self.check_all_assignments(clue)

    def test_status_innocent_counts_false_cells(self):
        for parity in ("EVEN", "ODD"):
            with self.subTest(parity=parity):
                self.check_all_assignments(mk(parity, COLB, status="INNOCENT"))

    def test_single_cell_region(self):
        self.assertEqual(Encoder(N).encode_parity(mk("ODD", ONE_CELL)), [[5]])
        self.assertEqual(Encoder(N).encode_parity(mk("EVEN", ONE_CELL)), [[-5]])
        self.assertEqual(Encoder(N).encode_parity(mk("ODD", ONE_CELL, status="INNOCENT")), [[-5]])

    def test_zero_criminals_is_even_not_odd(self):
        for parity, expected in (("EVEN", 1), ("ODD", 0)):
            enc = Encoder(N)
            clauses = enc.encode_parity(mk(parity, ROW1))
            fixed = {1: False, 2: False, 3: False}
            aux = list(range(10, 10 + enc.num_aux))
            self.assertEqual(count_extensions(clauses, fixed, aux), expected, parity)

    def test_clause_and_aux_counts(self):
        # m ô: m = 1 -> 1 clause, 0 aux; m >= 2 -> 4m - 6 clause, m - 2 aux
        cases = [(ONE_CELL, 1, 0), (NEI_A1, 6, 1), (ROW1, 6, 1), (NEI_B2, 26, 6)]
        for region, num_clauses, num_aux in cases:
            enc = Encoder(N)
            clauses = enc.encode_parity(mk("ODD", region))
            with self.subTest(region=region):
                self.assertEqual(len(clauses), num_clauses)
                self.assertEqual(enc.num_aux, num_aux)

    def test_two_cell_region_has_two_clauses_and_no_aux(self):
        enc = Encoder(N)
        clauses = enc.encode_parity(mk("EVEN", {"type": "list", "cells": ["A1", "B1"]}))
        self.assertEqual(len(clauses), 2)
        self.assertEqual(enc.num_aux, 0)

    def test_aux_vars_start_after_primary_and_are_separate(self):
        enc = Encoder(N)
        clauses = enc.encode_parity(mk("ODD", NEI_B2))
        used = {abs(l) for c in clauses for l in c}
        self.assertEqual(sorted(v for v in used if v > 9), list(range(10, 16)))
        self.assertNotIn(5, used)  # ô B2 không thuộc vùng neighbors của chính nó

    def test_second_call_continues_aux_numbering(self):
        enc = Encoder(N)
        enc.encode_parity(mk("ODD", ROW1))
        self.assertEqual(enc.num_aux, 1)
        enc.encode_parity(mk("EVEN", ROW1))
        self.assertEqual(enc.num_aux, 2)
        self.assertEqual(enc.new_aux(), 12)

    def test_encoding_is_deterministic(self):
        a = Encoder(N).encode_parity(mk("ODD", NEI_B2))
        b = Encoder(N).encode_parity(mk("ODD", NEI_B2))
        self.assertEqual(a, b)

    def test_wrong_clue_type_raises(self):
        clue = Clue(id="c", owner="A1", type="EXACTLY", params={"region": ROW1, "k": 1})
        with self.assertRaises(ValueError):
            Encoder(N).encode_parity(clue)

    def test_invalid_parity_or_region_raises(self):
        for clue in (mk("even", ROW1), mk("ODD", {"type": "row", "number": 9})):
            with self.assertRaises(ValueError):
                Encoder(N).encode_parity(clue)


class TestEncodeClueDispatchesParity(unittest.TestCase):
    def test_encode_clue_does_not_reject_parity(self):
        for parity in ("EVEN", "ODD"):
            with self.subTest(parity=parity):
                self.assertTrue(Encoder(N).encode_clue(mk(parity, ROW1)))

    def test_encode_clue_matches_encode_parity(self):
        for parity in ("EVEN", "ODD"):
            for region in (ONE_CELL, ROW1, NEI_A1, NEI_B2):
                for extra in ({}, {"status": "INNOCENT"}):
                    clue = mk(parity, region, **extra)
                    via_clue, direct = Encoder(N), Encoder(N)
                    with self.subTest(parity=parity, region=region, extra=extra):
                        self.assertEqual(via_clue.encode_clue(clue), direct.encode_parity(clue))
                        self.assertEqual(via_clue.num_aux, direct.num_aux)

    def test_encode_clue_continues_aux_numbering_across_calls(self):
        enc = Encoder(N)
        enc.encode_clue(mk("ODD", ROW1))
        enc.encode_clue(mk("EVEN", ROW1))
        self.assertEqual(enc.num_aux, 2)
        self.assertEqual(enc.new_aux(), 12)

    def test_encode_clue_still_validates_parity_clue(self):
        for clue in (mk("even", ROW1), mk("ODD", {"type": "row", "number": 9})):
            with self.assertRaises(ValueError):
                Encoder(N).encode_clue(clue)


if __name__ == "__main__":
    unittest.main()
