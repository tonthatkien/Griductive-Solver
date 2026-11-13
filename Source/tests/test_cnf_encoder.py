import unittest
import itertools
from math import comb

from logic.cnf_encoder import KB, Encoder
from engine import board
from engine.clue import Clue, resolve_region


class TestEncoderBase(unittest.TestCase):
    def test_first_aux_var_follows_primary_vars(self):
        self.assertEqual(Encoder(3).new_aux(), 10)
        self.assertEqual(Encoder(4).new_aux(), 17)

    def test_new_aux_increments_and_counts(self):
        enc = Encoder(3)
        self.assertEqual([enc.new_aux(), enc.new_aux(), enc.new_aux()], [10, 11, 12])
        self.assertEqual(enc.num_aux, 3)

    def test_literal_of_criminal_is_positive(self):
        self.assertEqual(Encoder(3).literal_of("C2", "CRIMINAL"), 6)

    def test_literal_of_innocent_is_negative(self):
        self.assertEqual(Encoder(3).literal_of("C2", "INNOCENT"), -6)

    def test_literal_of_requires_status(self):
        with self.assertRaises(TypeError):
            Encoder(3).literal_of("A1")

    def test_literal_of_invalid_cell_raises(self):
        for bad in ["D1", "a1", "A0", "A01", ""]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                Encoder(3).literal_of(bad, "CRIMINAL")

    def test_literal_of_bad_status_raises(self):
        for bad in ["criminal", "UNKNOWN", None]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                Encoder(3).literal_of("A1", bad)

    def test_literal_of_asymmetric_cell_catches_row_col_swap(self):
        self.assertEqual(Encoder(4).literal_of("B3", "CRIMINAL"), 10)
        self.assertEqual(Encoder(4).literal_of("B3", "INNOCENT"), -10)

    def test_two_encoders_have_independent_aux_counters(self):
        e1, e2 = Encoder(3), Encoder(3)
        e1.new_aux()
        self.assertEqual(e2.new_aux(), 10)
        self.assertEqual(e1.new_aux(), 11)

    def test_new_aux_does_not_change_num_primary(self):
        enc = Encoder(3)
        enc.new_aux()
        self.assertEqual(enc.num_primary, 9)

    def test_empty_kb_has_zero_clauses(self):
        kb = KB(clauses=[], num_primary=9, num_aux=0)
        self.assertEqual(kb.num_clauses, 0)
        self.assertEqual(kb.num_vars, 9)

    def test_kb_counts(self):
        kb = KB(clauses=[[1, -2], [3]], num_primary=9, num_aux=2)
        self.assertEqual(kb.num_vars, 11)
        self.assertEqual(kb.num_clauses, 2)

    def test_num_primary_is_n_squared(self):
        self.assertEqual(Encoder(3).num_primary, 9)
        self.assertEqual(Encoder(5).num_primary, 25)

def make_clue(clue_type, **params):
    return Clue(id="clue_test", owner="A1", type=clue_type, params=params)


def satisfies(clauses, model):
    """True nếu model (dict var -> bool) thỏa mọi clause"""
    return all(any(model[abs(lit)] == (lit > 0) for lit in c) for c in clauses)


