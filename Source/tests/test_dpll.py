"""test DPLL: Unit Propagation & Conflict Detection
"""
import unittest

from logic.dpll import DPLLSolver


class TestDPLLUnitPropagationAndConflict(unittest.TestCase):
    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_empty_clause_causes_immediate_conflict(self) -> None:
        """Mệnh đề rỗng [] phải gây ra conflict ngay lập tức."""
        clauses = [[]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertTrue(is_conf)
        self.assertEqual(conf_clause, [])
        self.assertEqual(len(assignment), 0)
        self.assertEqual(self.solver.stats.propagations, 0)

    def test_single_positive_unit_clause(self) -> None:
        """Mệnh đề đơn dương [1] phải ép biến 1 nhận giá trị True."""
        clauses = [[1]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertEqual(assignment, {1: True})
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_single_negative_unit_clause(self) -> None:
        """Mệnh đề đơn âm [-2] phải ép biến 2 nhận giá trị False."""
        clauses = [[-2]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertEqual(assignment, {2: False})
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_cascading_unit_propagation(self) -> None:
        """Lan truyền liên hoàn: [1], [-1, 2], [-2, 3], [-3, 4]."""
        clauses = [[1], [-1, 2], [-2, 3], [-3, 4]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertEqual(assignment, {1: True, 2: True, 3: True, 4: True})
        self.assertEqual(self.solver.stats.propagations, 4)

    def test_conflict_between_opposing_unit_clauses(self) -> None:
        """Hai mệnh đề đơn mâu thuẫn trực tiếp [1] và [-1] phải báo conflict."""
        clauses = [[1], [-1]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertTrue(is_conf)
        self.assertEqual(conf_clause, [-1])
        self.assertEqual(assignment, {1: True})
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_cascading_leads_to_conflict(self) -> None:
        """Chuỗi lan truyền dẫn tới xung đột: [1] -> 2 -> mâu thuẫn với [-2]."""
        clauses = [[1], [-1, 2], [-2]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertTrue(is_conf)
        self.assertEqual(conf_clause, [-2])
        self.assertEqual(assignment, {1: True, 2: True})
        self.assertEqual(self.solver.stats.propagations, 2)

    def test_longer_clause_shrinks_to_unit(self) -> None:
        """Mệnh đề [1, 2, 3] khi 1=False, 2=False sẽ trở thành unit clause suy ra 3=True."""
        clauses = [[1, 2, 3]]
        assignment = {1: False, 2: False}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertEqual(assignment[3], True)
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_satisfied_clause_ignored(self) -> None:
        """Mệnh đề đã thỏa mãn không được coi là unit clause hay conflict."""
        clauses = [[1, 2], [-1, 3]]
        assignment = {1: True, 3: True}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertNotIn(2, assignment)
        self.assertEqual(self.solver.stats.propagations, 0)

    def test_duplicate_literals_in_clause(self) -> None:
        """Mệnh đề có literal trùng lặp [1, 1] vẫn nhận diện đúng là unit clause."""
        clauses = [[1, 1]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertEqual(assignment, {1: True})
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_tautology_clause(self) -> None:
        """Mệnh đề chứa cả x và ¬x không gây conflict và tự satisfied khi gán."""
        clauses = [[1, -1], [2]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertEqual(assignment, {2: True})
        self.assertEqual(self.solver.stats.propagations, 1)

    def test_immutable_clauses_after_propagation(self) -> None:
        """Đảm bảo danh sách clauses gốc không bị thay đổi trong quá trình lan truyền."""
        clauses = [[1, 2], [-1, 3], [-3]]
        original_copy = [list(c) for c in clauses]

        assignment = {}
        self.solver.unit_propagate(clauses, assignment)

        self.assertEqual(clauses, original_copy)

    def test_no_unit_clause_does_nothing(self) -> None:
        """Nếu không có unit clause nào, không có biến nào được gán thêm."""
        clauses = [[1, 2], [-1, 3], [2, -3]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)

        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)
        self.assertEqual(assignment, {})
        self.assertEqual(self.solver.stats.propagations, 0)

    def test_get_clause_status_categories(self) -> None:
        """Kiểm tra độ chính xác của hàm phân loại trạng thái mệnh đề."""
        self.assertEqual(self.solver.get_clause_status([], {}), ("CONFLICT", None))
        self.assertEqual(self.solver.get_clause_status([1], {}), ("UNIT", 1))
        self.assertEqual(self.solver.get_clause_status([1, 2], {}), ("UNRESOLVED", None))
        self.assertEqual(self.solver.get_clause_status([1, 2], {1: True}), ("SATISFIED", None))
        self.assertEqual(self.solver.get_clause_status([1, 2], {1: False}), ("UNIT", 2))
        self.assertEqual(
            self.solver.get_clause_status([1, 2], {1: False, 2: False}),
            ("CONFLICT", None)
        )

    def test_is_conflict_helper_method(self) -> None:
        """Kiểm tra phương thức tiện ích is_conflict."""
        clauses = [[1, 2], [-1]]
        self.assertFalse(self.solver.is_conflict(clauses, {}))
        self.assertFalse(self.solver.is_conflict(clauses, {1: False}))
        self.assertTrue(self.solver.is_conflict(clauses, {1: True}))

    def test_deterministic_multiple_units(self) -> None:
        """Nhiều unit clause ban đầu phải được lan truyền theo thứ tự xác định."""
        clauses = [[3], [1], [2]]
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)
        self.assertFalse(is_conf)
        self.assertEqual(assignment, {3: True, 1: True, 2: True})
        self.assertEqual(self.solver.stats.propagations, 3)

    def test_example_from_spec_with_assumptions(self) -> None:
        """Ví dụ trong đề bài: KB = (A ∨ B) ∧ (¬A ∨ B).

        Giả sử B là Innocent (assumption ¬B tức là -2):
        Lan truyền ép A = True từ clause (A ∨ B).
        Sau đó clause (¬A ∨ B) trở thành mâu thuẫn -> UNSAT.
        Kết luận B bắt buộc phải là Criminal.
        """
        # A = 1, B = 2
        clauses = [[1, 2], [-1, 2]]

        # Kiểm tra giả định B = Innocent (literal -2) -> Dẫn tới Conflict
        assignment = {2: False}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)
        self.assertTrue(is_conf)
        self.assertEqual(conf_clause, [-1, 2])
        self.assertEqual(assignment[1], True)

        # Kiểm tra qua solver.solve với assumption
        res_innocent = self.solver.solve(clauses, num_vars=2, assumptions=[-2])
        self.assertFalse(res_innocent.sat)
        self.assertIsNone(res_innocent.model)

    def test_empty_formula_is_sat(self) -> None:
        """Công thức không chứa mệnh đề nào phải thỏa mãn (SAT) và không có conflict."""
        clauses = []
        assignment = {}
        is_conf, conf_clause = self.solver.unit_propagate(clauses, assignment)
        self.assertFalse(is_conf)
        self.assertIsNone(conf_clause)

        result = self.solver.solve(clauses, num_vars=3)
        self.assertTrue(result.sat)
        self.assertIsNotNone(result.model)
        self.assertEqual(len(result.model), 3)

    def test_contradictory_assumptions(self) -> None:
        """Assumptions chứa đồng thời x và ¬x phải lập tức trả về UNSAT."""
        clauses = [[1, 2]]
        result = self.solver.solve(clauses, num_vars=2, assumptions=[1, -1])
        self.assertFalse(result.sat)
        self.assertIsNone(result.model)

    def test_solve_raises_when_branching_needed(self) -> None:
        """Công thức chưa thể kết luận chỉ bằng Unit Propagation sẽ raise NotImplementedError."""
        # Công thức cần rẽ nhánh: (x ∨ y) không có unit clause
        clauses = [[1, 2]]
        with self.assertRaises(NotImplementedError):
            self.solver.solve(clauses, num_vars=2)


if __name__ == "__main__":
    unittest.main()
