"""Kiểm thử DPLL: Lan truyền đơn vị và phát hiện xung đột
"""
import time
import unittest
from typing import Dict, List, Tuple
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

        # 2. Chuỗi kết hợp làm gọn mệnh đề:
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
        """Bảo đảm clauses gốc bất biến khi gọi unit_propagate, solve và khi rẽ nhánh."""
        clauses = [[1, 2], [-1, 2]]
        copy_c = [list(c) for c in clauses]

        self.solver.unit_propagate(clauses, {})
        self.assertEqual(clauses, copy_c)

        self.solver.solve(clauses, num_vars=2, assumptions=[2])
        self.assertEqual(clauses, copy_c)

        # Bảo đảm tính bất biến khi solve phải rẽ nhánh / quay lui
        clauses_branch = [[1, 2], [-1, 3], [-1, -3]]
        copy_b = [list(c) for c in clauses_branch]
        self.solver.solve(clauses_branch, num_vars=3)
        self.assertEqual(clauses_branch, copy_b)

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


class TestDPLLBranchingAndBacktracking(unittest.TestCase):
    """Kiểm thử thuật toán DPLL: chọn biến deterministic, branching và backtracking."""

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_choose_variable_heuristic(self) -> None:
        """Kiểm tra toàn diện heuristic chọn biến phân nhánh trong choose_variable:
        mệnh đề ngắn nhất, phân xử hòa, bỏ qua clause đã thỏa, literal trùng lặp và deadline.
        """
        # 1. Chọn biến nhỏ nhất trong mệnh đề chưa thỏa mãn ngắn nhất
        clauses = [[3, 4, 5], [2, 6]]
        self.assertEqual(self.solver.choose_variable(clauses, {}), 2)

        # 2. Phân xử hòa: nhiều mệnh đề cùng độ dài nhỏ nhất -> chọn biến nhỏ nhất giữa chúng
        # Bất biến theo thứ tự mệnh đề (tính tất định - deterministic)
        self.assertEqual(self.solver.choose_variable([[3, 4], [2, 5]], {}), 2)
        self.assertEqual(self.solver.choose_variable([[2, 5], [3, 4]], {}), 2)

        # 3. Bỏ qua các mệnh đề đã thỏa mãn; trả về None khi toàn bộ đã thỏa
        self.assertEqual(self.solver.choose_variable([[1, 2], [3, 4, 5]], {1: True}), 3)
        self.assertIsNone(self.solver.choose_variable([[1, 2], [-1, 3]], {1: True, 3: True}))

        # 4. Độ dài mệnh đề tính theo số biến chưa gán phân biệt (loại trừ literal trùng lặp)
        # [3, 3, 3, 3] có 1 biến chưa gán {3} nên ngắn hơn [4, 5] có 2 biến {4, 5} -> chọn 3
        self.assertEqual(self.solver.choose_variable([[4, 5], [3, 3, 3, 3]], {}), 3)

        # 5. Kiểm tra deadline định kỳ khi quét literal của mệnh đề dài trong choose_variable
        long_clause = [list(range(1, 101))]
        calls = 0

        def mock_time() -> float:
            nonlocal calls
            calls += 1
            return 101.0 if calls >= 4 else 100.0

        with patch("time.perf_counter", side_effect=mock_time):
            with self.assertRaises(_TimeoutException):
                self.solver.choose_variable(long_clause, {}, deadline=100.5)
        self.assertGreaterEqual(calls, 4)

    def test_branching_and_backtracking_mechanics(self) -> None:
        """Kiểm tra cơ chế rẽ nhánh nhị phân (True/False), quay lui khi conflict và cô lập state."""
        # 1. Nhánh True đầu tiên thỏa mãn công thức ngay thì không cần quay lui
        res_first = self.solver.solve([[1, 2]], num_vars=2)
        self.assertTrue(res_first.sat and res_first.model and res_first.model[1] is True)
        self.assertEqual(res_first.stats.decisions, 1)
        self.assertEqual(res_first.stats.backtracks, 0)

        # 2. Nhánh True mâu thuẫn -> quay lui thử nhánh False thành công (1 backtrack)
        # (x1 ∨ x2) ∧ (¬x1 ∨ x3) ∧ (¬x1 ∨ ¬x3): x1=True gây conflict, quay lui sang x1=False
        clauses_conflict = [[1, 2], [-1, 3], [-1, -3]]
        copy_c = [list(c) for c in clauses_conflict]
        res_bt = self.solver.solve(clauses_conflict, num_vars=3)
        self.assertEqual(clauses_conflict, copy_c)
        self.assertTrue(res_bt.sat)
        self.assertIsNotNone(res_bt.model)
        assert res_bt.model is not None
        self.assertFalse(res_bt.model[1])
        self.assertTrue(res_bt.model[2])
        self.assertEqual(res_bt.stats.decisions, 1)
        self.assertEqual(res_bt.stats.backtracks, 1)

        # 3. Phép gán từ nhánh thất bại không bị rò rỉ sang nhánh tiếp theo (x3 tự do nhận False)
        self.assertFalse(res_bt.model[3])

        # 4. Công thức UNSAT: cả hai nhánh đều mâu thuẫn và quay lui về gốc
        clauses_unsat = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        res_unsat = self.solver.solve(clauses_unsat, num_vars=2)
        self.assertFalse(res_unsat.sat)
        self.assertIsNone(res_unsat.model)
        self.assertEqual(res_unsat.stats.decisions, 1)
        self.assertEqual(res_unsat.stats.backtracks, 2)

        # 5. Kết hợp assumptions với branching: [[1, 2, 3], [-1, 2], [-2, -3]] với assumptions=[-3]
        clauses_assump_branch = [[1, 2, 3], [-1, 2], [-2, -3]]
        copy_ab = [list(c) for c in clauses_assump_branch]
        res_ab = self.solver.solve(clauses_assump_branch, num_vars=3, assumptions=[-3])
        self.assertEqual(clauses_assump_branch, copy_ab)
        self.assertTrue(res_ab.sat)
        self.assertIsNotNone(res_ab.model)
        assert res_ab.model is not None
        self.assertFalse(res_ab.model[3])
        self.assertTrue(res_ab.model[2])
        self.assertTrue(res_ab.model[1])
        self.assertEqual(res_ab.stats.decisions, 1)

    def test_multilevel_search_and_deduction(self) -> None:
        """Kiểm tra đệ quy rẽ nhánh nhiều tầng và ví dụ suy diễn entailment từ đề bài."""
        # 1. Rẽ nhánh nhiều tầng (multi-level branching)
        # (x1 ∨ x2 ∨ x3) ∧ (¬x1 ∨ x2) ∧ (¬x2 ∨ ¬x3) ∧ (¬x1 ∨ ¬x2)
        clauses = [[1, 2, 3], [-1, 2], [-2, -3], [-1, -2]]
        res_multi = self.solver.solve(clauses, num_vars=3)
        self.assertTrue(res_multi.sat and res_multi.model)
        assert res_multi.model is not None
        for c in clauses:
            self.assertTrue(self.solver.is_clause_satisfied(c, res_multi.model))
        self.assertGreaterEqual(res_multi.stats.decisions, 2)
        self.assertGreaterEqual(res_multi.stats.backtracks, 1)

        # 2. Ví dụ trong đề bài: KB = (A ∨ B) ∧ (¬A ∨ B) với A = 1, B = 2
        spec_kb = [[1, 2], [-1, 2]]
        # KB ∧ ¬B là UNSAT -> chứng minh B là Criminal (True)
        self.assertFalse(self.solver.solve(spec_kb, num_vars=2, assumptions=[-2]).sat)
        # KB ∧ B là SAT
        res_b = self.solver.solve(spec_kb, num_vars=2, assumptions=[2])
        self.assertTrue(res_b.sat and res_b.model and res_b.model[2] is True)
        # KB ∧ A và KB ∧ ¬A đều SAT -> A là UNKNOWN
        self.assertTrue(self.solver.solve(spec_kb, num_vars=2, assumptions=[1]).sat)
        self.assertTrue(self.solver.solve(spec_kb, num_vars=2, assumptions=[-1]).sat)

    def test_model_and_solver_properties(self) -> None:
        """Kiểm chứng tính đầy đủ của model, tính tất định và xử lý timeout khi rẽ nhánh."""
        # 1. Mọi biến 1..num_vars đều có mặt trong model (kể cả biến tự do 3, 4)
        res_model = self.solver.solve([[1, 2]], num_vars=4)
        self.assertTrue(res_model.sat and res_model.model)
        assert res_model.model is not None
        self.assertEqual(set(res_model.model.keys()), {1, 2, 3, 4})

        # 2. Tính tất định: 2 lần giải liên tiếp cho ra model và stats trùng khớp 100%
        clauses = [[1, 2, 3], [-1, 2], [-2, -3], [-1, -2]]
        run1 = self.solver.solve(clauses, num_vars=3)
        run2 = self.solver.solve(clauses, num_vars=3)
        self.assertEqual(run1.sat, run2.sat)
        self.assertEqual(run1.model, run2.model)
        self.assertEqual(run1.stats.decisions, run2.stats.decisions)
        self.assertEqual(run1.stats.propagations, run2.stats.propagations)
        self.assertEqual(run1.stats.backtracks, run2.stats.backtracks)

        # 3. Timeout = 0.0 lập tức trả về kết quả timeout mà không treo
        res_timeout = self.solver.solve(
            [[1, 2], [-1, 2], [1, -2], [-1, -2]], num_vars=2, timeout=0.0
        )
        self.assertTrue(res_timeout.timed_out)
        self.assertFalse(res_timeout.sat)
        self.assertIsNone(res_timeout.model)

    def test_random_cnf_matches_brute_force(self) -> None:
        """Đối chiếu kết quả DPLL với Brute Force trên 200 random CNF nhỏ (có seed cố định)."""
        import itertools
        import random

        rng = random.Random(2026)
        for _ in range(200):
            n = rng.randint(1, 6)
            clauses = [
                [rng.choice([-1, 1]) * rng.randint(1, n) for _ in range(rng.randint(1, 3))]
                for _ in range(rng.randint(0, 12))
            ]

            def sat_under(a: Tuple[bool, ...]) -> bool:
                return all(any(a[abs(lit) - 1] == (lit > 0) for lit in c) for c in clauses)

            expected = any(sat_under(a) for a in itertools.product([False, True], repeat=n))
            res = self.solver.solve(clauses, num_vars=n)
            self.assertEqual(res.sat, expected, f"Lệch kết quả tại clauses: {clauses}")
            if res.sat:
                self.assertIsNotNone(res.model)
                assert res.model is not None
                self.assertTrue(
                    all(self.solver.is_clause_satisfied(c, res.model) for c in clauses)
                )


