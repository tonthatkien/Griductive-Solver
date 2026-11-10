"""Test cho engine/clue.py (việc A2): clue_cells, validate_clue."""
import unittest

from engine.clue import Clue, clue_cells, clue_from_dict, clue_status, validate_clue

N = 3


def mk(type_: str, owner: str = "A1", **params) -> Clue:
    return Clue(id=f"clue_{owner}", owner=owner, type=type_, params=params)


ROW2 = {"type": "row", "number": 2}
COLB = {"type": "col", "letter": "B"}
NEI_A1 = {"type": "neighbors", "cell": "A1"}
NEI_B2 = {"type": "neighbors", "cell": "B2"}


class ClueCellsTest(unittest.TestCase):
    def test_fact_returns_its_cell(self):
        self.assertEqual(clue_cells(mk("FACT", target="B2", status="CRIMINAL"), N), ["B2"])

    def test_same_and_different_return_both_cells_row_major(self):
        for t in ("SAME_STATUS", "DIFFERENT_STATUS"):
            with self.subTest(type=t):
                self.assertEqual(clue_cells(mk(t, cell1="C1", cell2="A1"), N), ["A1", "C1"])

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
        region = {"type": "list", "cells": ["C3", "A1", "C3"]}
        self.assertEqual(clue_cells(mk("EXACTLY", region=region, k=1), N), ["A1", "C3"])

    def test_parity_uses_region(self):
        self.assertEqual(clue_cells(mk("PARITY", region=COLB, parity="ODD"), N),
                         ["B1", "B2", "B3"])

    def test_compare_returns_union_of_both_regions_without_duplicates(self):
        clue = mk("COMPARE", region1={"type": "row", "number": 1},
                  region2={"type": "col", "letter": "A"}, op="GT")
        self.assertEqual(clue_cells(clue, N), ["A1", "B1", "C1", "A2", "A3"])

    def test_owner_is_not_included_unless_mentioned(self):
        self.assertNotIn("A1", clue_cells(mk("EXACTLY", owner="A1", region=NEI_A1, k=1), N))

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            clue_cells(mk("BOGUS"), N)


