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
    """Kiểm thử thuật toán DPLL: chọn biến deterministic, branching và backtracking (Task D2)."""

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
    """Kiểm thử DPLL với assumptions và trả kết quả SAT/UNSAT kèm model (Task D3)."""

    def setUp(self) -> None:
        self.solver = DPLLSolver()

    def test_solve_preserves_kb_clauses_and_assumptions(self) -> None:
        """Hàm solve không làm biến đổi danh sách mệnh đề gốc và assumptions."""
        clauses = [[1, 2], [-1, 2], [-2, 3]]
        copy_clauses = [list(c) for c in clauses]
        clause_ids = [id(c) for c in clauses]

        assumptions = [-2]
        copy_assumptions = list(assumptions)

        res = self.solver.solve(clauses, num_vars=3, assumptions=assumptions)
        self.assertEqual(clauses, copy_clauses)
        self.assertEqual([id(c) for c in clauses], clause_ids)
        self.assertEqual(assumptions, copy_assumptions)

        # Kiểm tra tính bất biến khi có rẽ nhánh và quay lui
        branching_clauses = [[1, 2, 3], [-1, 2], [-2, -3]]
        copy_bc = [list(c) for c in branching_clauses]
        bc_ids = [id(c) for c in branching_clauses]

        self.solver.solve(branching_clauses, num_vars=3, assumptions=[-3])
        self.assertEqual(branching_clauses, copy_bc)
        self.assertEqual([id(c) for c in branching_clauses], bc_ids)

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
        """Khi UNSAT, cờ sat là False và model bắt buộc là None."""
        # 1. Công thức vô nghiệm ngay từ clauses gốc
        res_conflict = self.solver.solve([[1], [-1]], num_vars=1)
        self.assertFalse(res_conflict.sat)
        self.assertIsNone(res_conflict.model)

        # 2. Assumptions tự mâu thuẫn trực tiếp
        res_assump_conflict = self.solver.solve([[1, 2]], num_vars=2, assumptions=[1, -1])
        self.assertFalse(res_assump_conflict.sat)
        self.assertIsNone(res_assump_conflict.model)

        # 3. Assumption xung đột với unit clause
        res_unit_conflict = self.solver.solve([[1]], num_vars=2, assumptions=[-1])
        self.assertFalse(res_unit_conflict.sat)
        self.assertIsNone(res_unit_conflict.model)

        # 4. Assumption dẫn tới mâu thuẫn qua nhiều bước suy diễn
        clauses = [[1, 2], [-1, 2]]
        res_deduced_conflict = self.solver.solve(clauses, num_vars=2, assumptions=[-2])
        self.assertFalse(res_deduced_conflict.sat)
        self.assertIsNone(res_deduced_conflict.model)

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

        res4 = self.solver.solve(clauses, num_vars=2, assumptions=[])
        self.assertTrue(res4.sat and res4.model)

    def test_model_enumeration_via_blocking_clauses(self) -> None:
        """Tìm toàn bộ nghiệm thỏa mãn bằng cách thêm blocking clause sau mỗi lần giải."""
        # Công thức (x1 ∨ x2) với num_vars = 2 có 3 model thỏa mãn: (T, F), (F, T), (T, T)
        clauses = [[1, 2]]
        all_clauses = list(clauses)
        models = []

        while True:
            res = self.solver.solve(all_clauses, num_vars=2)
            if not res.sat:
                self.assertIsNone(res.model)
                break
            assert res.model is not None
            models.append(dict(res.model))

            # Chặn model hiện tại: ít nhất một biến phải nhận giá trị ngược lại
            blocking = [-var if val else var for var, val in res.model.items()]
            all_clauses.append(blocking)

        self.assertEqual(len(models), 3)
        # Kiểm tra danh sách ban đầu không bị biến đổi
        self.assertEqual(clauses, [[1, 2]])


if __name__ == "__main__":
    unittest.main()