class TestDPLLAssumptionsAndModel(unittest.TestCase):
    """Kiểm thử DPLL với assumptions và trả kết quả SAT/UNSAT kèm model."""

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_solve_preserves_kb_clauses_and_assumptions(self) -> None:
        """Hàm solve không làm biến đổi danh sách mệnh đề gốc và assumptions."""
        # 1. Kiểm tra bất biến khi suy diễn bằng lan truyền đơn vị
        clauses = [[1, 2], [-1, 2], [-2, 3]]
        copy_clauses = [list(c) for c in clauses]
        clause_ids = [id(c) for c in clauses]

        assumptions = [-2]
        copy_assumptions = list(assumptions)

        res = self.solver.solve(clauses, num_vars=3, assumptions=assumptions)
        self.assertEqual(clauses, copy_clauses)
        self.assertEqual([id(c) for c in clauses], clause_ids)
        self.assertEqual(assumptions, copy_assumptions)

        # 2. Kiểm tra bất biến khi giải thuật thực sự kích hoạt rẽ nhánh và quay lui
        # (x1 ∨ x2) ∧ (¬x1 ∨ x3) ∧ (¬x1 ∨ ¬x3) ∧ (x4 ∨ x5) với assumption [-5]:
        # Nhánh 1=True dẫn tới mâu thuẫn giữa x3 và ¬x3, buộc DPLL phải quay lui sang 1=False.
        clauses_bt = [[1, 2], [-1, 3], [-1, -3], [4, 5]]
        copy_clauses_bt = [list(c) for c in clauses_bt]
        clause_ids_bt = [id(c) for c in clauses_bt]

        assump_bt = [-5]
        copy_assump_bt = list(assump_bt)

        res_bt = self.solver.solve(clauses_bt, num_vars=5, assumptions=assump_bt)
        # Xác nhận có kích hoạt quay lui trong quá trình tìm kiếm
        self.assertTrue(res_bt.sat)
        self.assertGreaterEqual(res_bt.stats.backtracks, 1)
        # Dữ liệu clauses và assumptions không bị biến đổi sau khi quay lui
        self.assertEqual(clauses_bt, copy_clauses_bt)
        self.assertEqual([id(c) for c in clauses_bt], clause_ids_bt)
        self.assertEqual(assump_bt, copy_assump_bt)

    def test_sat_returns_complete_model_satisfying_all_constraints(self) -> None:
        """Khi SAT, model trả về chứa đủ mọi biến từ 1 đến num_vars và thỏa mãn toàn bộ mệnh đề."""
        clauses = [[1, 2], [-1, 3]]
        res = self.solver.solve(clauses, num_vars=5, assumptions=[2])
        self.assertTrue(res.sat)
        self.assertIsNotNone(res.model)
        assert res.model is not None

        # Model phải có đầy đủ mọi biến từ 1 đến num_vars
        self.assertEqual(set(res.model.keys()), {1, 2, 3, 4, 5})

        # Giá trị assumption phải được thỏa mãn
        self.assertTrue(res.model[2])

        # Toàn bộ mệnh đề phải thỏa mãn
        for c in clauses:
            self.assertTrue(self.solver.is_clause_satisfied(c, res.model))

    def test_unsat_returns_none_model(self) -> None:
        """Khi UNSAT, cờ sat là False, model là None và timed_out là False."""
        # 1. Công thức vô nghiệm ngay từ clauses gốc
        res_conflict = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertFalse(res_conflict.sat)
        self.assertIsNone(res_conflict.model)
        self.assertFalse(res_conflict.timed_out)

        # 2. Assumptions tự mâu thuẫn trực tiếp
        res_assump_conflict = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertFalse(res_assump_conflict.sat)
        self.assertIsNone(res_assump_conflict.model)
        self.assertFalse(res_assump_conflict.timed_out)

        # 3. Assumption xung đột với unit clause
        res_unit_conflict = self.solver.solve([[1]], num_vars=2, assumptions=[-1])
        self.assertFalse(res_unit_conflict.sat)
        self.assertIsNone(res_unit_conflict.model)
        self.assertFalse(res_unit_conflict.timed_out)

        # 4. Assumption dẫn tới mâu thuẫn qua nhiều bước suy diễn
        clauses = [[1, 2], [-1, 2]]
        res_deduced_conflict = self.solver.solve(clauses, num_vars=2, assumptions=[-2])
        self.assertFalse(res_deduced_conflict.sat)
        self.assertIsNone(res_deduced_conflict.model)
        self.assertFalse(res_deduced_conflict.timed_out)

    def test_free_variables_assigned_in_full_model(self) -> None:
        """Biến tự do không xuất hiện trong mệnh đề vẫn có mặt trong model với giá trị mặc định."""
        clauses = [[1, 2]]
        res = self.solver.solve(clauses, num_vars=6, assumptions=[1, 4])
        self.assertTrue(res.sat)
        self.assertIsNotNone(res.model)
        assert res.model is not None

        self.assertEqual(set(res.model.keys()), {1, 2, 3, 4, 5, 6})
        self.assertTrue(res.model[1])
        self.assertTrue(res.model[4])  # Biến tự do được cố định qua assumption
        self.assertFalse(res.model[3])  # Biến tự do mặc định False
        self.assertFalse(res.model[5])
        self.assertFalse(res.model[6])

    def test_empty_formula_and_zero_vars(self) -> None:
        """Xử lý đúng công thức rỗng và num_vars bằng 0."""
        # num_vars = 0, clauses rỗng
        res_zero = self.solver.solve([], num_vars=0)
        self.assertTrue(res_zero.sat)
        self.assertEqual(res_zero.model, {})

        # num_vars = 3, clauses rỗng
        res_empty = self.solver.solve([], num_vars=3, assumptions=[2])
        self.assertTrue(res_empty.sat)
        self.assertEqual(res_empty.model, {1: False, 2: True, 3: False})

    def test_assumptions_iterable_types_and_none(self) -> None:
        """Hỗ trợ nhiều kiểu sequence khác nhau cho assumptions, bao gồm None."""
        clauses = [[1, 2], [-1, 2]]

        # assumptions = None (mặc định rỗng)
        res_none = self.solver.solve(clauses, num_vars=2, assumptions=None)
        self.assertTrue(res_none.sat and res_none.model)

        # assumptions dạng tuple
        res_tuple = self.solver.solve(clauses, num_vars=2, assumptions=(-2,))
        self.assertFalse(res_tuple.sat)
        self.assertIsNone(res_tuple.model)
        self.assertFalse(res_tuple.timed_out)

        # assumptions dạng generator
        res_gen = self.solver.solve(clauses, num_vars=2, assumptions=(lit for lit in [2]))
        self.assertTrue(res_gen.sat and res_gen.model and res_gen.model[2] is True)

        # assumptions có literal lặp cùng dấu
        res_dup = self.solver.solve(clauses, num_vars=2, assumptions=[2, 2])
        self.assertTrue(res_dup.sat and res_dup.model and res_dup.model[2] is True)

    def test_griductive_entailment_semantics(self) -> None:
        """Kiểm tra 4 trạng thái suy diễn logic theo tài liệu thiết kế đồ án."""
        # KB = (A ∨ B) ∧ (¬A ∨ B), với A = 1, B = 2
        kb = [[1, 2], [-1, 2]]

        # KB ∧ ¬B vô nghiệm (UNSAT) => B là Criminal (bắt buộc True)
        res_not_b = self.solver.solve(kb, num_vars=2, assumptions=[-2])
        self.assertFalse(res_not_b.sat)
        self.assertIsNone(res_not_b.model)
        self.assertFalse(res_not_b.timed_out)

        # KB ∧ B có nghiệm (SAT)
        res_b = self.solver.solve(kb, num_vars=2, assumptions=[2])
        self.assertTrue(res_b.sat)
        self.assertIsNotNone(res_b.model)
        assert res_b.model is not None
        self.assertTrue(res_b.model[2])

        # KB ∧ A và KB ∧ ¬A đều SAT => trạng thái của A là Unknown
        res_a = self.solver.solve(kb, num_vars=2, assumptions=[1])
        res_not_a = self.solver.solve(kb, num_vars=2, assumptions=[-1])
        self.assertTrue(res_a.sat)
        self.assertTrue(res_not_a.sat)

        # KB tự mâu thuẫn => Inconsistent
        inconsistent_kb = [[1], [-1]]
        res_inconsistent = self.solver.solve(inconsistent_kb, num_vars=1)
        self.assertFalse(res_inconsistent.sat)
        self.assertIsNone(res_inconsistent.model)
        self.assertFalse(res_inconsistent.timed_out)

    def test_solver_reuse_with_changing_assumptions(self) -> None:
        """Các lần gọi solve liên tiếp trên cùng solver không gây rò rỉ trạng thái."""
        clauses = [[1, 2]]

        res1 = self.solver.solve(clauses, num_vars=2, assumptions=[1])
        self.assertTrue(res1.sat and res1.model and res1.model[1] is True)

        res2 = self.solver.solve(clauses, num_vars=2, assumptions=[-1])
        self.assertTrue(
            res2.sat and res2.model and res2.model[1] is False and res2.model[2] is True
        )

        res3 = self.solver.solve(clauses, num_vars=2, assumptions=[-1, -2])
        self.assertFalse(res3.sat)
        self.assertIsNone(res3.model)
        self.assertFalse(res3.timed_out)

        res4 = self.solver.solve(clauses, num_vars=2, assumptions=[])
        self.assertTrue(res4.sat and res4.model)

    def test_uniqueness_check_blocks_only_primary_variables(self) -> None:
        """Kiểm tra tính duy nhất của nghiệm puzzle bằng blocking clause trên biến primary.

        Quy ước (uniqueness_check):
        Một puzzle có nghiệm duy nhất khi không có nghiệm thứ hai trên các ô của lưới
        (biến primary: 1..num_primary). Biến phụ (auxiliary: > num_primary) chỉ hỗ trợ
        encoding logic, không đại diện cho ô nhân vật. Do đó blocking clause chỉ phủ
        định các biến primary, tránh nhầm lẫn việc biến phụ đổi giá trị thành nghiệm puzzle mới.
        """
        # Giả sử puzzle có 2 biến primary (1, 2) và 1 biến phụ (3)
        num_primary = 2
        num_vars = 3

        # Ràng buộc: ô 1 là True, ô 2 là True; biến 3 là biến phụ tự do
        clauses = [[1], [2]]

        # Tìm nghiệm đầu tiên
        res1 = self.solver.solve(clauses, num_vars=num_vars)
        self.assertTrue(res1.sat)
        self.assertIsNotNone(res1.model)
        assert res1.model is not None
        self.assertTrue(res1.model[1] and res1.model[2])

        # Nếu chặn cả biến phụ (1..num_vars), nghiệm thứ hai vẫn tồn tại vì biến phụ 3 đổi giá trị
        naive_blocking = [-var if res1.model[var] else var for var in range(1, num_vars + 1)]
        res_naive = self.solver.solve(clauses + [naive_blocking], num_vars=num_vars)
        self.assertTrue(res_naive.sat)  # Vẫn SAT vì chỉ khác biến phụ

        #Chỉ tạo blocking clause trên các biến primary (1..num_primary)
        primary_blocking = [
            -var if res1.model[var] else var for var in range(1, num_primary + 1)
        ]
        self.assertEqual(primary_blocking, [-1, -2])

        # Giải lại với blocking clause primary: không còn nghiệm nào khác cho các ô trên lưới
        clauses_with_block = clauses + [primary_blocking]
        res_unique = self.solver.solve(clauses_with_block, num_vars=num_vars)

        self.assertFalse(res_unique.sat)
        self.assertIsNone(res_unique.model)
        self.assertFalse(res_unique.timed_out)

        # Danh sách clauses ban đầu không bị biến đổi
        self.assertEqual(clauses, [[1], [2]])