class TestEncodeBinaryClues(unittest.TestCase):
    def test_fact_criminal_is_positive_unit_clause(self):
        clue = make_clue("FACT", target="B2", status="CRIMINAL")
        self.assertEqual(Encoder(3).encode_clue(clue), [[5]])

    def test_fact_innocent_is_negative_unit_clause(self):
        clue = make_clue("FACT", target="B2", status="INNOCENT")
        self.assertEqual(Encoder(3).encode_clue(clue), [[-5]])

    def test_fact_without_status_raises(self):
        with self.assertRaises(ValueError):
            Encoder(3).encode_clue(make_clue("FACT", target="B2"))

    def test_same_exact_clauses(self):
        clue = make_clue("SAME_STATUS", cell1="A1", cell2="C2")
        self.assertEqual(Encoder(3).encode_clue(clue), [[-1, 6], [1, -6]])

    def test_different_exact_clauses(self):
        clue = make_clue("DIFFERENT_STATUS", cell1="A1", cell2="C2")
        self.assertEqual(Encoder(3).encode_clue(clue), [[1, 6], [-1, -6]])

    def test_same_truth_table(self):
        clauses = Encoder(3).encode_clue(make_clue("SAME_STATUS", cell1="A1", cell2="C2"))
        for a, b in itertools.product([False, True], repeat=2):
            self.assertEqual(satisfies(clauses, {1: a, 6: b}), a == b)

    def test_different_truth_table(self):
        clauses = Encoder(3).encode_clue(make_clue("DIFFERENT_STATUS", cell1="A1", cell2="C2"))
        for a, b in itertools.product([False, True], repeat=2):
            self.assertEqual(satisfies(clauses, {1: a, 6: b}), a != b)

    def test_binary_clues_use_no_aux_vars(self):
        enc = Encoder(3)
        enc.encode_clue(make_clue("FACT", target="A1", status="CRIMINAL"))
        enc.encode_clue(make_clue("SAME_STATUS", cell1="A1", cell2="B1"))
        enc.encode_clue(make_clue("DIFFERENT_STATUS", cell1="A1", cell2="B1"))
        self.assertEqual(enc.num_aux, 0)

    def test_binary_clue_with_same_cell_raises(self):
        for clue_type in ("SAME_STATUS", "DIFFERENT_STATUS"):
            with self.assertRaises(ValueError, msg=clue_type):
                Encoder(3).encode_clue(make_clue(clue_type, cell1="A1", cell2="A1"))

    def test_binary_clue_with_cell_outside_grid_raises(self):
        with self.assertRaises(ValueError):
            Encoder(3).encode_clue(make_clue("SAME_STATUS", cell1="A1", cell2="D1"))

    def test_unknown_clue_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            Encoder(3).encode_clue(make_clue("BOGUS"))

ROW2 = {"type": "row", "number": 2}
NEI_A1 = {"type": "neighbors", "cell": "A1"}
NEI_B2 = {"type": "neighbors", "cell": "B2"}


def holds(clue_type, count, k):
    """Giá trị đúng của điều kiện đếm, viết độc lập với encoder"""
    return {"EXACTLY": count == k, "AT_LEAST": count >= k, "AT_MOST": count <= k}[clue_type]