class ValidateClueValidTest(unittest.TestCase):
    def test_all_core_and_extension_types_accepted(self):
        good = [
            mk("FACT", target="B2", status="INNOCENT"),
            mk("SAME_STATUS", cell1="A1", cell2="B2"),
            mk("DIFFERENT_STATUS", cell1="A1", cell2="C3"),
            mk("EXACTLY", region=ROW2, k=2),
            mk("AT_LEAST", region=COLB, k=1),
            mk("AT_MOST", region=NEI_A1, k=2),
            mk("PARITY", region=ROW2, parity="EVEN"),
            mk("COMPARE", region1=ROW2, region2=COLB, op="LE"),
        ]
        for clue in good:
            with self.subTest(type=clue.type):
                self.assertIsNone(validate_clue(clue, N))

    def test_k_boundaries_zero_and_region_size_accepted(self):
        for k in (0, 3):
            with self.subTest(k=k):
                validate_clue(mk("EXACTLY", region=ROW2, k=k), N)

    def test_single_cell_region_accepted(self):
        validate_clue(mk("EXACTLY", region={"type": "list", "cells": ["B2"]}, k=1), N)

    def test_status_is_optional_and_defaults_to_criminal_for_counting_types(self):
        for clue in (
            mk("EXACTLY", region=ROW2, k=1),
            mk("AT_LEAST", region=ROW2, k=1),
            mk("AT_MOST", region=ROW2, k=1),
            mk("PARITY", region=ROW2, parity="EVEN"),
            mk("COMPARE", region1=ROW2, region2=COLB, op="GT"),
        ):
            with self.subTest(type=clue.type):
                validate_clue(clue, N)
                self.assertEqual(clue_status(clue), "CRIMINAL")

    def test_pair_types_ignore_status_and_clue_status_rejects_them(self):
        for t in ("SAME_STATUS", "DIFFERENT_STATUS"):
            with self.subTest(type=t):
                clue = mk(t, cell1="A1", cell2="B2")
                validate_clue(clue, N)
                with self.assertRaises(ValueError):
                    clue_status(clue)

    def test_clue_status_fact_returns_given_status(self):
        self.assertEqual(clue_status(mk("FACT", target="A1", status="INNOCENT")), "INNOCENT")

    def test_status_innocent_accepted_on_every_type_that_has_it(self):
        for clue in (
            mk("FACT", target="B2", status="INNOCENT"),
            mk("EXACTLY", region=ROW2, k=1, status="INNOCENT"),
            mk("AT_LEAST", region=ROW2, k=1, status="INNOCENT"),
            mk("AT_MOST", region=ROW2, k=1, status="INNOCENT"),
            mk("PARITY", region=ROW2, parity="ODD", status="INNOCENT"),
            mk("COMPARE", region1=ROW2, region2=COLB, op="GT", status="INNOCENT"),
        ):
            with self.subTest(type=clue.type):
                validate_clue(clue, N)
                self.assertEqual(clue_status(clue), "INNOCENT")

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
                self.assert_invalid(mk("FACT", target=bad, status="CRIMINAL"))

    def test_fact_requires_status(self):
        self.assert_invalid(mk("FACT", target="A1"))
        with self.assertRaises(ValueError):
            clue_status(mk("FACT", target="A1"))

    def test_fact_bad_status(self):
        for bad in ("criminal", "UNKNOWN", None):
            with self.subTest(status=bad):
                self.assert_invalid(mk("FACT", target="A1", status=bad))

    def test_same_and_different_reject_outside_cell_and_identical_cells(self):
        for t in ("SAME_STATUS", "DIFFERENT_STATUS"):
            with self.subTest(type=t, case="outside"):
                self.assert_invalid(mk(t, cell1="A1", cell2="D4"))
            with self.subTest(type=t, case="identical"):
                self.assert_invalid(mk(t, cell1="B2", cell2="B2"))

    def test_bad_status_on_non_fact_types(self):
        for clue in (
            mk("EXACTLY", region=ROW2, k=1, status="innocent"),
            mk("PARITY", region=ROW2, parity="ODD", status=None),
            mk("COMPARE", region1=ROW2, region2=COLB, op="GT", status="UNKNOWN"),
        ):
            with self.subTest(type=clue.type):
                self.assert_invalid(clue)

    def test_old_key_names_are_rejected(self):
        self.assert_invalid(mk("FACT", cell="A1", status="CRIMINAL"))
        self.assert_invalid(mk("SAME", a="A1", b="B2"))
        self.assert_invalid(mk("EXACTLY", region={"type": "row", "index": 2}, k=1))
        self.assert_invalid(mk("EXACTLY", region={"type": "cells", "cells": ["A1"]}, k=1))
        self.assert_invalid(mk("COMPARE", left=ROW2, right=COLB, op="GT"))

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
        self.assert_invalid(mk("EXACTLY", region={"type": "list", "cells": []}, k=0))

    def test_cells_region_with_duplicates(self):
        region = {"type": "list", "cells": ["A1", "B2", "A1"]}
        self.assert_invalid(mk("EXACTLY", region=region, k=1))

    def test_cells_region_with_outside_cell(self):
        region = {"type": "list", "cells": ["A1", "D1"]}
        self.assert_invalid(mk("EXACTLY", region=region, k=1))

    def test_row_and_col_outside_grid(self):
        for region in ({"type": "row", "number": 0}, {"type": "row", "number": 4},
                       {"type": "col", "letter": "D"}, {"type": "col", "letter": "AB"}):
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
        self.assert_invalid(mk("COMPARE", region1=ROW2, region2=COLB, op="NE"))
        self.assert_invalid(mk("COMPARE", region1=ROW2, region2={"type": "row", "number": 9}, op="GT"))
        self.assert_invalid(mk("COMPARE", region1=ROW2, op="GT"))


if __name__ == "__main__":
    unittest.main()