class TestDPLLPhase1Statistics(unittest.TestCase):
    """Kiểm thử chuẩn hóa bộ đếm thống kê SolverStats.

    Xác minh đúng đắn của decisions, propagations, backtracks, runtime và tính
    độc lập giữa các lần gọi solve() theo đúng quy ước mã nguồn.
    """

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_pure_unit_propagation_stats(self) -> None:
        """Công thức giải thuần bằng Unit Propagation thì decisions=0, backtracks=0."""
        clauses = [[1], [-1, 2], [-2, 3]]
        res = self.solver.solve(clauses, num_vars=3)

        self.assertTrue(res.sat)
        self.assertEqual(res.stats.decisions, 0)
        self.assertEqual(res.stats.propagations, 3)
        self.assertEqual(res.stats.backtracks, 0)
        self.assertGreaterEqual(res.stats.runtime, 0.0)

    def test_assumptions_do_not_count_as_propagations(self) -> None:
        """Assumptions được đưa thẳng vào bảng gán ban đầu, không tăng propagations."""
        # Assumptions thỏa mãn clause ngay từ đầu -> không có unit propagation
        res = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1])
        self.assertTrue(res.sat)
        self.assertEqual(res.stats.propagations, 0)
        self.assertEqual(res.stats.decisions, 0)
        self.assertEqual(res.stats.backtracks, 0)

        # Công thức rỗng với nhiều assumptions -> propagations vẫn là 0
        res_empty = self.solver.solve([], num_vars=3, assumptions=[1, -2, 3])
        self.assertTrue(res_empty.sat)
        self.assertEqual(res_empty.stats.propagations, 0)
        self.assertEqual(res_empty.stats.decisions, 0)
        self.assertEqual(res_empty.stats.backtracks, 0)

    def test_branching_and_backtracks_accounting(self) -> None:
        """Kiểm tra đếm decisions và backtracks theo từng nhánh đệ quy thất bại."""
        # 1. Rẽ nhánh 1 tầng, nhánh True thỏa mãn ngay -> 1 decision, 0 backtrack
        res_first = self.solver.solve([[1, 2]], num_vars=2)
        self.assertTrue(res_first.sat)
        self.assertEqual(res_first.stats.decisions, 1)
        self.assertEqual(res_first.stats.backtracks, 0)

        # 2. Nhánh True mâu thuẫn, nhánh False thỏa mãn -> 1 decision, 1 backtrack
        clauses_tf = [[1, 2], [-1, 3], [-1, -3]]
        res_tf = self.solver.solve(clauses_tf, num_vars=3)
        self.assertTrue(res_tf.sat)
        self.assertEqual(res_tf.stats.decisions, 1)
        self.assertEqual(res_tf.stats.backtracks, 1)

        # 3. Cả 2 nhánh True và False đều mâu thuẫn -> 1 decision, 2 backtracks
        clauses_unsat = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        res_unsat = self.solver.solve(clauses_unsat, num_vars=2)
        self.assertFalse(res_unsat.sat)
        self.assertEqual(res_unsat.stats.decisions, 1)
        self.assertEqual(res_unsat.stats.backtracks, 2)

    def test_direct_assumptions_conflict_stats(self) -> None:
        """Assumptions tự mâu thuẫn thoát sớm: decisions=0, propagations=0, backtracks=0."""
        res = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertFalse(res.sat)
        self.assertIsNone(res.model)
        self.assertFalse(res.timed_out)
        self.assertEqual(res.stats.decisions, 0)
        self.assertEqual(res.stats.propagations, 0)
        self.assertEqual(res.stats.backtracks, 0)
        self.assertGreaterEqual(res.stats.runtime, 0.0)

    def test_runtime_recorded_in_all_exit_paths(self) -> None:
        """Runtime được đo bằng time.perf_counter() và cập nhật ở mọi ngõ thoát."""
        # Thoát sớm khi timeout < 0 hoặc timeout == 0
        res_neg = self.solver.solve([[1]], num_vars=1, timeout=-1.0)
        self.assertTrue(res_neg.timed_out)
        self.assertGreaterEqual(res_neg.stats.runtime, 0.0)

        res_zero = self.solver.solve([[1]], num_vars=1, timeout=0.0)
        self.assertTrue(res_zero.timed_out)
        self.assertGreaterEqual(res_zero.stats.runtime, 0.0)

        # Thoát sớm khi assumptions mâu thuẫn
        res_conflict = self.solver.solve([[1]], num_vars=1, assumptions=[1, -1])
        self.assertGreaterEqual(res_conflict.stats.runtime, 0.0)

        # Ngõ SAT bình thường
        res_sat = self.solver.solve([[1]], num_vars=1)
        self.assertGreaterEqual(res_sat.stats.runtime, 0.0)

        # Ngõ UNSAT bình thường
        res_unsat = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertGreaterEqual(res_unsat.stats.runtime, 0.0)

    def test_stats_independent_reset_across_calls(self) -> None:
        """Mỗi lần gọi solve() phải reset hoàn toàn SolverStats, không cộng dồn."""
        # Lần 1: Pure unit propagation
        res1 = self.solver.solve([[1], [-1, 2]], num_vars=2)
        self.assertEqual(res1.stats.decisions, 0)
        self.assertEqual(res1.stats.propagations, 2)
        self.assertEqual(res1.stats.backtracks, 0)

        # Lần 2: Xung đột assumptions trực tiếp
        res2 = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertEqual(res2.stats.decisions, 0)
        self.assertEqual(res2.stats.propagations, 0)
        self.assertEqual(res2.stats.backtracks, 0)

        # Lần 3: Rẽ nhánh có quay lui
        res3 = self.solver.solve([[1, 2], [-1, 3], [-1, -3]], num_vars=3)
        self.assertEqual(res3.stats.decisions, 1)
        self.assertEqual(res3.stats.backtracks, 1)

        # Lần 4: Chạy lại bài toán đơn giản, xác nhận sạch sẽ
        res4 = self.solver.solve([[1]], num_vars=1)
        self.assertEqual(res4.stats.decisions, 0)
        self.assertEqual(res4.stats.propagations, 1)
        self.assertEqual(res4.stats.backtracks, 0)
        self.assertGreaterEqual(res4.stats.runtime, 0.0)


