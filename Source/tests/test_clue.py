"""Test cho engine/clue.py (việc A2): clue_cells, validate_clue."""
import unittest

from engine.clue import Clue, clue_cells, clue_from_dict, validate_clue

N = 3


def mk(type_: str, owner: str = "A1", **params) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type=type_, params=params)


ROW2 = {"type": "row", "index": 2}
COLB = {"type": "col", "index": "B"}
NEI_A1 = {"type": "neighbors", "cell": "A1"}
NEI_B2 = {"type": "neighbors", "cell": "B2"}


class ClueCellsTest(unittest.TestCase):
    def test_fact_returns_its_cell(self):
        self.assertEqual(clue_cells(mk("FACT", cell="B2", status="CRIMINAL"), N), ["B2"])

    def test_same_and_different_return_both_cells_row_major(self):
        for t in ("SAME", "DIFFERENT"):
            with self.subTest(type=t):
                self.assertEqual(clue_cells(mk(t, a="C1", b="A1"), N), ["A1", "C1"])

    def test_counting_with_row_region(self):
        self.assertEqual(clue_cells(mk("EXACTLY", region=ROW2, k=1), N), ["A2", "B2", "C2"])

    def test_counting_with_col_region(self):
        self.assertEqual(clue_cells(mk("AT_LEAST", region=COLB, k=1), N), ["B1", "B2", "B3"])

    def test_counting_with_corner_neighbors_has_three_cells(self):
        self.assertEqual(clue_cells(mk("AT_MOST", region=NEI_A1, k=1), N), ["B1", "A2", "B2"])

    def test_neighbors_do_not_include_center_cell(self):
        self.assertNotIn("B2", clue_cells(mk("EXACTLY", region=NEI_B2, k=1), N))
        self.assertEqual(len(clue_cells(mk("EXACTLY", region=NEI_B2, k=1), N)), 8)

    def test_cells_region_is_sorted_and_deduplicated(self):
        region = {"type": "cells", "cells": ["C3", "A1", "C3"]}
        self.assertEqual(clue_cells(mk("EXACTLY", region=region, k=1), N), ["A1", "C3"])

    def test_parity_uses_region(self):
        self.assertEqual(clue_cells(mk("PARITY", region=COLB, parity="ODD"), N),
                         ["B1", "B2", "B3"])

    def test_compare_returns_union_of_both_regions_without_duplicates(self):
        clue = mk("COMPARE", left={"type": "row", "index": 1},
                  right={"type": "col", "index": "A"}, op="GT")
        self.assertEqual(clue_cells(clue, N), ["A1", "B1", "C1", "A2", "A3"])

    def test_owner_is_not_included_unless_mentioned(self):
        self.assertNotIn("A1", clue_cells(mk("EXACTLY", owner="A1", region=NEI_A1, k=1), N))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            clue_cells(mk("BOGUS"), N)


class ValidateClueValidTest(unittest.TestCase):
    def test_all_core_and_extension_types_accepted(self):
        good = [
            mk("FACT", cell="B2", status="INNOCENT"),
            mk("SAME", a="A1", b="B2"),
            mk("DIFFERENT", a="A1", b="C3"),
            mk("EXACTLY", region=ROW2, k=2),
            mk("AT_LEAST", region=COLB, k=1),
            mk("AT_MOST", region=NEI_A1, k=2),
            mk("PARITY", region=ROW2, parity="EVEN"),
            mk("COMPARE", left=ROW2, right=COLB, op="LE"),
        ]
        for clue in good:
            with self.subTest(type=clue.type):
                self.assertIsNone(validate_clue(clue, N))

    def test_k_boundaries_zero_and_region_size_accepted(self):
        for k in (0, 3):
            with self.subTest(k=k):
                validate_clue(mk("EXACTLY", region=ROW2, k=k), N)

    def test_single_cell_region_accepted(self):
        validate_clue(mk("EXACTLY", region={"type": "cells", "cells": ["B2"]}, k=1), N)

    def test_clue_from_dict_roundtrip_validates(self):
        clue = clue_from_dict("A1", {"type": "EXACTLY", "region": NEI_A1, "k": 1})
        validate_clue(clue, N)


