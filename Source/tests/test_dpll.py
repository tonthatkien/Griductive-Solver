"""Kiểm thử DPLL: Lan truyền đơn vị và phát hiện xung đột.
"""
import time
import unittest
from typing import Dict, List

from logic.dpll import DPLLSolver, _TimeoutException


class TestDPLLUnitPropagationAndConflict(unittest.TestCase):
    """Kiểm thử thuật toán lan truyền đơn vị và phát hiện xung đột."""

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_unit_propagation_single_and_cascading(self) -> None:
        """Lan truyền mệnh đề đơn lẻ, chuỗi liên hoàn và co gọn mệnh đề nhiều biến."""
        # 1. Đơn dương [1] ép 1 = True
        assign_pos: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[1]], assign_pos)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_pos, {1: True})
        self.assertEqual(self.solver.stats.propagations, 1)

        # 2. Đơn âm [-2] ép 2 = False
        assign_neg: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[-2]], assign_neg)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_neg, {2: False})

        # 3. Lan truyền liên hoàn: [1] -> 2 -> 3 -> 4
        assign_casc: Dict[int, bool] = {}
        casc_clauses = [[1], [-1, 2], [-2, 3], [-3, 4]]
        is_conf, conf_c = self.solver.unit_propagate(casc_clauses, assign_casc)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_casc, {1: True, 2: True, 3: True, 4: True})

        # 4. Mệnh đề [1, 2, 3] khi 1=False, 2=False co gọn thành unit clause suy ra 3=True
        assign_shrink = {1: False, 2: False}
        is_conf, conf_c = self.solver.unit_propagate([[1, 2, 3]], assign_shrink)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertEqual(assign_shrink[3], True)

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
        assign_casc_conf: Dict[int, bool] = {}
        casc_conf_clauses = [[1], [-1, 2], [-2]]
        is_conf, conf_c = self.solver.unit_propagate(casc_conf_clauses, assign_casc_conf)
        self.assertTrue(is_conf)
        self.assertEqual(conf_c, [-2])
        self.assertEqual(assign_casc_conf, {1: True, 2: True})

    def test_clause_filtering_and_edge_cases(self) -> None:
        """Bỏ qua clause đã thỏa mãn, xử lý literal trùng và thứ tự lan truyền xác định."""
        # 1. Mệnh đề đã thỏa mãn không được xem là unit clause hay conflict
        clauses_sat = [[1, 2], [-1, 3]]
        assign_sat = {1: True, 3: True}
        is_conf, conf_c = self.solver.unit_propagate(clauses_sat, assign_sat)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)
        self.assertNotIn(2, assign_sat)

        # 2. Literal trùng lặp [1, 1] vẫn nhận diện đúng là unit clause
        assign_dup: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[1, 1]], assign_dup)
        self.assertFalse(is_conf)
        self.assertEqual(assign_dup, {1: True})

        # 3. Không có unit clause nào -> không gán thêm biến
        assign_empty: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[1, 2], [-1, 3]], assign_empty)
        self.assertFalse(is_conf)
        self.assertEqual(assign_empty, {})

        # 4. Nhiều unit clause ban đầu lan truyền theo thứ tự xác định
        assign_multi: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate([[3], [1], [2]], assign_multi)
        self.assertFalse(is_conf)
        self.assertEqual(assign_multi, {3: True, 1: True, 2: True})

    def test_get_clause_status_and_helpers(self) -> None:
        """Kiểm tra phân loại trạng thái mệnh đề và hàm tiện ích is_conflict."""
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

        # Tiện ích is_conflict
        conflict_clauses = [[1, 2], [-1]]
        self.assertFalse(self.solver.is_conflict(conflict_clauses, {}))
        self.assertFalse(self.solver.is_conflict(conflict_clauses, {1: False}))
        self.assertTrue(self.solver.is_conflict(conflict_clauses, {1: True}))

    def test_tautology_clause(self) -> None:
        """Mệnh đề chứa cả x và ¬x là hằng đúng (Tautology), luôn SAT và không gây conflict.
        """
        # 1. Trạng thái của [1, -1] dưới phép gán rỗng phải là SATISFIED
        self.assertEqual(self.solver.get_clause_status([1, -1], {}), ("SATISFIED", None))

        # 2. unit_propagate trên [[1, -1], [2]] chỉ lan truyền unit clause [2]
        clauses = [[1, -1], [2]]
        assignment: Dict[int, bool] = {}
        is_conf, conf_c = self.solver.unit_propagate(clauses, assignment)
        self.assertFalse(is_conf)
        self.assertEqual(assignment, {2: True})
        self.assertEqual(self.solver.stats.propagations, 1)

        # 3. solve([[1, -1]]) trả về SAT với model hợp lệ mà không cần branching
        res_single = self.solver.solve([[1, -1]], num_vars=1)
        self.assertTrue(res_single.sat)
        self.assertIsNotNone(res_single.model)
        assert res_single.model is not None
        self.assertTrue(self.solver.is_clause_satisfied([1, -1], res_single.model))

        # 4. Tautology kết hợp unit clause: [[1, -1, 2], [-2]]
        res_combined = self.solver.solve([[1, -1, 2], [-2]], num_vars=2)
        self.assertTrue(res_combined.sat)
        self.assertIsNotNone(res_combined.model)
        assert res_combined.model is not None
        for c in [[1, -1, 2], [-2]]:
            self.assertTrue(self.solver.is_clause_satisfied(c, res_combined.model))

    def test_sat_model_validates_all_clauses(self) -> None:
        """Kiểm chứng tính đúng đắn thực sự của SAT model sau khi lan truyền đơn vị.
        """
        clauses = [[1], [-1, 2], [-2, 3]]
        num_vars = 5
        result = self.solver.solve(clauses, num_vars=num_vars)

        self.assertTrue(result.sat)
        self.assertIsNotNone(result.model)
        assert result.model is not None

        # 1. Model chứa đầy đủ biến 1..num_vars
        self.assertEqual(set(result.model.keys()), {1, 2, 3, 4, 5})

        # 2. Các giá trị ép buộc từ unit propagation
        self.assertTrue(result.model[1])
        self.assertTrue(result.model[2])
        self.assertTrue(result.model[3])

        # 3. Mỗi clause đều có ít nhất một literal True dưới model
        for clause in clauses:
            clause_sat = any(
                result.model[abs(lit)] if lit > 0 else not result.model[abs(lit)]
                for lit in clause
            )
            self.assertTrue(clause_sat, msg=f"Mệnh đề {clause} không được thỏa mãn bởi model!")

        # 4. Biến tự do (4, 5) được hoàn thiện mà không làm mất tính thỏa mãn
        self.assertIn(4, result.model)
        self.assertIn(5, result.model)

    def test_clauses_immutability(self) -> None:
        """Bảo đảm danh sách clauses gốc bất biến khi gọi unit_propagate và solve kèm assumptions.

        Đáp ứng nhận xét:
        - solve() là API chính mà các module khác sử dụng.
        - Quá trình propagation và assumptions không được làm thay đổi cấu trúc CNF gốc.
        """
        # 1. Bất biến khi gọi trực tiếp unit_propagate()
        clauses_prop = [[1, 2], [-1, 3], [-3]]
        copy_prop = [list(c) for c in clauses_prop]
        self.solver.unit_propagate(clauses_prop, {})
        self.assertEqual(clauses_prop, copy_prop)

        # 2. Bất biến khi gọi solve() kèm assumptions
        clauses_solve = [[1, 2], [-1, 2]]
        copy_solve = [list(c) for c in clauses_solve]
        self.solver.solve(clauses_solve, num_vars=2, assumptions=[2])
        self.assertEqual(clauses_solve, copy_solve)

    def test_solver_instance_reuse_resets_stats_and_state(self) -> None:
        """Gọi solve() nhiều lần trên cùng 1 instance solver phải reset stats và cô lập state.

        Đáp ứng nhận xét:
        - SolverStats được reset chính xác ở mỗi lần gọi.
        - Số propagation của lần giải trước không ảnh hưởng lần giải sau.
        - Assignment của lần trước không bị tái sử dụng ngoài ý muốn.
        """
        # Lần 1: Giải [[1]] -> model[1] = True, propagations = 1
        res_1 = self.solver.solve([[1]], num_vars=1)
        self.assertTrue(res_1.sat)
        assert res_1.model is not None
        self.assertTrue(res_1.model[1])
        self.assertEqual(res_1.stats.propagations, 1)

        # Lần 2: Giải [[-1]] trên cùng instance -> model[1] phải là False
        res_2 = self.solver.solve([[-1]], num_vars=1)
        self.assertTrue(res_2.sat)
        assert res_2.model is not None
        self.assertFalse(res_2.model[1])
        self.assertEqual(res_2.stats.propagations, 1)

        # Lần 3: Giải bài toán có conflict liên hoàn [[1], [-1, 2], [-2]] -> UNSAT
        res_3 = self.solver.solve([[1], [-1, 2], [-2]], num_vars=2)
        self.assertFalse(res_3.sat)
        self.assertIsNone(res_3.model)
        self.assertEqual(res_3.stats.propagations, 2)

        # Lần 4: Giải lại bài toán đơn vị [[2]] -> propagations reset về 1
        res_4 = self.solver.solve([[2]], num_vars=2)
        self.assertTrue(res_4.sat)
        assert res_4.model is not None
        self.assertTrue(res_4.model[2])
        self.assertEqual(res_4.stats.propagations, 1)

    def test_example_from_spec_with_assumptions(self) -> None:
        """Ví dụ trong đề bài: KB = (A ∨ B) ∧ (¬A ∨ B) với assumptions."""
        clauses = [[1, 2], [-1, 2]]

        # Giả sử B = Innocent (-2) -> ép A=True rồi mâu thuẫn với (¬A ∨ B) -> UNSAT
        assign = {2: False}
        is_conf, conf_c = self.solver.unit_propagate(clauses, assign)
        self.assertTrue(is_conf)
        self.assertEqual(conf_c, [-1, 2])
        self.assertEqual(assign[1], True)

        # Kiểm tra qua API solve() với assumption
        res_innocent = self.solver.solve(clauses, num_vars=2, assumptions=[-2])
        self.assertFalse(res_innocent.sat)
        self.assertIsNone(res_innocent.model)

    def test_empty_formula_is_sat(self) -> None:
        """Công thức không chứa mệnh đề nào là SAT và model đủ num_vars."""
        clauses: List[List[int]] = []
        is_conf, conf_c = self.solver.unit_propagate(clauses, {})
        self.assertFalse(is_conf)
        self.assertIsNone(conf_c)

        result = self.solver.solve(clauses, num_vars=3)
        self.assertTrue(result.sat)
        self.assertIsNotNone(result.model)
        assert result.model is not None
        self.assertEqual(len(result.model), 3)

    def test_contradictory_assumptions(self) -> None:
        """Assumptions chứa đồng thời x và ¬x phải lập tức trả về UNSAT."""
        result = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertFalse(result.sat)
        self.assertIsNone(result.model)

    def test_formula_requiring_branching_raises_not_implemented(self) -> None:
        """Ranh giới Task D1 -> D2: Công thức cần rẽ nhánh ném NotImplementedError."""
        # (x1 ∨ x2) không có unit clause ban đầu, cần branching (thuộc Task D2)
        with self.assertRaises(NotImplementedError):
            self.solver.solve([[1, 2]], num_vars=2)

    def test_input_validation(self) -> None:
        """Xác thực toàn diện đầu vào: từ chối kiểu sai, giá trị ngoài phạm vi, literal 0, NaN."""
        # 1. Literal 0
        with self.assertRaises(ValueError):
            self.solver.solve([[0]], num_vars=2)
        with self.assertRaises(ValueError):
            self.solver.solve([[1]], num_vars=2, assumptions=[0])

        # 2. Vượt phạm vi num_vars hoặc num_vars âm
        with self.assertRaises(ValueError):
            self.solver.solve([[3]], num_vars=2)
        with self.assertRaises(ValueError):
            self.solver.solve([[1]], num_vars=2, assumptions=[-3])
        with self.assertRaises(ValueError):
            self.solver.solve([], num_vars=-1)

        # 3. Kiểu dữ liệu không phải int (float, bool, str)
        with self.assertRaises(TypeError):
            self.solver.solve([], num_vars=1.5)
        with self.assertRaises(TypeError):
            self.solver.solve([], num_vars=True)  
        with self.assertRaises(TypeError):
            self.solver.solve([[1.5]], num_vars=2)  
        with self.assertRaises(TypeError):
            self.solver.solve([[1, True]], num_vars=2)  
        with self.assertRaises(TypeError):
            self.solver.solve([[1]], num_vars=2, assumptions=[False])  

        # 4. Timeout không hợp lệ (NaN, chuỗi, bool)
        with self.assertRaises(ValueError):
            self.solver.solve([[1]], num_vars=1, timeout=float("nan"))
        with self.assertRaises(TypeError):
            self.solver.solve([[1]], num_vars=1, timeout="1.0") 
        with self.assertRaises(TypeError):
            self.solver.solve([[1]], num_vars=1, timeout=True)  

    def test_iterator_and_generator_safety(self) -> None:
        """Hỗ trợ an toàn các cấu trúc iterator/generator và không nuốt lỗi RecursionError."""
        # 1. Iterator clauses mâu thuẫn không bị cạn kiệt trong lúc validate -> trả về UNSAT
        res_iter = self.solver.solve(iter([[1], [-1]]), num_vars=1)  
        self.assertFalse(res_iter.sat)

        # 2. Generator clauses hợp lệ giải quyết bằng unit propagation -> SAT
        gen_c = (c for c in [[1], [-1, 2]])
        res_gen = self.solver.solve(gen_c, num_vars=2)  
        self.assertTrue(res_gen.sat)
        assert res_gen.model is not None
        self.assertTrue(res_gen.model[1] and res_gen.model[2])

        # 3. Generator assumptions mâu thuẫn -> UNSAT
        gen_assump = (lit for lit in [-2])
        res_assump = self.solver.solve([[1, 2], [-1, 2]], num_vars=2, assumptions=gen_assump)
        self.assertFalse(res_assump.sat)

        # 4. Generator đệ quy bất thường thành UNSAT
        def _recursive_gen():
            yield from _recursive_gen()

        with self.assertRaises(RecursionError):
            self.solver.solve(_recursive_gen(), num_vars=1)

    def test_timeout_handling(self) -> None:
        """Kiểm soát timeout chính xác: ngắt ngay lập tức hoặc ngắt giữa chừng khi xử lý lớn."""
        # 1. Timeout = 0.0 lập tức dừng mà không treo
        res_zero = self.solver.solve([[1]], num_vars=1, timeout=0.0)
        self.assertTrue(res_zero.timed_out)
        self.assertFalse(res_zero.sat)

        # 2. Timeout ngắt giữa chuỗi lan truyền lớn
        large_clauses = [[1]] + [[-i, i + 1] for i in range(1, 10000)]
        res_prop = self.solver.solve(large_clauses, num_vars=10001, timeout=1e-6)
        self.assertTrue(res_prop.timed_out)

        # 3. Timeout ngắt an toàn trước generator assumptions vô hạn
        def _infinite_assumptions():
            while True:
                yield 1

        res_inf = self.solver.solve(
            [[1]], num_vars=1, assumptions=_infinite_assumptions(), timeout=0.005
        )
        self.assertTrue(res_inf.timed_out)

        # 4. _build_full_model ném _TimeoutException khi dựng model cho số lượng biến cực lớn
        deadline = time.perf_counter() + 0.002
        with self.assertRaises(_TimeoutException):
            self.solver._build_full_model({}, num_vars=2_000_000, deadline=deadline)


if __name__ == "__main__":
    unittest.main()