class TestDPLLPhase2Timeout(unittest.TestCase):
    """Kiểm thử cơ chế Timeout định kỳ và các ca biên.

    Xác minh phát hiện TIMEOUT an toàn, không treo hệ thống, phân biệt với UNSAT,
    chặn đúng các ca stress tổ hợp và bảo đảm cô lập trạng thái khi tái sử dụng.
    """

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_instant_timeout_nonpositive_values(self) -> None:
        """Timeout <= 0 (0, số âm) trả về TIMEOUT ngay mà không tìm kiếm."""
        for t_val in [0.0, -0.5, -1.0, -1e-9]:
            with self.subTest(timeout=t_val):
                res = self.solver.solve([[1, 2], [-1, 2]], num_vars=2, timeout=t_val)
                self.assertTrue(res.timed_out)
                self.assertFalse(res.sat)
                self.assertIsNone(res.model)
                self.assertGreaterEqual(res.stats.runtime, 0.0)
                self.assertEqual(res.stats.decisions, 0)
                self.assertEqual(res.stats.propagations, 0)
                self.assertEqual(res.stats.backtracks, 0)

    def test_timeout_during_active_branching(self) -> None:
        """Ngắt an toàn khi solver đang tích cực rẽ nhánh và quay lui."""
        # PHP 5 chim 4 chuồng: vô nghiệm và buộc rẽ nhánh
        clauses = (
            [[p * 4 + h for h in range(1, 5)] for p in range(5)]
            + [[-(p1 * 4 + h), -(p2 * 4 + h)]
               for h in range(1, 5) for p1 in range(5) for p2 in range(p1 + 1, 5)]
        )
        res = self.solver.solve(clauses, num_vars=20, timeout=0.005)

        self.assertTrue(res.timed_out)
        self.assertFalse(res.sat)
        self.assertIsNone(res.model)
        self.assertGreater(res.stats.runtime, 0.0)
        self.assertGreater(res.stats.decisions, 0)

    def test_strict_discrimination_timeout_vs_unsat(self) -> None:
        """Phân biệt tuyệt đối giữa vô nghiệm (UNSAT) và hết giờ (TIMEOUT)."""
        res_unsat = self.solver.solve([[1], [-1]], num_vars=1, timeout=1.0)
        res_timeout = self.solver.solve([[1, 2]], num_vars=2, timeout=0.0)

        self.assertFalse(res_unsat.timed_out)
        self.assertTrue(res_timeout.timed_out)
        self.assertFalse(res_unsat.sat)
        self.assertFalse(res_timeout.sat)
        self.assertNotEqual(res_unsat.timed_out, res_timeout.timed_out)

    def test_solver_clean_reuse_after_timeout(self) -> None:
        """Sau khi bị ngắt bởi timeout, solver vẫn dùng lại bình thường và sạch state."""
        res_timeout = self.solver.solve([[1, 2]], num_vars=2, timeout=0.0)
        self.assertTrue(res_timeout.timed_out)

        res_next = self.solver.solve([[1, 2], [-1, 2]], num_vars=2, timeout=1.0)
        self.assertFalse(res_next.timed_out)
        self.assertTrue(res_next.sat)
        self.assertIsNotNone(res_next.model)
        assert res_next.model is not None
        self.assertTrue(res_next.model[2])

    def test_infinite_assumptions_generator_interrupted(self) -> None:
        """Dừng an toàn trước chuỗi assumptions sinh liên tục từ generator vô hạn."""
        def _infinite_stream():
            while True:
                yield 1

        res = self.solver.solve(
            [[1]], num_vars=1, assumptions=_infinite_stream(), timeout=0.005
        )
        self.assertTrue(res.timed_out)
        self.assertFalse(res.sat)
        self.assertIsNone(res.model)
        self.assertGreater(res.stats.runtime, 0.0)

    def test_periodic_polling_batch_runtime_positive(self) -> None:
        """Cơ chế kiểm tra deadline định kỳ đảm bảo runtime dương."""
        large_clauses = [[1]] + [[-i, i + 1] for i in range(1, 8000)]
        res = self.solver.solve(large_clauses, num_vars=8001, timeout=1e-5)

        self.assertTrue(res.timed_out)
        self.assertFalse(res.sat)
        self.assertGreater(res.stats.runtime, 0.0)