class ValidateClueInvalidTest(unittest.TestCase):
    def assert_invalid(self, clue: Clue, n: int = N):
        with self.assertRaises(ValueError):
            validate_clue(clue, n)

    def test_unknown_type(self):
        self.assert_invalid(mk("BOGUS"))

    def test_owner_outside_grid(self):
        self.assert_invalid(mk("FACT", owner="D1", cell="A1", status="CRIMINAL"))

    def test_cells_outside_grid_or_malformed(self):
        for bad in ("D1", "A4", "a1", "A01", "", "1A", None, 5):
            with self.subTest(cell=bad):
                self.assert_invalid(mk("FACT", cell=bad, status="CRIMINAL"))

    def test_fact_bad_status(self):
        for bad in ("criminal", "UNKNOWN", None):
            with self.subTest(status=bad):
                self.assert_invalid(mk("FACT", cell="A1", status=bad))

    def test_same_and_different_reject_outside_cell_and_identical_cells(self):
        for t in ("SAME", "DIFFERENT"):
            with self.subTest(type=t, case="outside"):
                self.assert_invalid(mk(t, a="A1", b="D4"))
            with self.subTest(type=t, case="identical"):
                self.assert_invalid(mk(t, a="B2", b="B2"))

    def test_k_out_of_range(self):
        # vùng neighbors của A1 có 3 ô
        for k in (-1, 4):
            with self.subTest(k=k):
                self.assert_invalid(mk("AT_MOST", region=NEI_A1, k=k))

    def test_k_wrong_type(self):
        for bad in (True, 1.0, "1", None):
            with self.subTest(k=bad):
                self.assert_invalid(mk("EXACTLY", region=ROW2, k=bad))

    def test_missing_k_or_region(self):
        self.assert_invalid(mk("EXACTLY", region=ROW2))
        self.assert_invalid(mk("EXACTLY", k=1))

    def test_empty_cells_region(self):
        self.assert_invalid(mk("EXACTLY", region={"type": "cells", "cells": []}, k=0))

    def test_cells_region_with_duplicates(self):
        region = {"type": "cells", "cells": ["A1", "B2", "A1"]}
        self.assert_invalid(mk("EXACTLY", region=region, k=1))

    def test_cells_region_with_outside_cell(self):
        region = {"type": "cells", "cells": ["A1", "D1"]}
        self.assert_invalid(mk("EXACTLY", region=region, k=1))

    def test_row_and_col_outside_grid(self):
        for region in ({"type": "row", "index": 0}, {"type": "row", "index": 4},
                       {"type": "col", "index": "D"}, {"type": "col", "index": "AB"}):
            with self.subTest(region=region):
                self.assert_invalid(mk("EXACTLY", region=region, k=0))

    def test_neighbors_of_cell_outside_grid(self):
        self.assert_invalid(mk("EXACTLY", region={"type": "neighbors", "cell": "E5"}, k=0))

    def test_neighbors_region_empty_on_1x1_grid(self):
        clue = mk("EXACTLY", region={"type": "neighbors", "cell": "A1"}, k=0)
        self.assert_invalid(clue, n=1)

    def test_unknown_region_type(self):
        self.assert_invalid(mk("EXACTLY", region={"type": "diagonal"}, k=0))

    def test_parity_bad_value(self):
        self.assert_invalid(mk("PARITY", region=ROW2, parity="even"))
        self.assert_invalid(mk("PARITY", region=ROW2))

    def test_compare_bad_op_or_region(self):
        self.assert_invalid(mk("COMPARE", left=ROW2, right=COLB, op="NE"))
        self.assert_invalid(mk("COMPARE", left=ROW2, right={"type": "row", "index": 9}, op="GT"))
        self.assert_invalid(mk("COMPARE", left=ROW2, op="GT"))


if __name__ == "__main__":
    unittest.main()