class TestEncodeCountingClues(unittest.TestCase):
    def test_at_most_exact_clauses(self):
        clue = make_clue("AT_MOST", region=ROW2, k=1)  # A2, B2, C2 = vars 4, 5, 6
        self.assertEqual(Encoder(3).encode_clue(clue), [[-4, -5], [-4, -6], [-5, -6]])

    def test_at_least_exact_clauses(self):
        clue = make_clue("AT_LEAST", region=ROW2, k=1)
        self.assertEqual(Encoder(3).encode_clue(clue), [[4, 5, 6]])

    def test_exactly_is_at_most_then_at_least(self):
        clue = make_clue("EXACTLY", region=ROW2, k=1)
        self.assertEqual(Encoder(3).encode_clue(clue),
                         [[-4, -5], [-4, -6], [-5, -6], [4, 5, 6]])

    def test_exactly_zero_forces_all_innocent(self):
        clue = make_clue("EXACTLY", region=NEI_A1, k=0)  # B1, A2, B2 = vars 2, 4, 5
        self.assertEqual(Encoder(3).encode_clue(clue), [[-2], [-4], [-5]])

    def test_exactly_region_size_forces_all_criminal(self):
        clue = make_clue("EXACTLY", region=NEI_A1, k=3)
        self.assertEqual(Encoder(3).encode_clue(clue), [[2], [4], [5]])

    def test_trivial_bounds_generate_no_clause(self):
        self.assertEqual(Encoder(3).encode_clue(make_clue("AT_LEAST", region=ROW2, k=0)), [])
        self.assertEqual(Encoder(3).encode_clue(make_clue("AT_MOST", region=ROW2, k=3)), [])

    def test_single_cell_region(self):
        region = {"type": "list", "cells": ["B2"]}
        self.assertEqual(Encoder(3).encode_clue(make_clue("EXACTLY", region=region, k=1)), [[5]])
        self.assertEqual(Encoder(3).encode_clue(make_clue("EXACTLY", region=region, k=0)), [[-5]])

    def test_innocent_status_flips_literals(self):
        clue = make_clue("AT_LEAST", region=ROW2, k=1, status="INNOCENT")
        self.assertEqual(Encoder(3).encode_clue(clue), [[-4, -5, -6]])

    def test_clause_counts_match_formula(self):
        m = 8  # láng giềng của ô giữa 3x3
        for k in range(m + 1):
            with self.subTest(k=k):
                enc = Encoder(3)
                at_most = enc.encode_clue(make_clue("AT_MOST", region=NEI_B2, k=k))
                at_least = enc.encode_clue(make_clue("AT_LEAST", region=NEI_B2, k=k))
                exactly = enc.encode_clue(make_clue("EXACTLY", region=NEI_B2, k=k))
                self.assertEqual(len(at_most), comb(m, k + 1))
                self.assertEqual(len(at_least), comb(m, m - k + 1))
                self.assertEqual(len(exactly), len(at_most) + len(at_least))

    def test_truth_table_all_assignments(self):
        for clue_type in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            for status in ("CRIMINAL", "INNOCENT"):
                for region in (ROW2, NEI_A1):
                    cells = resolve_region(region, 3)
                    for k in range(len(cells) + 1):
                        clue = make_clue(clue_type, region=region, k=k, status=status)
                        clauses = Encoder(3).encode_clue(clue)
                        for values in itertools.product([False, True], repeat=len(cells)):
                            model = {v: False for v in range(1, 10)}
                            for cell, val in zip(cells, values):
                                model[board.var_of(cell, 3)] = val
                            count = sum(v == (status == "CRIMINAL") for v in values)
                            with self.subTest(t=clue_type, s=status, k=k, v=values):
                                self.assertEqual(satisfies(clauses, model),
                                                 holds(clue_type, count, k))

    def test_counting_clues_use_no_aux_vars(self):
        enc = Encoder(3)
        for t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            enc.encode_clue(make_clue(t, region=NEI_B2, k=2))
        self.assertEqual(enc.num_aux, 0)

    def test_encoding_is_deterministic(self):
        clue = make_clue("EXACTLY", region=NEI_B2, k=3)
        self.assertEqual(Encoder(3).encode_clue(clue), Encoder(3).encode_clue(clue))

    def test_status_defaults_to_criminal_when_missing(self):
        at_least = make_clue("AT_LEAST", region=ROW2, k=1)  # không có status
        self.assertEqual(Encoder(3).encode_clue(at_least), [[4, 5, 6]])
        at_most = make_clue("AT_MOST", region=ROW2, k=1)
        self.assertEqual(Encoder(3).encode_clue(at_most), [[-4, -5], [-4, -6], [-5, -6]])

    def test_list_region_order_does_not_change_clauses(self):
        shuffled = {"type": "list", "cells": ["C3", "A1", "B2"]}   # vars 9, 1, 5
        ordered = {"type": "list", "cells": ["A1", "B2", "C3"]}
        clauses = Encoder(3).encode_clue(make_clue("AT_MOST", region=shuffled, k=1))
        self.assertEqual(clauses, [[-1, -5], [-1, -9], [-5, -9]])   # row-major, không theo input
        self.assertEqual(clauses, Encoder(3).encode_clue(make_clue("AT_MOST", region=ordered, k=1)))

    def test_k_out_of_range_raises(self):
        for k in (-1, 4):
            with self.assertRaises(ValueError, msg=k):
                Encoder(3).encode_clue(make_clue("EXACTLY", region=NEI_A1, k=k))

    def test_region_cell_outside_grid_raises(self):
        region = {"type": "list", "cells": ["A1", "D1"]}
        with self.assertRaises(ValueError):
            Encoder(3).encode_clue(make_clue("AT_MOST", region=region, k=1))


if __name__ == "__main__":
    unittest.main()
