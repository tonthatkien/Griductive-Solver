"""Kiểm thử DPLL: Lan truyền đơn vị và phát hiện xung đột
"""
import time
import unittest
from typing import Dict, List
from unittest.mock import patch

from logic.dpll import DPLLSolver, _TimeoutException


class TestDPLLUnitPropagationAndConflict(unittest.TestCase):
    """Kiểm thử thuật toán lan truyền đơn vị và phát hiện xung đột"""

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_unit_propagation(self) -> None:
        """Lan truyền mệnh đề đơn lẻ, chuỗi liên hoàn và co gọn mệnh đề nhiều biến."""
        # 1. Đơn âm [-2] ép 2 = False
        assign_neg: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[-2]], assign_neg)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_neg, {2: False})
        self.assertEqual(self.solver.stats.propagations, 1)

        # 2. Chuỗi liên hoàn kết hợp co gọn mệnh đề:
        # [1] ép 1=True; [-1, 2] ép 2=True; [-2, -4, 3] với 4=True (literal -4=False) ép 3=True
        solver = DPLLSolver()
        assign_casc: Dict[int, bool] = {4: True}
        clauses = [[1], [-1, 2], [-2, -4, 3]]
        is_conf, conf_c = solver.unit_propagate(clauses, assign_casc)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_casc, {4: True, 1: True, 2: True, 3: True})
        self.assertEqual(solver.stats.propagations, 3)

    def test_conflict_detection(self) -> None:
        """Phát hiện xung đột từ mệnh đề rỗng, mệnh đề đối nghịch và chuỗi lan truyền."""
        # 1. Mệnh đề rỗng [] gây conflict ngay lập tức
        is_conf, conf_c = self.solver.unit_propagate([[]], {})
        self.assertTrue(is_conf)
        self.assertEqual(conf_c, [])

        # 2. Hai mệnh đề đơn mâu thuẫn trực tiếp [1] và [-1]
        assign_opp: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[1], [-1]], assign_opp)
        self.assertTrue(is_conf)
        self.assertEqual(conf_c, [-1])
        self.assertEqual(assign_opp, {1: True})

        # 3. Chuỗi lan truyền dẫn tới xung đột: [1] -> 2 -> mâu thuẫn với [-2]
        assign_casc: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[1], [-1, 2], [-2]], assign_casc)
        self.assertTrue(is_conf)
        self.assertEqual(conf_c, [-2])
        self.assertEqual(assign_casc, {1: True, 2: True})

    def test_clause_filtering_and_status(self) -> None:
        """Kiểm tra phân loại trạng thái mệnh đề và bỏ qua các mệnh đề đã thỏa mãn."""
        # Phân loại trạng thái mệnh đề
        self.assertEqual(self.solver.get_clause_status([], {}), ("CONFLICT", None))
        self.assertEqual(self.solver.get_clause_status([1], {}), ("UNIT", 1))
        self.assertEqual(self.solver.get_clause_status([1, 2], {}), ("UNRESOLVED", None))
        self.assertEqual(self.solver.get_clause_status([1, 2], {1: True}), ("SATISFIED", None))
        self.assertEqual(self.solver.get_clause_status([1, 2], {1: False}), ("UNIT", 2))
        self.assertEqual(
            self.solver.get_clause_status([1, 2], {1: False, 2: False}),
            ("CONFLICT", None),
        )

        # Mệnh đề đã thỏa mãn hoặc literal trùng lặp [1, 1] được lọc chính xác
        assign: Dict[int, bool] = {1: True}
        is_conf, _ = self.solver.unit_propagate([[1, 2], [3, 3]], assign)
        self.assertFalse(is_conf)
        self.assertEqual(assign, {1: True, 3: True})

        # Tiện ích is_conflict
        self.assertFalse(self.solver.is_conflict([[1, 2], [-1]], {}))
        self.assertTrue(self.solver.is_conflict([[1, 2], [-1]], {1: True}))

    def test_tautology_clause(self) -> None:
        """Mệnh đề chứa cả x và ¬x là hằng đúng (Tautology), luôn SAT và không gây conflict."""
        # 1. Trạng thái khi chưa gán và khi đã gán đều là SATISFIED
        self.assertEqual(self.solver.get_clause_status([1, -1], {}), ("SATISFIED", None))
        self.assertEqual(self.solver.get_clause_status([1, -1], {1: True}), ("SATISFIED", None))
        self.assertEqual(self.solver.get_clause_status([1, -1], {1: False}), ("SATISFIED", None))

        # 2. solve([[1, -1]]) trả về SAT mà không cần branching
        res = self.solver.solve([[1, -1]], num_vars=1)
        self.assertTrue(res.sat)
        self.assertIsNotNone(res.model)
        assert res.model is not None
        self.assertTrue(self.solver.is_clause_satisfied([1, -1], res.model))

        # 3. Khóa hành vi với assumptions: ép 1=True hoặc 1=False vẫn luôn SAT
        res_true = self.solver.solve([[1, -1]], num_vars=1, assumptions=[1])
        self.assertTrue(res_true.sat and res_true.model and res_true.model[1] is True)

        res_false = self.solver.solve([[1, -1]], num_vars=1, assumptions=[-1])
        self.assertTrue(res_false.sat and res_false.model and res_false.model[1] is False)

        # 4. Tautology kết hợp unit clause: [[1, -1, 2], [-2]]
        res_comb = self.solver.solve([[1, -1, 2], [-2]], num_vars=2)
        self.assertTrue(res_comb.sat and res_comb.model and res_comb.model[2] is False)

    def test_sat_model_validates_all_clauses(self) -> None:
        """Kiểm chứng tính đúng đắn của SAT model cho công thức rỗng và chuỗi lan truyền."""
        # 1. Công thức rỗng luôn SAT và model đủ biến
        res_empty = self.solver.solve([], num_vars=3)
        self.assertTrue(res_empty.sat and res_empty.model and len(res_empty.model) == 3)

        # 2. Công thức chuỗi: [[1], [-1, 2], [-2, 3]] với num_vars = 5
        clauses = [[1], [-1, 2], [-2, 3]]
        result = self.solver.solve(clauses, num_vars=5)
        self.assertTrue(result.sat)
        self.assertIsNotNone(result.model)
        assert result.model is not None

        # Model chứa đủ 1..5 và thỏa mãn mọi mệnh đề
        self.assertEqual(set(result.model.keys()), {1, 2, 3, 4, 5})
        self.assertTrue(result.model[1] and result.model[2] and result.model[3])
        for clause in clauses:
            self.assertTrue(self.solver.is_clause_satisfied(clause, result.model))

    def test_clauses_immutability(self) -> None:
        """Bảo đảm clauses gốc bất biến khi gọi unit_propagate và solve kèm assumptions."""
        clauses = [[1, 2], [-1, 2]]
        copy_c = [list(c) for c in clauses]

        self.solver.unit_propagate(clauses, {})
        self.assertEqual(clauses, copy_c)

        self.solver.solve(clauses, num_vars=2, assumptions=[2])
        self.assertEqual(clauses, copy_c)

    def test_solver_instance_reuse_resets_stats_and_state(self) -> None:
        """Gọi solve() nhiều lần trên cùng 1 instance solver phải reset stats và cô lập state."""
        # Lần 1: Giải [[1]] -> model[1] = True, propagations = 1
        res_1 = self.solver.solve([[1]], num_vars=1)
        self.assertTrue(res_1.sat and res_1.model and res_1.model[1] is True)
        self.assertEqual(res_1.stats.propagations, 1)

        # Lần 2: Giải bài toán mâu thuẫn [[1], [-1]] -> UNSAT, reset stats
        res_2 = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertFalse(res_2.sat)
        self.assertIsNone(res_2.model)

        # Lần 3: Giải [[-1]] -> model[1] phải là False, propagations reset về 1
        res_3 = self.solver.solve([[-1]], num_vars=1)
        self.assertTrue(res_3.sat and res_3.model and res_3.model[1] is False)
        self.assertEqual(res_3.stats.propagations, 1)

    def test_assumptions_handling(self) -> None:
        """Xử lý assumptions: mâu thuẫn trực tiếp và suy diễn trong đề bài KB = (A∨B) ∧ (¬A∨B)."""
        # 1. Assumptions mâu thuẫn trực tiếp [1, -1] lập tức trả về UNSAT
        res_direct = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertFalse(res_direct.sat)

        # 2. Giả sử B = Innocent (-2) -> ép A=True rồi mâu thuẫn với (¬A ∨ B) -> UNSAT
        clauses = [[1, 2], [-1, 2]]
        res_innocent = self.solver.solve(clauses, num_vars=2, assumptions=[-2])
        self.assertFalse(res_innocent.sat)
        self.assertIsNone(res_innocent.model)

    def test_formula_requiring_branching_raises_not_implemented(self) -> None:
        """Công thức cần rẽ nhánh ném NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.solver.solve([[1, 2]], num_vars=2)

    def test_input_validation(self) -> None:
        """Xác thực toàn diện đầu vào: từ chối kiểu sai, giá trị ngoài phạm vi, literal 0, NaN."""
        # 1. Literal 0 và vượt phạm vi bounds
        with self.assertRaises(ValueError):
            self.solver.solve([[0]], num_vars=2)
        with self.assertRaises(ValueError):
            self.solver.solve([[3]], num_vars=2)
        with self.assertRaises(ValueError):
            self.solver.solve([[1]], num_vars=2, assumptions=[0])
        with self.assertRaises(ValueError):
            self.solver.solve([], num_vars=-1)

        # 2. Kiểu dữ liệu không phải int (float, bool, str)
        with self.assertRaises(TypeError):
            self.solver.solve([], num_vars=1.5)
        with self.assertRaises(TypeError):
            self.solver.solve([], num_vars=True)
        with self.assertRaises(TypeError):
            self.solver.solve([[1.5]], num_vars=2)
        with self.assertRaises(TypeError):
            self.solver.solve([[1]], num_vars=2, assumptions=[False])

        # 3. Timeout không hợp lệ
        with self.assertRaises(ValueError):
            self.solver.solve([[1]], num_vars=1, timeout=float("nan"))
        with self.assertRaises(TypeError):
            self.solver.solve([[1]], num_vars=1, timeout="1.0")

    def test_iterator_and_generator_safety(self) -> None:
        """Hỗ trợ an toàn các cấu trúc iterator/generator và không bỏ lỗi RecursionError."""
        # 1. Iterator clauses mâu thuẫn không bị cạn kiệt trong lúc validate -> trả về UNSAT
        res_iter = self.solver.solve(iter([[1], [-1]]), num_vars=1)
        self.assertFalse(res_iter.sat)

        # 2. Generator clauses và generator assumptions giải quyết chính xác
        gen_c = (c for c in [[1], [-1, 2]])
        res_gen = self.solver.solve(gen_c, num_vars=2)
        self.assertTrue(res_gen.sat and res_gen.model and res_gen.model[1] and res_gen.model[2])

        gen_assump = (lit for lit in [-2])
        res_assump = self.solver.solve([[1, 2], [-1, 2]], num_vars=2, assumptions=gen_assump)
        self.assertFalse(res_assump.sat)

        # 3. Generator đệ quy bất thường không bị đổi thành UNSAT
        def _recursive_gen():
            yield from _recursive_gen()

        with self.assertRaises(RecursionError):
            self.solver.solve(_recursive_gen(), num_vars=1)

    def test_timeout_handling(self) -> None:
        """Kiểm soát timeout chính xác, phân biệt với UNSAT và cập nhật runtime/stats."""
        # 1. Timeout = 0.0: dùng mock timer để chứng minh runtime thực sự được cập nhật từ đồng hồ
        with patch("time.perf_counter", side_effect=[100.0, 100.05]):
            res_zero = self.solver.solve([[1]], num_vars=1, timeout=0.0)
            self.assertTrue(res_zero.timed_out)
            self.assertFalse(res_zero.sat)
            self.assertIsNone(res_zero.model)
            self.assertAlmostEqual(res_zero.stats.runtime, 0.05)

        # 2. Phân biệt rõ ràng giữa TIMEOUT và UNSAT thực sự
        res_unsat = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertFalse(res_unsat.sat)
        self.assertFalse(res_unsat.timed_out)

        # 3. Timeout ngắt giữa chuỗi lan truyền lớn và ghi nhận runtime thực tế > 0
        large_clauses = [[1]] + [[-i, i + 1] for i in range(1, 10000)]
        res_prop = self.solver.solve(large_clauses, num_vars=10001, timeout=1e-6)
        self.assertTrue(res_prop.timed_out)
        self.assertGreater(res_prop.stats.runtime, 0.0)

        # 4. Timeout ngắt an toàn trước generator assumptions vô hạn
        def _infinite_assumptions():
            while True:
                yield 1

        res_inf = self.solver.solve(
            [[1]], num_vars=1, assumptions=_infinite_assumptions(), timeout=0.005
        )
        self.assertTrue(res_inf.timed_out)

        # 5. _build_full_model kiểm tra deadline nhất quán
        deadline_past = time.perf_counter() - 0.001
        with self.assertRaises(_TimeoutException):
            self.solver._build_full_model({}, num_vars=5, deadline=deadline_past)


if __name__ == "__main__":
    unittest.main()