class TestDPLLPhase3Entailment(unittest.TestCase):
    """Kiểm thử suy diễn logic và ví dụ mẫu trong đề bài.

    Ví dụ: KB = (A ∨ B) ∧ (¬A ∨ B), chứng minh B là Criminal qua phản chứng KB ∧ ¬B UNSAT,
    xác nhận A là UNKNOWN qua 2 truy vấn SAT, và kiểm tra không phát sinh rẽ nhánh.
    """

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_spec_kb_proves_criminal_without_branching(self) -> None:
        """KB ∧ ¬B vô nghiệm chứng minh B Criminal; hoàn tất bằng unit propagate."""
        # A = 1, B = 2
        kb = [[1, 2], [-1, 2]]

        # Giả định B = Innocent (¬B, literal -2)
        res_refutation = self.solver.solve(kb, num_vars=2, assumptions=[-2])
        self.assertFalse(res_refutation.sat)
        self.assertIsNone(res_refutation.model)
        self.assertFalse(res_refutation.timed_out)

        # Suy diễn phản chứng hoàn tất mà không cần rẽ nhánh hay quay lui
        self.assertEqual(res_refutation.stats.decisions, 0)
        self.assertEqual(res_refutation.stats.backtracks, 0)

        # Ngược lại KB ∧ B thỏa mãn
        res_b = self.solver.solve(kb, num_vars=2, assumptions=[2])
        self.assertTrue(res_b.sat)
        self.assertIsNotNone(res_b.model)
        assert res_b.model is not None
        self.assertTrue(res_b.model[2])

    def test_spec_kb_classifies_a_as_unknown(self) -> None:
        """Cả KB ∧ A và KB ∧ ¬A đều thỏa mãn nên A là UNKNOWN."""
        kb = [[1, 2], [-1, 2]]

        # Thử A = Criminal (literal 1) -> SAT với B = True
        res_pos = self.solver.solve(kb, num_vars=2, assumptions=[1])
        self.assertTrue(res_pos.sat)
        self.assertIsNotNone(res_pos.model)
        assert res_pos.model is not None
        self.assertTrue(res_pos.model[1])
        self.assertTrue(res_pos.model[2])

        # Thử A = Innocent (literal -1) -> SAT với B = True
        res_neg = self.solver.solve(kb, num_vars=2, assumptions=[-1])
        self.assertTrue(res_neg.sat)
        self.assertIsNotNone(res_neg.model)
        assert res_neg.model is not None
        self.assertFalse(res_neg.model[1])
        self.assertTrue(res_neg.model[2])

    def test_refutation_proves_innocent_without_branching(self) -> None:
        """Chứng minh Innocent qua phản chứng KB ∧ C_i UNSAT với decisions=0."""
        # KB = (A ∨ ¬B) ∧ (¬A ∨ ¬B) với A = 1, B = 2
        kb_innocent = [[1, -2], [-1, -2]]

        # Giả định B = Criminal (literal 2) -> mâu thuẫn trực tiếp qua unit propagate
        res_criminal = self.solver.solve(kb_innocent, num_vars=2, assumptions=[2])
        self.assertFalse(res_criminal.sat)
        self.assertIsNone(res_criminal.model)
        self.assertFalse(res_criminal.timed_out)
        self.assertEqual(res_criminal.stats.decisions, 0)
        self.assertEqual(res_criminal.stats.backtracks, 0)

        # Giả định B = Innocent (literal -2) -> SAT
        res_innocent = self.solver.solve(kb_innocent, num_vars=2, assumptions=[-2])
        self.assertTrue(res_innocent.sat)
        self.assertIsNotNone(res_innocent.model)
        assert res_innocent.model is not None
        self.assertFalse(res_innocent.model[2])

    def test_inconsistent_kb_detected_without_branching(self) -> None:
        """KB mâu thuẫn [[1], [-1]] trả về UNSAT với decisions=0, backtracks=0."""
        res = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertFalse(res.sat)
        self.assertIsNone(res.model)
        self.assertFalse(res.timed_out)
        self.assertEqual(res.stats.decisions, 0)
        self.assertEqual(res.stats.backtracks, 0)

    def test_all_models_of_spec_kb_force_criminal_b(self) -> None:
        """Toàn bộ model của KB đều có B=True; không tồn tại model nào có B=False."""
        kb = [[1, 2], [-1, 2]]

        # Model 1
        res1 = self.solver.solve(kb, num_vars=2)
        self.assertTrue(res1.sat)
        self.assertIsNotNone(res1.model)
        assert res1.model is not None
        self.assertTrue(res1.model[2])

        # Chặn model 1 để tìm model 2
        block1 = [-1 if res1.model[1] else 1, -2]
        res2 = self.solver.solve(kb + [block1], num_vars=2)
        self.assertTrue(res2.sat)
        self.assertIsNotNone(res2.model)
        assert res2.model is not None
        self.assertTrue(res2.model[2])
        self.assertNotEqual(res1.model[1], res2.model[1])

        # Chặn cả 2 model -> không còn model nào khác (UNSAT)
        block2 = [-1 if res2.model[1] else 1, -2]
        res3 = self.solver.solve(kb + [block1, block2], num_vars=2)
        self.assertFalse(res3.sat)
        self.assertIsNone(res3.model)


