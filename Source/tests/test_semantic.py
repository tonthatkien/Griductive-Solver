import itertools
import json
from pathlib import Path
import unittest

from engine import board
from engine.clue import Clue, resolve_region
from engine.constants import CRIMINAL, INNOCENT
from logic.semantic import (
    count_status_matches,
    eval_at_least,
    eval_at_most,
    eval_compare,
    eval_different_status,
    eval_exactly,
    eval_fact,
    eval_noise,
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

    def test_resolve_region_row_and_col(self):
        self.assertEqual(
            resolve_region_cells({"type": "row", "number": 1}, self.n),
            ["A1", "B1", "C1"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "row", "number": 2}, self.n),
            ["A2", "B2", "C2"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "col", "letter": "B"}, self.n),
            ["B1", "B2", "B3"],
        )
        self.assertEqual(
            resolve_region_cells({"type": "col", "letter": "C"}, self.n),
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
        # type list
        self.assertEqual(
            resolve_region_cells({"type": "list", "cells": ["C3", "A1"]}, self.n),
            ["A1", "C3"],
        )

    def test_resolve_region_vs_engine_clue_resolve_region(self):
        # Đối chiếu resolve_region_cells với engine.clue.resolve_region trên mọi row, col, neighbors
        for size in (3, 4):
            # Mọi hàng
            for r in range(1, size + 1):
                reg = {"type": "row", "number": r}
                self.assertEqual(
                    resolve_region_cells(reg, size),
                    resolve_region(reg, size),
                )
            # Mọi cột
            for c_letter in board.COLS[:size]:
                reg = {"type": "col", "letter": c_letter}
                self.assertEqual(
                    resolve_region_cells(reg, size),
                    resolve_region(reg, size),
                )
            # Mọi neighbors
            for cell in board.all_cells(size):
                reg = {"type": "neighbors", "cell": cell}
                self.assertEqual(
                    resolve_region_cells(reg, size),
                    resolve_region(reg, size),
                )

    def test_resolve_region_rejects_empty_region(self):
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "list", "cells": []}, self.n)

    def test_resolve_region_rejects_tuple_cells(self):
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "list", "cells": ("A1", "B1")}, self.n)

    def test_resolve_region_rejects_duplicate_cells(self):
        bad_duplicates = [
            {"type": "list", "cells": ["A1", "A1"]},
            {"type": "list", "cells": ["B2", "C3", "B2"]},
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

        # Cột không phải chữ cái in hoa 1 ký tự hoặc ngoài lưới
        bad_cols = ["b", "AB", 1, True, "D", ""]
        for bad_c in bad_cols:
            with self.assertRaises(ValueError, msg=f"Col={bad_c!r} không bị bắt lỗi"):
                resolve_region_cells({"type": "col", "letter": bad_c}, self.n)

    def test_resolve_region_rejects_invalid_cell(self):
        # Ô ngoài lưới
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "list", "cells": ["Z9"]}, self.n)

        # Phần tử không phải string hoặc sai kiểu
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
        # Giá trị trong assignment sai kiểu bool (phải bị ném TypeError)
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

    def test_eval_same_status_truth_table_all_4_combinations(self):
        # Kiểm tra đầy đủ bảng chân trị 4 tổ hợp: (T,T), (T,F), (F,T), (F,F)
        clue_same = {"type": "SAME_STATUS", "cell1": "A1", "cell2": "B1"}
        for val1, val2 in itertools.product([True, False], repeat=2):
            asg = dict(self.assignment)
            asg["A1"] = val1
            asg["B1"] = val2
            expected = (val1 == val2)
            self.assertEqual(
                eval_same_status(clue_same, asg, self.n),
                expected,
                msg=f"SAME_STATUS thất bại với tổ hợp ({val1}, {val2})",
            )
            self.assertEqual(evaluate(clue_same, asg, self.n), expected)

    def test_eval_same_status_edge_cases(self):
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

    def test_eval_different_status_truth_table_all_4_combinations(self):
        # Kiểm tra đầy đủ bảng chân trị 4 tổ hợp: (T,T), (T,F), (F,T), (F,F)
        clue_diff = {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "B1"}
        for val1, val2 in itertools.product([True, False], repeat=2):
            asg = dict(self.assignment)
            asg["A1"] = val1
            asg["B1"] = val2
            expected = (val1 != val2)
            self.assertEqual(
                eval_different_status(clue_diff, asg, self.n),
                expected,
                msg=f"DIFFERENT_STATUS thất bại với tổ hợp ({val1}, {val2})",
            )
            self.assertEqual(evaluate(clue_diff, asg, self.n), expected)

    def test_eval_different_status_edge_cases(self):
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

    def test_exhaustive_counting_clues(self):
        # Duyệt mọi assignment 2^3 của vùng 3 ô, mọi k trong 0..3, cả 2 status
        # Kiểm chứng toàn diện cho EXACTLY, AT_LEAST, AT_MOST
        region_cells = ["A1", "B1", "C1"]
        region = {"type": "list", "cells": region_cells}
        for vals in itertools.product([True, False], repeat=3):
            asg = dict(self.assignment)
            for c, v in zip(region_cells, vals):
                asg[c] = v
            for status in ("CRIMINAL", "INNOCENT"):
                target_val = (status == "CRIMINAL")
                count = sum(1 for v in vals if v == target_val)
                for k in range(4):
                    clue_exact = {
                        "type": "EXACTLY", "region": region, "k": k, "status": status,
                    }
                    clue_ge = {
                        "type": "AT_LEAST", "region": region, "k": k, "status": status,
                    }
                    clue_le = {
                        "type": "AT_MOST", "region": region, "k": k, "status": status,
                    }
                    self.assertEqual(
                        eval_exactly(clue_exact, asg, self.n),
                        count == k,
                        msg=f"EXACTLY thất bại: vals={vals}, status={status}, k={k}",
                    )
                    self.assertEqual(
                        eval_at_least(clue_ge, asg, self.n),
                        count >= k,
                        msg=f"AT_LEAST thất bại: vals={vals}, status={status}, k={k}",
                    )
                    self.assertEqual(
                        eval_at_most(clue_le, asg, self.n),
                        count <= k,
                        msg=f"AT_MOST thất bại: vals={vals}, status={status}, k={k}",
                    )

    def test_strict_k_validation(self):
        bad_ks = [1.5, "1", True, False, 2.0]
        region = {"type": "row", "number": 1}
        for bad_k in bad_ks:
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi"):
                eval_exactly(
                    {"type": "EXACTLY", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi"):
                eval_at_least(
                    {"type": "AT_LEAST", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} không bị bắt lỗi"):
                eval_at_most(
                    {"type": "AT_MOST", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )

        # k nằm ngoài phạm vi [0, |R|]
        out_of_bounds_ks = [-1, 4, 10]
        for bad_k in out_of_bounds_ks:
            with self.assertRaises(ValueError, msg=f"k ngoài biên {bad_k} không bị bắt"):
                eval_exactly(
                    {"type": "EXACTLY", "region": region, "k": bad_k},
                    self.assignment,
                    self.n,
                )

    def test_counting_clues_missing_params_and_invalid_status(self):
        region = {"type": "row", "number": 1}
        # Thiếu region hoặc thiếu k
        with self.assertRaises(ValueError):
            eval_exactly({"type": "EXACTLY", "k": 1}, self.assignment, self.n)
        with self.assertRaises(ValueError):
            eval_exactly({"type": "EXACTLY", "region": region}, self.assignment, self.n)
        with self.assertRaises(ValueError):
            eval_at_least({"type": "AT_LEAST", "k": 1}, self.assignment, self.n)
        with self.assertRaises(ValueError):
            eval_at_most({"type": "AT_MOST", "k": 1}, self.assignment, self.n)

        # Status sai (ví dụ chữ thường 'criminal' hoặc chuỗi lạ)
        for bad_st in ["criminal", "innocent", "UNKNOWN", 123]:
            with self.assertRaises(ValueError):
                eval_exactly(
                    {"type": "EXACTLY", "region": region, "k": 1, "status": bad_st},
                    self.assignment,
                    self.n,
                )


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
        # Quy ước: count = 0 là EVEN
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

        # GE: Hàng 1 (1 crim) >= Cột A (1 crim) -> True
        clue_ge = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "GE",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        self.assertTrue(eval_compare(clue_ge, self.assignment, self.n))

    def test_eval_compare_le_operator(self):
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

    def test_eval_compare_rejects_old_left_right(self):
        clue_left = {
            "type": "COMPARE",
            "left": {"type": "row", "number": 1},
            "op": "GE",
            "region2": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        with self.assertRaises(ValueError):
            eval_compare(clue_left, self.assignment, self.n)

        clue_right = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "GE",
            "right": {"type": "col", "letter": "A"},
            "status": "CRIMINAL",
        }
        with self.assertRaises(ValueError):
            eval_compare(clue_right, self.assignment, self.n)

    def test_eval_compare_status_innocent(self):
        # Đánh giá COMPARE khi status=INNOCENT
        # Hàng 1: A1=T, B1=F, C1=F -> Innocent count = 2
        # Hàng 2: A2=F, B2=T, C2=T -> Innocent count = 1
        # Cột A: A1=T, A2=F, A3=F -> Innocent count = 2
        clue_inn_gt = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "GT",
            "region2": {"type": "row", "number": 2},
            "status": "INNOCENT",
        }
        self.assertTrue(eval_compare(clue_inn_gt, self.assignment, self.n))

        clue_inn_eq = {
            "type": "COMPARE",
            "region1": {"type": "row", "number": 1},
            "op": "EQ",
            "region2": {"type": "col", "letter": "A"},
            "status": "INNOCENT",
        }
        self.assertTrue(eval_compare(clue_inn_eq, self.assignment, self.n))

    def test_eval_compare_invalid_inputs(self):
        # Thiếu region1 hoặc region2
        with self.assertRaises(ValueError):
            eval_compare(
                {"type": "COMPARE", "region2": {"type": "row", "number": 1}, "op": "EQ"},
                self.assignment,
                self.n,
            )
        with self.assertRaises(ValueError):
            eval_compare(
                {"type": "COMPARE", "region1": {"type": "row", "number": 1}, "op": "EQ"},
                self.assignment,
                self.n,
            )

        # Toán tử op không hợp lệ
        for bad_op in ["INVALID", ">", "==", None]:
            with self.assertRaises(ValueError):
                eval_compare(
                    {
                        "type": "COMPARE",
                        "region1": {"type": "row", "number": 1},
                        "op": bad_op,
                        "region2": {"type": "col", "letter": "A"},
                    },
                    self.assignment,
                    self.n,
                )

        # Status sai (ví dụ chữ thường 'criminal' hoặc giá trị lạ)
        for bad_status in ["criminal", "innocent", "UNKNOWN", 123]:
            with self.assertRaises(ValueError):
                eval_compare(
                    {
                        "type": "COMPARE",
                        "region1": {"type": "row", "number": 1},
                        "op": "EQ",
                        "region2": {"type": "col", "letter": "A"},
                        "status": bad_status,
                    },
                    self.assignment,
                    self.n,
                )

        # Region sai cấu trúc trong COMPARE
        with self.assertRaises(ValueError):
            eval_compare(
                {
                    "type": "COMPARE",
                    "region1": {"type": "row", "number": 99},
                    "op": "EQ",
                    "region2": {"type": "col", "letter": "A"},
                },
                self.assignment,
                self.n,
            )

    def test_eval_parity_status_innocent(self):
        # Hàng 1: A1=T, B1=F, C1=F -> Innocent count = 2 (EVEN)
        clue_inn_even = {
            "type": "PARITY",
            "parity": "EVEN",
            "region": {"type": "row", "number": 1},
            "status": "INNOCENT",
        }
        self.assertTrue(eval_parity(clue_inn_even, self.assignment, self.n))

        clue_inn_odd = {
            "type": "PARITY",
            "parity": "ODD",
            "region": {"type": "row", "number": 1},
            "status": "INNOCENT",
        }
        self.assertFalse(eval_parity(clue_inn_odd, self.assignment, self.n))

        # Hàng 2: A2=F, B2=T, C2=T -> Innocent count = 1 (ODD)
        clue_row2_inn_odd = {
            "type": "PARITY",
            "parity": "ODD",
            "region": {"type": "row", "number": 2},
            "status": "INNOCENT",
        }
        self.assertTrue(eval_parity(clue_row2_inn_odd, self.assignment, self.n))

    def test_eval_parity_invalid_inputs(self):
        # Thiếu region hoặc parity
        with self.assertRaises(ValueError):
            eval_parity({"type": "PARITY", "parity": "EVEN"}, self.assignment, self.n)
        with self.assertRaises(ValueError):
            eval_parity(
                {"type": "PARITY", "region": {"type": "row", "number": 1}},
                self.assignment,
                self.n,
            )

        # Parity không hợp lệ
        for bad_p in ["even", "odd", "UNKNOWN", 123]:
            with self.assertRaises(ValueError):
                eval_parity(
                    {
                        "type": "PARITY",
                        "parity": bad_p,
                        "region": {"type": "row", "number": 1},
                    },
                    self.assignment,
                    self.n,
                )

        # Status sai (ví dụ chữ thường 'criminal' hoặc giá trị lạ)
        for bad_status in ["criminal", "innocent", "UNKNOWN", 123]:
            with self.assertRaises(ValueError):
                eval_parity(
                    {
                        "type": "PARITY",
                        "parity": "EVEN",
                        "region": {"type": "row", "number": 1},
                        "status": bad_status,
                    },
                    self.assignment,
                    self.n,
                )

    def test_clue_object_support(self):
        # Hỗ trợ đối tượng Clue từ engine.clue
        clue_obj = Clue(
            id="clue_A1",
            owner="A1",
            type="FACT",
            params={"target": "A1", "status": "CRIMINAL"},
        )
        self.assertTrue(evaluate(clue_obj, self.assignment, self.n))

        # Đối tượng Clue cho PARITY
        clue_parity = Clue(
            id="clue_A2",
            owner="A2",
            type="PARITY",
            params={"region": {"type": "row", "number": 1}, "parity": "ODD"},
        )
        self.assertTrue(evaluate(clue_parity, self.assignment, self.n))

        # Đối tượng Clue cho COMPARE
        clue_compare = Clue(
            id="clue_A3",
            owner="A3",
            type="COMPARE",
            params={
                "region1": {"type": "col", "letter": "C"},
                "op": "GT",
                "region2": {"type": "col", "letter": "A"},
            },
        )
        self.assertTrue(evaluate(clue_compare, self.assignment, self.n))

    def test_eval_noise_is_always_true(self):
        clue = {"type": "NOISE", "text": "Tôi thích trồng hoa."}
        flipped = {cell: not value for cell, value in self.assignment.items()}
        self.assertTrue(eval_noise(clue, self.assignment, self.n))
        self.assertTrue(evaluate(clue, self.assignment, self.n))
        self.assertTrue(evaluate(clue, flipped, self.n))
        self.assertTrue(evaluate(clue, {}, self.n))  # không đọc assignment
        as_object = Clue(id="clue_A1", owner="A1", type="NOISE", params={"text": "x"})
        self.assertTrue(evaluate(as_object, self.assignment, self.n))

    def test_eval_noise_rejects_missing_or_empty_text(self):
        for bad in ({"type": "NOISE"}, {"type": "NOISE", "text": ""},
                    {"type": "NOISE", "text": "   "}, {"type": "NOISE", "text": 5}):
            with self.subTest(clue=bad):
                with self.assertRaises(ValueError):
                    evaluate(bad, self.assignment, self.n)

    def test_evaluate_all_ignores_noise_clues(self):
        noise = {"type": "NOISE", "text": "Tôi thích trồng hoa."}
        true_fact = {"type": "FACT", "target": "A1", "status": "CRIMINAL"}
        false_fact = {"type": "FACT", "target": "B1", "status": "CRIMINAL"}
        self.assertTrue(evaluate_all([noise, true_fact], self.assignment, self.n))
        self.assertFalse(evaluate_all([noise, false_fact], self.assignment, self.n))

    def test_evaluate_rejects_non_string_clue_type(self):
        bad_types = [["FACT"], 123, True, False, None, {"nested": "FACT"}]
        for bad_t in bad_types:
            with self.assertRaises(ValueError, msg=f"Type={bad_t!r} không bị bắt lỗi"):
                evaluate(
                    {"type": bad_t, "target": "A1", "status": "CRIMINAL"},
                    self.assignment,
                    self.n,
                )

    def test_evaluate_rejects_unknown_clue_type(self):
        with self.assertRaises(ValueError):
            evaluate(
                {"type": "UNKNOWN_CLUE", "target": "A1"},
                self.assignment,
                self.n,
            )

    def test_evaluate_rejects_invalid_clue_container(self):
        # Clue không phải Clue hay dict -> TypeError
        for bad_c in [123, "not_a_clue", ["FACT"], None]:
            with self.assertRaises(TypeError):
                evaluate(bad_c, self.assignment, self.n)

    def test_reject_deprecated_aliases(self):
        # 1. SAME và DIFFERENT bị loại khỏi CLUE_EVALUATORS
        with self.assertRaises(ValueError):
            evaluate({"type": "SAME", "cell1": "A1", "cell2": "B1"}, self.assignment, self.n)
        with self.assertRaises(ValueError):
            evaluate(
                {"type": "DIFFERENT", "cell1": "A1", "cell2": "B1"}, self.assignment, self.n
            )

        # 2. FACT dùng cell thay vì target
        with self.assertRaises(ValueError):
            eval_fact({"type": "FACT", "cell": "A1", "status": "CRIMINAL"}, self.assignment, self.n)

        # 3. SAME_STATUS dùng a/b thay vì cell1/cell2
        with self.assertRaises(ValueError):
            eval_same_status(
                {"type": "SAME_STATUS", "a": "A1", "b": "B1"}, self.assignment, self.n
            )

        # 4. DIFFERENT_STATUS dùng a/b thay vì cell1/cell2
        with self.assertRaises(ValueError):
            eval_different_status(
                {"type": "DIFFERENT_STATUS", "a": "A1", "b": "B1"}, self.assignment, self.n
            )

        # 5. Region row dùng index thay vì number
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "row", "index": 1}, self.n)

        # 6. Region col dùng index thay vì letter
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "col", "index": "A"}, self.n)

        # 7. Region cells thay vì list
        with self.assertRaises(ValueError):
            resolve_region_cells({"type": "cells", "cells": ["A1", "B1"]}, self.n)

    def test_evaluate_all_utility(self):
        # evaluate_all([]) danh sách rỗng phải trả về True
        self.assertTrue(evaluate_all([], self.assignment, self.n))

        clues = [
            {"type": "FACT", "target": "A1", "status": "CRIMINAL"},
            {"type": "SAME_STATUS", "cell1": "B1", "cell2": "C1"},
            {"type": "EXACTLY", "region": {"type": "row", "number": 2}, "k": 2},
            {"type": "PARITY", "region": {"type": "row", "number": 1}, "parity": "ODD"},
            {
                "type": "COMPARE",
                "region1": {"type": "col", "letter": "C"},
                "op": "GT",
                "region2": {"type": "col", "letter": "A"},
            },
        ]
        self.assertTrue(evaluate_all(clues, self.assignment, self.n))

        # Thêm 1 clue sai
        clues.append({"type": "FACT", "target": "B1", "status": "CRIMINAL"})
        self.assertFalse(evaluate_all(clues, self.assignment, self.n))

    # Quét mọi puzzle trong data/puzzles_*/*.json bằng glob + subTest
    def test_evaluate_against_real_puzzles(self):
        data_dir = Path(__file__).resolve().parent.parent / "data"
        puzzle_files = sorted(data_dir.glob("puzzles_*/*.json"))
        self.assertTrue(len(puzzle_files) > 0, "Không tìm thấy file puzzle nào trong data/")

        for p_path in puzzle_files:
            with self.subTest(puzzle=p_path.name):
                with open(p_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                n = data["n"]
                solution = {char["cell"]: char["criminal"] for char in data["characters"]}
                all_clues = [char["clue"] for char in data["characters"]]

                # Tất cả các clue của puzzle phải đúng trên nghiệm thật
                for i, clue in enumerate(all_clues):
                    self.assertTrue(
                        evaluate(clue, solution, n),
                        msg=f"Clue {i} ({clue['type']}) sai trên nghiệm của {p_path.name}!",
                    )

                # evaluate_all cũng phải trả về True
                self.assertTrue(evaluate_all(all_clues, solution, n))


if __name__ == "__main__":
    unittest.main()