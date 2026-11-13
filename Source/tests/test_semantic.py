import itertools
import json
from pathlib import Path
from typing import Dict, List
import unittest

from engine import board
from engine.clue import Clue
from engine.constants import CRIMINAL, INNOCENT
from logic.semantic import (
    count_status_matches,
    eval_at_least,
    eval_at_most,
    eval_compare,
    eval_different_status,
    eval_exactly,
    eval_fact,
    eval_parity,
    eval_same_status,
    evaluate,
    evaluate_all,
    resolve_region_cells,
)


class TestSemanticEvaluator(unittest.TestCase):
    def setUp(self):
        self.n = 3
        # Lưới 3x3 mẫu:
        # A1=T (C), B1=F (I), C1=F (I)
        # A2=F (I), B2=T (C), C2=T (C)
        # A3=F (I), B3=F (I), C3=T (C)
        self.assignment = {
            "A1": True,  "B1": False, "C1": False,
            "A2": False, "B2": True,  "C2": True,
            "A3": False, "B3": False, "C3": True,
        }

    # ------------------ Region & Helper Tests ------------------
    def test_resolve_region_row_and_col(self):
        self.assertEqual(
            resolve_region_cells({"type": "row", "number": 1}, self.n),
            ["A1", "B1", "C1"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "row", "index": 2}, self.n),
            ["A2", "B2", "C2"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "col", "letter": "B"}, self.n),
            ["B1", "B2", "B3"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "col", "index": "C"}, self.n),
            ["C1", "C2", "C3"],
        )

    def test_resolve_region_neighbors_and_list(self):
        # A1 có 3 ô kề: B1, A2, B2
        self.assertEqual(
            resolve_region_cells({"type": "neighbors", "cell": "A1"}, self.n),
            ["B1", "A2", "B2"],
        )
        # B2 có 8 ô kề xung quanh
        expected_b2_neighbors = ["A1", "B1", "C1", "A2", "C2", "A3", "B3", "C3"]
        self.assertEqual(
            resolve_region_cells({"type": "neighbors", "cell": "B2"}, self.n),
            expected_b2_neighbors,
        )
        # type list / cells
        self.assertEqual(
            resolve_region_cells({"type": "list", "cells": ["C3", "A1"]}, self.n),
            ["A1", "C3"],
        )

    def test_resolve_region_rejects_empty_region(self):
        # Vùng rỗng bắt buộc phải raise ValueError theo REVIEW_GUIDE.md
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "list", "cells": []}, self.n)

        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "cells", "cells": []}, self.n)

    def test_resolve_region_rejects_duplicate_cells(self):
        # Ô trùng trong region list phải bị từ chối theo INTERFACES.md 2.4 quy tắc 8
        bad_duplicates = [
            {"type": "list", "cells": ["A1", "A1"]},
            {"type": "cells", "cells": ["B2", "C3", "B2"]},
        ]
        for region in bad_duplicates:
            with self.assertRaises(ValueError, msg=f"Không bắt lỗi ô trùng trong {region}"):
                resolve_region_cells(region, self.n)

        # Kiểm tra trực tiếp qua hàm evaluate() với clue chứa ô trùng
        clue_dup = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["A1", "A1"]},
            "k": 1,
            "status": "CRIMINAL",
        }
        with self.assertRaises(ValueError):
            evaluate(clue_dup, self.assignment, self.n)

    def test_resolve_region_rejects_invalid_row_and_col(self):
        # Hàng không phải int (float, str, bool, ngoài lưới)
        bad_rows = [1.5, "1", True, False, 0, 4]
        for bad_r in bad_rows:
            with self.assertRaises(ValueError, msg=f"Row={bad_r!r} không bị bắt lỗi"):
                resolve_region_cells({"type": "row", "number": bad_r}, self.n)

        # Kiểm tra trực tiếp qua hàm evaluate() với number=1.5
        clue_float_row = {
            "type": "EXACTLY",
            "region": {"type": "row", "number": 1.5},
            "k": 1,
            "status": "CRIMINAL",
        }
        with self.assertRaises(ValueError):
            evaluate(clue_float_row, self.assignment, self.n)

        # Cột không phải chữ cái hoa 1 ký tự hoặc ngoài lưới
        bad_cols = ["b", "AB", 1, True, "D", ""]
        for bad_c in bad_cols:
            with self.assertRaises(ValueError, msg=f"Col={bad_c!r} không bị bắt lỗi"):
                resolve_region_cells({"type": "col", "letter": bad_c}, self.n)

    def test_resolve_region_rejects_invalid_cell(self):
        # Ô ngoài lưới
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "list", "cells": ["Z9"]}, self.n)

        # Phần tử không hash được (như list, dict) hoặc không phải string
        unhashable_cases = [[["A1"]], [{"a": 1}], [123], [None]]
        for bad_cells in unhashable_cases:
            with self.assertRaises(ValueError, msg=f"Cells={bad_cells!r} phải ném ValueError"):
                resolve_region_cells({"type": "list", "cells": bad_cells}, self.n)

    def test_count_status_matches(self):
        row2 = ["A2", "B2", "C2"]  # False, True, True
        self.assertEqual(count_status_matches(row2, CRIMINAL, self.assignment), 2)
        self.assertEqual(count_status_matches(row2, INNOCENT, self.assignment), 1)

    def test_count_status_missing_cell_raises_key_error(self):
        with self.assertRaises(KeyError):
            count_status_matches(["A1", "Z9"], CRIMINAL, self.assignment)

    def test_assignment_rejects_non_bool_values(self):
        # Giá trị trong assignment sai kiểu bool (như chuỗi "False", số 1, 0, None)
        # phải bị ném TypeError thay vì âm thầm ép kiểu bằng bool()
        bad_values = ["False", "True", 0, 1, None, [True]]
        clue_fact = {"type": "FACT", "target": "A1", "status": "CRIMINAL"}
        clue_same = {"type": "SAME_STATUS", "cell1": "A1", "cell2": "B1"}
        clue_exact = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["A1"]},
            "k": 1,
            "status": "CRIMINAL",
        }

        for bad_val in bad_values:
            bad_asg = dict(self.assignment)
            bad_asg["A1"] = bad_val

            with self.assertRaises(TypeError, msg=f"Val={bad_val!r} không bắt trong FACT"):
                eval_fact(clue_fact, bad_asg, self.n)

            with self.assertRaises(TypeError, msg=f"Val={bad_val!r} không bắt trong SAME"):
                eval_same_status(clue_same, bad_asg, self.n)

            with self.assertRaises(TypeError, msg=f"Val={bad_val!r} không bắt trong EXACTLY"):
                eval_exactly(clue_exact, bad_asg, self.n)

            with self.assertRaises(TypeError, msg=f"Val={bad_val!r} không bắt qua evaluate()"):
                evaluate(clue_fact, bad_asg, self.n)

    # ------------------ Core Clues (Task D5) ------------------
    def test_eval_fact(self):
        # A1 là Criminal (True)
        clue_true = {"type": "FACT", "target": "A1", "status": "CRIMINAL"}
        self.assertTrue(eval_fact(clue_true, self.assignment, self.n))
        self.assertTrue(evaluate(clue_true, self.assignment, self.n))

        # B1 là Innocent (False)
        clue_b1_inn = {"type": "FACT", "target": "B1", "status": "INNOCENT"}
        self.assertTrue(eval_fact(clue_b1_inn, self.assignment, self.n))

        # Khẳng định sai
        clue_wrong = {"type": "FACT", "target": "A1", "status": "INNOCENT"}
        self.assertFalse(eval_fact(clue_wrong, self.assignment, self.n))

        # Hỗ trợ cell thay vì target
        clue_cell_key = {"type": "FACT", "cell": "A1", "status": "CRIMINAL"}
        self.assertTrue(eval_fact(clue_cell_key, self.assignment, self.n))

        # Thiếu status bắt buộc phải raise ValueError
        bad_fact = {"type": "FACT", "target": "A1"}
        with self.assertRaises(ValueError):
            eval_fact(bad_fact, self.assignment, self.n)

        # Ô target ngoài lưới hoặc sai kiểu chuỗi phải raise ValueError
        bad_targets = ["Z9", 123, True, ["A1"]]
        for bad_t in bad_targets:
            with self.assertRaises(ValueError, msg=f"Target={bad_t!r} không bị bắt lỗi"):
                eval_fact(
                    {"type": "FACT", "target": bad_t, "status": "CRIMINAL"},
                    self.assignment,
                    self.n,
                )

    def test_eval_same_status(self):
        # B1 (F) và C1 (F) cùng status
        clue_same = {"type": "SAME_STATUS", "cell1": "B1", "cell2": "C1"}
        self.assertTrue(eval_same_status(clue_same, self.assignment, self.n))
        self.assertTrue(evaluate(clue_same, self.assignment, self.n))

        # B2 (T) và C2 (T) cùng status
        clue_same_t = {"type": "SAME", "a": "B2", "b": "C2"}
        self.assertTrue(eval_same_status(clue_same_t, self.assignment, self.n))

        # A1 (T) và B1 (F) khác status
        clue_diff = {"type": "SAME_STATUS", "cell1": "A1", "cell2": "B1"}
        self.assertFalse(eval_same_status(clue_diff, self.assignment, self.n))

        # Trùng 2 ô (cell1 == cell2) phải raise ValueError
        with self.assertRaises(ValueError):
            eval_same_status(
                {"type": "SAME_STATUS", "cell1": "A1", "cell2": "A1"},
                self.assignment,
                self.n,
            )

        # Ô sai kiểu chuỗi (số, list) phải raise ValueError
        with self.assertRaises(ValueError):
            eval_same_status(
                {"type": "SAME_STATUS", "cell1": 123, "cell2": "B1"},
                self.assignment,
                self.n,
            )

    def test_eval_different_status(self):
        # A1 (T) và B1 (F) khác status
        clue_diff = {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "B1"}
        self.assertTrue(eval_different_status(clue_diff, self.assignment, self.n))
        self.assertTrue(evaluate(clue_diff, self.assignment, self.n))

        # B1 (F) và C1 (F) cùng status -> different_status là False
        clue_same = {"type": "DIFFERENT", "a": "B1", "b": "C1"}
        self.assertFalse(eval_different_status(clue_same, self.assignment, self.n))

        # Trùng 2 ô phải raise ValueError
        with self.assertRaises(ValueError):
            eval_different_status(
                {"type": "DIFFERENT_STATUS", "cell1": "B2", "cell2": "B2"},
                self.assignment,
                self.n,
            )

        # Ô sai kiểu chuỗi phải raise ValueError
        with self.assertRaises(ValueError):
            eval_different_status(
                {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": 456},
                self.assignment,
                self.n,
            )

    def test_eval_exactly(self):
        # Cột C: C1=F, C2=T, C3=T -> Criminal = 2, Innocent = 1
        clue_c_crim = {
            "type": "EXACTLY",
            "region": {"type": "col", "letter": "C"},
            "k": 2,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_exactly(clue_c_crim, self.assignment, self.n))

        clue_c_inn = {
            "type": "EXACTLY",
            "region": {"type": "col", "letter": "C"},
            "k": 1,
            "status": "INNOCENT",
        }
        self.assertTrue(eval_exactly(clue_c_inn, self.assignment, self.n))

    def test_eval_exactly_edge_cases(self):
        # Biên k = 0
        clue_k0_false = {
            "type": "EXACTLY",
            "region": {"type": "row", "number": 1},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_exactly(clue_k0_false, self.assignment, self.n))

        clue_k0_true = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["B1", "C1"]},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_exactly(clue_k0_true, self.assignment, self.n))

        # Biên k = |R|
        clue_k_max_true = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["B2", "C2"]},
            "k": 2,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_exactly(clue_k_max_true, self.assignment, self.n))

        clue_k_max_false = {
            "type": "EXACTLY",
            "region": {"type": "row", "number": 2},
            "k": 3,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_exactly(clue_k_max_false, self.assignment, self.n))

        # Biên vùng 1 ô (single-cell region)
        clue_single_cell_k1 = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["A1"]},
            "k": 1,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_exactly(clue_single_cell_k1, self.assignment, self.n))

        clue_single_cell_k0 = {
            "type": "EXACTLY",
            "region": {"type": "list", "cells": ["A1"]},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_exactly(clue_single_cell_k0, self.assignment, self.n))

    def test_eval_at_least(self):
        # Hàng 2: A2=F, B2=T, C2=T -> Criminal = 2
        clue_at_least_1 = {
            "type": "AT_LEAST",
            "region": {"type": "row", "number": 2},
            "k": 1,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_least(clue_at_least_1, self.assignment, self.n))

        clue_at_least_2 = {
            "type": "AT_LEAST",
            "region": {"type": "row", "number": 2},
            "k": 2,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_least(clue_at_least_2, self.assignment, self.n))

        clue_at_least_3 = {
            "type": "AT_LEAST",
            "region": {"type": "row", "number": 2},
            "k": 3,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_at_least(clue_at_least_3, self.assignment, self.n))

    def test_eval_at_least_edge_cases(self):
        # Biên k = 0: luôn True vì số lượng không âm
        clue_k_0 = {
            "type": "AT_LEAST",
            "region": {"type": "row", "number": 2},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_least(clue_k_0, self.assignment, self.n))

        # Biên k = |R| trên vùng 1 ô
        clue_single_k1 = {
            "type": "AT_LEAST",
            "region": {"type": "list", "cells": ["B2"]},
            "k": 1,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_least(clue_single_k1, self.assignment, self.n))

        clue_single_k0 = {
            "type": "AT_LEAST",
            "region": {"type": "list", "cells": ["A2"]},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_least(clue_single_k0, self.assignment, self.n))

    def test_eval_at_most(self):
        # Hàng 2: Criminal = 2
        clue_at_most_2 = {
            "type": "AT_MOST",
            "region": {"type": "row", "number": 2},
            "k": 2,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_most(clue_at_most_2, self.assignment, self.n))

        clue_at_most_1 = {
            "type": "AT_MOST",
            "region": {"type": "row", "number": 2},
            "k": 1,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_at_most(clue_at_most_1, self.assignment, self.n))

    def test_eval_at_most_edge_cases(self):
        # Biên k = |R|: luôn True vì số lượng tối đa là |R|
        clue_at_most_max = {
            "type": "AT_MOST",
            "region": {"type": "row", "number": 2},
            "k": 3,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_most(clue_at_most_max, self.assignment, self.n))

        # Biên k = 0 trên vùng 1 ô
        clue_single_k0_true = {
            "type": "AT_MOST",
            "region": {"type": "list", "cells": ["A2"]},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_at_most(clue_single_k0_true, self.assignment, self.n))

        clue_single_k0_false = {
            "type": "AT_MOST",
            "region": {"type": "list", "cells": ["A1"]},
            "k": 0,
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_at_most(clue_single_k0_false, self.assignment, self.n))

    # ------------------ Strict k Validation Tests ------------------
    def test_strict_k_validation(self):
        # k không phải int (float, str, bool) phải bị bắt lỗi
        bad_ks = [1.5, "1", True, False, 2.0]
        region = {"type": "row", "number": 1}

        for bad_k in bad_ks:
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi!"):
                eval_exactly(
                    {"type": "EXACTLY", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi!"):
                eval_at_least(
                    {"type": "AT_LEAST", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi!"):
                eval_at_most(
                    {"type": "AT_MOST", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )

        # k ngoài phạm vi [0, |R|] phải raise ValueError
        out_of_bounds_ks = [-1, 4, 10]
        for bad_k in out_of_bounds_ks:
            with self.assertRaises(ValueError, msg=f"k={bad_k} ngoài [0, 3] không bị bắt!"):
                eval_exactly(
                    {"type": "EXACTLY", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )

    # ------------------ Extension Clues (Task D6) ------------------
    def test_eval_parity(self):
        # Hàng 1: A1=T, B1=F, C1=F -> Criminal = 1 (ODD)
        clue_odd = {
            "type": "PARITY",
            "parity": "ODD",
            "region": {"type": "row", "number": 1},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_parity(clue_odd, self.assignment, self.n))
        self.assertTrue(evaluate(clue_odd, self.assignment, self.n))

        clue_even = {
            "type": "PARITY",
            "parity": "EVEN",
            "region": {"type": "row", "number": 1},
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_parity(clue_even, self.assignment, self.n))

        # Hàng 2: A2=F, B2=T, C2=T -> Criminal = 2 (EVEN)
        clue_even_row2 = {
            "type": "PARITY",
            "parity": "EVEN",
            "region": {"type": "row", "number": 2},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_parity(clue_even_row2, self.assignment, self.n))

    def test_eval_parity_zero_count_is_even(self):
        # Quy ước docs/INTERFACES.md: count = 0 là EVEN.
        # Dùng vùng hợp lệ 2 ô không rỗng: B1 và C1 đều là Innocent -> số Criminal = 0.
        clue_zero_even = {
            "type": "PARITY",
            "parity": "EVEN",
            "region": {"type": "list", "cells": ["B1", "C1"]},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_parity(clue_zero_even, self.assignment, self.n))

        clue_zero_odd = {
            "type": "PARITY",
            "parity": "ODD",
            "region": {"type": "list", "cells": ["B1", "C1"]},
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_parity(clue_zero_odd, self.assignment, self.n))

    def test_eval_parity_single_cell(self):
        # Vùng 1 ô: A1 (Criminal) -> count = 1 -> ODD True, EVEN False
        clue_single_odd = {
            "type": "PARITY",
            "parity": "ODD",
            "region": {"type": "list", "cells": ["A1"]},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_parity(clue_single_odd, self.assignment, self.n))

        clue_single_even = {
            "type": "PARITY",
            "parity": "EVEN",
            "region": {"type": "list", "cells": ["A1"]},
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_parity(clue_single_even, self.assignment, self.n))

    def test_eval_compare(self):
        # Cột C (2 criminals) vs Cột A (1 criminal: A1)
        clue_gt = {
            "type": "COMPARE",
            "region1": {"type": "col", "letter": "C"},
            "op": "GT",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_gt, self.assignment, self.n))
        self.assertTrue(evaluate(clue_gt, self.assignment, self.n))

        clue_lt = {
            "type": "COMPARE",
            "region1": {"type": "col", "letter": "C"},
            "op": "LT",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_compare(clue_lt, self.assignment, self.n))

        # EQ: Hàng 1 (1 criminal) == Cột A (1 criminal) -> True
        clue_eq = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "EQ",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_eq, self.assignment, self.n))

        # GE với alias left/right
        clue_ge = {
            "type": "COMPARE",
            "left": {"type": "row", "number": 1},
            "op": "GE",
            "right": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_ge, self.assignment, self.n))

    def test_eval_compare_le_operator(self):
        # Kiểm tra trực tiếp toán tử LE (<=)
        # Hàng 1 (1 crim) <= Cột C (2 crim): 1 <= 2 -> True
        clue_le_less = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "LE",
            "region2": {"type": "col", "letter": "C"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_le_less, self.assignment, self.n))

        # Hàng 1 (1 crim) <= Cột A (1 crim): 1 <= 1 -> True
        clue_le_equal = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "LE",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_le_equal, self.assignment, self.n))

        # Cột C (2 crim) <= Hàng 1 (1 crim): 2 <= 1 -> False
        clue_le_greater = {
            "type": "COMPARE",
            "region1": {"type": "col", "letter": "C"},
            "op": "LE",
            "region2": {"type": "row", "number": 1},
            "status": "CRIMINAL",
        }
        self.assertFalse(eval_compare(clue_le_greater, self.assignment, self.n))

    def test_eval_compare_single_cells(self):
        # So sánh 2 vùng mỗi vùng 1 ô: A1 (Crim=1) > B1 (Crim=0)
        clue_single_cmp = {
            "type": "COMPARE",
            "region1": {"type": "list", "cells": ["A1"]},
            "op": "GT",
            "region2": {"type": "list", "cells": ["B1"]},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_single_cmp, self.assignment, self.n))

    def test_clue_object_support(self):
        # Hỗ trợ đối tượng Clue từ engine.clue
        clue_obj = Clue(
            id="clue_A1",
            owner="A1",
            type="FACT",
            params={"target": "A1", "status": "CRIMINAL"},
        )
        self.assertTrue(evaluate(clue_obj, self.assignment, self.n))

    def test_evaluate_all_utility(self):
        clues = [
            {"type": "FACT", "target": "A1", "status": "CRIMINAL"},
            {"type": "SAME_STATUS", "cell1": "B1", "cell2": "C1"},
            {"type": "EXACTLY", "region": {"type": "row", "number": 2}, "k": 2},
        ]
        self.assertTrue(evaluate_all(clues, self.assignment, self.n))

        # Thêm 1 clue sai
        clues.append({"type": "FACT", "target": "B1", "status": "CRIMINAL"})
        self.assertFalse(evaluate_all(clues, self.assignment, self.n))

    # ------------------ Test trực tiếp với puzzle thật p01.json ------------------
    def test_evaluate_against_real_puzzle_p01(self):
        puzzle_path = (
            Path(__file__).resolve().parent.parent / "data" / "puzzles_3x3" / "p01.json"
        )
        with open(puzzle_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        n = data["n"]
        solution = {char["cell"]: char["criminal"] for char in data["characters"]}
        all_clues = [char["clue"] for char in data["characters"]]

        # Tất cả các clue của p01.json PHẢI đúng trên nghiệm thật
        for i, clue in enumerate(all_clues):
            self.assertTrue(
                evaluate(clue, solution, n),
                msg=f"Clue thứ {i} ({clue['type']}) sai trên nghiệm của p01.json!",
            )

        # evaluate_all cũng phải trả về True
        self.assertTrue(evaluate_all(all_clues, solution, n))


class TestSemanticIntegration(unittest.TestCase):
    """Kiểm tra tích hợp cho Brute Force (Task B2) và Kiểm chứng chéo CNF (Task C7)."""

    def test_brute_force_solver_using_semantic_evaluator(self):
        """Chứng minh evaluate_all() dùng trực tiếp trong Brute-Force checker (B2)."""
        puzzle_path = (
            Path(__file__).resolve().parent.parent / "data" / "puzzles_3x3" / "p01.json"
        )
        with open(puzzle_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        n = data["n"]
        expected_solution = {c["cell"]: c["criminal"] for c in data["characters"]}
        all_clues = [c["clue"] for c in data["characters"]]

        # Cố định các ô initially_revealed để giảm không gian tìm kiếm
        fixed_cells = {c: expected_solution[c] for c in data["initially_revealed"]}
        free_cells = [c for c in board.all_cells(n) if c not in fixed_cells]

        # Brute force duyệt toàn bộ 2^7 = 128 phép gán
        solutions = []
        for combo in itertools.product([False, True], repeat=len(free_cells)):
            assignment = dict(fixed_cells)
            assignment.update(dict(zip(free_cells, combo)))
            if evaluate_all(all_clues, assignment, n):
                solutions.append(assignment)

        # Phải tìm được ĐÚNG 1 nghiệm duy nhất và trùng khớp với nghiệm của puzzle
        self.assertEqual(len(solutions), 1, "Puzzle phải có duy nhất 1 nghiệm qua brute force!")
        self.assertEqual(solutions[0], expected_solution)

    def test_semantic_matches_cnf_truth_table(self):
        """Chứng minh evaluate() tương đương chân trị với CNF logic (nền tảng cho C7)."""
        # Kiểm tra với SAME_STATUS: (¬A ∨ B) ∧ (A ∨ ¬B)
        clue_same = {"type": "SAME_STATUS", "cell1": "A1", "cell2": "B1"}
        for a_val, b_val in itertools.product([False, True], repeat=2):
            asg = {"A1": a_val, "B1": b_val}
            cnf_sat = ((not a_val) or b_val) and (a_val or (not b_val))
            self.assertEqual(
                evaluate(clue_same, asg, 3),
                cnf_sat,
                msg=f"Không khớp chân trị tại A1={a_val}, B1={b_val}",
            )

        # Kiểm tra với DIFFERENT_STATUS: (A ∨ B) ∧ (¬A ∨ ¬B)
        clue_diff = {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "B1"}
        for a_val, b_val in itertools.product([False, True], repeat=2):
            asg = {"A1": a_val, "B1": b_val}
            cnf_sat = (a_val or b_val) and ((not a_val) or (not b_val))
            self.assertEqual(
                evaluate(clue_diff, asg, 3),
                cnf_sat,
                msg=f"Không khớp chân trị tại A1={a_val}, B1={b_val}",
            )


if __name__ == "__main__":
    unittest.main()