class TestDPLLPhase4BruteForceComparison(unittest.TestCase):
    """Kiểm chứng chéo toàn diện giữa DPLL và Brute Force.

    Tập trung vào tính đúng đắn:
    1. So sánh 1:1 trên 300 công thức ngẫu nhiên có seed cố định (1..7 biến, 0..25 mệnh đề).
    2. Kiểm chứng nghiệm model thỏa mãn 100% mệnh đề khi SAT.
    3. Thử nghiệm tích hợp nhỏ với các mẫu CNF sinh từ clue cơ bản (FACT, SAME, DIFFERENT).
    4. Xác minh sự trùng khớp khi công thức có nghiệm duy nhất.
    """

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_random_cnf_cross_validation_300(self) -> None:
        """Đối chiếu DPLL với Brute Force trên 300 CNF ngẫu nhiên (seed cố định)."""
        import itertools
        import random

        rng = random.Random(2026)
        for idx in range(300):
            n = rng.randint(1, 7)
            m = rng.randint(0, 25)
            clauses = [
                [rng.choice([-1, 1]) * rng.randint(1, n) for _ in range(rng.randint(1, 3))]
                for _ in range(m)
            ]

            def _sat_under(assignment: Tuple[bool, ...]) -> bool:
                return all(
                    any(assignment[abs(lit) - 1] == (lit > 0) for lit in clause)
                    for clause in clauses
                )

            expected_sat = any(
                _sat_under(a) for a in itertools.product([False, True], repeat=n)
            )
            res = self.solver.solve(clauses, num_vars=n)

            self.assertEqual(
                res.sat,
                expected_sat,
                f"Lệch kết quả tại test #{idx} với n={n}, clauses={clauses}",
            )

            # Nếu SAT, model phải đầy đủ và thỏa mãn tất cả mệnh đề
            if res.sat:
                self.assertIsNotNone(res.model)
                assert res.model is not None
                self.assertEqual(set(res.model.keys()), set(range(1, n + 1)))
                self.assertTrue(
                    all(self.solver.is_clause_satisfied(c, res.model) for c in clauses)
                )

    def test_basic_clue_cnf_patterns_against_brute_force(self) -> None:
        """Kiểm chứng tích hợp mẫu CNF cơ bản (FACT, SAME, DIFFERENT) với Brute Force."""
        import itertools

        # 4 biến tương ứng lưới 2x2: FACT(1), SAME(1, 2), DIFFERENT(2, 3)
        clauses = [[1], [-1, 2], [1, -2], [2, 3], [-2, -3]]
        n = 4

        def _sat_under(a: Tuple[bool, ...]) -> bool:
            return all(any(a[abs(lit) - 1] == (lit > 0) for lit in c) for c in clauses)

        bf_models = [a for a in itertools.product([False, True], repeat=n) if _sat_under(a)]
        self.assertEqual(len(bf_models), 2)

        res = self.solver.solve(clauses, num_vars=n)
        self.assertTrue(res.sat)
        self.assertIsNotNone(res.model)
        assert res.model is not None

        # Model tìm được bởi DPLL phải nằm trong danh sách nghiệm vét cạn
        model_tuple = tuple(res.model[i] for i in range(1, n + 1))
        self.assertIn(model_tuple, bf_models)

    def test_unique_solution_matches_brute_force(self) -> None:
        """Khi công thức có đúng 1 nghiệm theo Brute Force, DPLL tìm ra đúng nghiệm đó."""
        # Ràng buộc cố định cả 4 biến: 1=True, 2=False, 3=True, 4=False
        clauses = [[1], [-2], [3], [-4]]
        res = self.solver.solve(clauses, num_vars=4)

        self.assertTrue(res.sat)
        self.assertEqual(res.model, {1: True, 2: False, 3: True, 4: False})


if __name__ == "__main__":
    unittest.main()
