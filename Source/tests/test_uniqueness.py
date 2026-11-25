"""Kiểm thử E4: duy nhất trên biến primary, timeout và đối chiếu semantic độc lập."""

import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.constants import CRIMINAL, INNOCENT
from logic.agent import uniqueness_check
from logic.cnf_encoder import Encoder, KB
from logic.dpll import DPLLSolver, SolveResult, SolverStats
from tools.brute_force import count_solutions

DATA = Path(__file__).resolve().parents[1] / "data"


def fact(cell: str, value: bool) -> Clue:
    """Tạo FACT từ trạng thái công khai được caller chọn."""
    return clue_from_dict(cell, {"type": "FACT", "target": cell,
                                 "status": CRIMINAL if value else INNOCENT})


def fixed_board(n: int) -> list[Clue]:
    """Ràng buộc từng ô, có cả Criminal và Innocent."""
    return [fact(cell, index % 2 == 0) for index, cell in enumerate(board.all_cells(n))]


def puzzle_constraints(path: Path, *, include_initial: bool) -> tuple[list[Clue], int]:
    """Lấy tập clue; chỉ thêm các nhãn face-up khi được yêu cầu rõ ràng."""
    data = json.loads(path.read_text(encoding="utf-8"))
    clues = [clue_from_dict(c["cell"], c["clue"]) for c in data["characters"]]
    if include_initial:
        clues += [fact(c["cell"], c["criminal"]) for c in data["characters"]
                  if c["cell"] in data["initially_revealed"]]
    return clues, data["n"]


def result(sat: bool, model: dict[int, bool] | None = None,
           *, timed_out: bool = False) -> SolveResult:
    """Kết quả solver giả cho các trường hợp timeout và model lỗi."""
    return SolveResult(sat, model, SolverStats(), timed_out)


class UniquenessResultTests(unittest.TestCase):
    """Phân biệt vô nghiệm, duy nhất và ít nhất hai nghiệm."""

    def test_empty_clue_set_has_multiple_assignments_including_5x5(self) -> None:
        for n in (1, 3, 4, 5):
            with self.subTest(n=n):
                self.assertEqual(uniqueness_check([], n), (False, 2))

    def test_contradictory_facts_are_unsat(self) -> None:
        self.assertEqual(uniqueness_check([fact("A1", True), fact("A1", False)], 3),
                         (False, 0))

    def test_all_primary_cells_fixed_is_unique(self) -> None:
        for n in (1, 3, 4, 5):
            with self.subTest(n=n):
                self.assertEqual(uniqueness_check(fixed_board(n), n), (True, 1))

    def test_one_free_primary_cell_means_two_models(self) -> None:
        self.assertEqual(uniqueness_check(fixed_board(3)[:-1], 3), (False, 2))

    def test_count_is_capped_at_two_not_an_exhaustive_count(self) -> None:
        clues = [fact("A1", True)]
        self.assertEqual(count_solutions(clues, 3).satisfying_assignments, 256)
        self.assertEqual(uniqueness_check(clues, 3), (False, 2))

    def test_input_clues_and_nested_params_remain_unchanged(self) -> None:
        clue = clue_from_dict("A1", {"type": "EXACTLY",
                                    "region": {"type": "list", "cells": ["B1", "A1"]}, "k": 1})
        clues = [clue, fact("B1", True)]
        before = deepcopy([asdict(c) for c in clues])
        uniqueness_check(clues, 3)
        self.assertEqual([asdict(c) for c in clues], before)

    def test_generator_of_clues_is_supported(self) -> None:
        self.assertEqual(uniqueness_check((c for c in fixed_board(3)), 3), (True, 1))

    def test_repeated_calls_do_not_reuse_blocking_clauses(self) -> None:
        for clues, expected in ((fixed_board(3), (True, 1)), ([], (False, 2)),
                                 (fixed_board(3), (True, 1))):
            self.assertEqual(uniqueness_check(clues, 3), expected)

    def test_initial_statuses_are_explicit_constraints_not_hidden_inputs(self) -> None:
        clues = fixed_board(3)[2:]
        clues.append(clue_from_dict("A1", {
            "type": "EXACTLY", "region": {"type": "list", "cells": ["A1", "B1"]}, "k": 1}))
        self.assertEqual(uniqueness_check(clues, 3), (False, 2))
        self.assertEqual(uniqueness_check(clues + [fact("A1", True)], 3), (True, 1))


class BlockingAndSolverContractTests(unittest.TestCase):
    """Blocking clause chỉ chứa biến của ô, dù biến phụ có nhiều cách gán."""

    def test_free_auxiliary_variables_do_not_count_as_new_puzzle_models(self) -> None:
        encoded = KB([[v] for v in range(1, 10)], num_primary=9, num_aux=2)
        before = deepcopy(encoded.clauses)
        with patch.object(Encoder, "build_kb", return_value=encoded):
            self.assertEqual(uniqueness_check([], 3), (True, 1))
        self.assertEqual(encoded.clauses, before)

    def test_blocking_signs_primary_range_and_num_vars(self) -> None:
        encoded = KB([[-v if v % 2 else v] for v in range(1, 10)],
                     num_primary=9, num_aux=2)
        before = deepcopy(encoded.clauses)
        model = {v: v % 2 == 0 for v in range(1, 12)}
        with patch.object(Encoder, "build_kb", return_value=encoded), \
                patch.object(DPLLSolver, "solve",
                             side_effect=[result(True, model), result(False)]) as solve:
            self.assertEqual(uniqueness_check([], 3, timeout=0.5), (True, 1))
        first, second = solve.call_args_list
        self.assertEqual(first.args, (before, 11))
        expected = [-v if model[v] else v for v in range(1, 10)]
        self.assertEqual(second.args, (before + [expected], 11))
        self.assertEqual(first.kwargs["timeout"], 0.5)
        self.assertEqual(second.kwargs["timeout"], 0.5)
        self.assertEqual(encoded.clauses, before)

    def test_unsat_stops_after_first_query(self) -> None:
        with patch.object(DPLLSolver, "solve", return_value=result(False)) as solve:
            self.assertEqual(uniqueness_check([], 3), (False, 0))
        self.assertEqual(solve.call_count, 1)

    def test_two_sat_results_stop_after_two_queries(self) -> None:
        model = dict.fromkeys(range(1, 10), False)
        second_model = {**model, 9: True}
        with patch.object(DPLLSolver, "solve",
                          side_effect=[result(True, model), result(True, second_model)]) as solve:
            self.assertEqual(uniqueness_check([], 3), (False, 2))
        self.assertEqual(solve.call_count, 2)

    def test_invalid_primary_model_raises_instead_of_claiming_uniqueness(self) -> None:
        for model in (None, {}, {1: True}, {**dict.fromkeys(range(1, 10), False), 9: 0}):
            with self.subTest(model=model), \
                    patch.object(DPLLSolver, "solve", return_value=result(True, model)):
                with self.assertRaises(RuntimeError):
                    uniqueness_check([], 3)

    def test_solver_error_propagates(self) -> None:
        with patch.object(DPLLSolver, "solve", side_effect=RuntimeError("solver bug")):
            with self.assertRaisesRegex(RuntimeError, "solver bug"):
                uniqueness_check([], 3)


class TimeoutAndValidationTests(unittest.TestCase):
    """Timeout và dữ liệu sai không được biến thành kết quả logic."""

    def test_timeout_in_first_or_second_query_raises(self) -> None:
        model = dict.fromkeys(range(1, 10), False)
        for phase in (0, 1):
            outcomes = ([result(True, model)] if phase else []) + [
                result(False, timed_out=True)]
            with self.subTest(phase=phase), \
                    patch.object(DPLLSolver, "solve", side_effect=outcomes) as solve:
                with self.assertRaises(TimeoutError):
                    uniqueness_check([], 3)
                self.assertEqual(solve.call_count, phase + 1)

    def test_timeout_flag_has_priority_even_when_sat_true(self) -> None:
        with patch.object(DPLLSolver, "solve", return_value=result(True, timed_out=True)):
            with self.assertRaises(TimeoutError):
                uniqueness_check([], 3)

    def test_real_solver_zero_timeout_raises(self) -> None:
        with self.assertRaises(TimeoutError):
            uniqueness_check([], 3, timeout=0)

    def test_invalid_sizes_fail_before_solver(self) -> None:
        with patch.object(DPLLSolver, "solve") as solve:
            for n in (None, True, 0, -1, 11, 3.0, "3"):
                with self.subTest(n=n), self.assertRaises(ValueError):
                    uniqueness_check([], n)
            solve.assert_not_called()

    def test_invalid_clue_input_fails_before_solver(self) -> None:
        invalid = (None, "FACT", {}, [None], [{"type": "FACT"}],
                   [Clue("bad", "A1", "FACT", [])],
                   [clue_from_dict("A1", {"type": "UNSUPPORTED"})],
                   [clue_from_dict("A1", {"type": "FACT", "target": "Z9", "status": CRIMINAL})])
        with patch.object(DPLLSolver, "solve") as solve:
            for clues in invalid:
                with self.subTest(clues=clues), self.assertRaises(ValueError):
                    uniqueness_check(clues, 3)
            solve.assert_not_called()

    def test_bad_timeout_from_solver_is_not_a_uniqueness_result(self) -> None:
        for timeout in (True, "1", float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises((TypeError, ValueError)):
                uniqueness_check([], 3, timeout=timeout)


class RealEncoderIntegrationTests(unittest.TestCase):
    """Oracle semantic B2 độc lập và dữ liệu repo thật, không dùng nhãn ẩn để lọc."""

    def test_all_eight_clue_types_match_semantic_brute_force(self) -> None:
        prefix = fixed_board(3)[1:]
        region = {"type": "list", "cells": ["A1", "B1", "C1"]}
        fixtures = [
            [fact("A1", True)],
            [clue_from_dict("A1", {"type": "SAME_STATUS", "cell1": "A1", "cell2": "B1"})],
            [clue_from_dict("A1", {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "B1"})],
            [clue_from_dict("A1", {"type": kind, "region": region, "k": 1})
             for kind in ("EXACTLY", "AT_LEAST", "AT_MOST")],
            [clue_from_dict("A1", {"type": "PARITY", "region": region, "parity": "ODD"})],
            [clue_from_dict("A1", {"type": "COMPARE",
                                  "region1": {"type": "list", "cells": ["A1"]},
                                  "region2": {"type": "list", "cells": ["B1"]}, "op": "GT"})],
            [fact("A1", True), fact("A1", False)],
        ]
        for i, constraints in enumerate(fixtures):
            clues = prefix + constraints
            models = count_solutions(clues, 3).satisfying_assignments
            with self.subTest(fixture=i):
                self.assertEqual(uniqueness_check(clues, 3), (models == 1, min(models, 2)))

    def test_all_3x3_and_4x4_puzzles_match_brute_force(self) -> None:
        for n in (3, 4):
            for path in sorted((DATA / f"puzzles_{n}x{n}").glob("*.json")):
                for include_initial in (False, True):
                    clues, size = puzzle_constraints(path, include_initial=include_initial)
                    models = count_solutions(clues, size).satisfying_assignments
                    with self.subTest(n=n, file=path.name, initial=include_initial):
                        self.assertEqual(uniqueness_check(clues, size, timeout=10),
                                         (models == 1, min(models, 2)))

    def test_all_5x5_puzzles_with_initial_facts_are_unique(self) -> None:
        for path in sorted((DATA / "puzzles_5x5").glob("*.json")):
            clues, n = puzzle_constraints(path, include_initial=True)
            with self.subTest(puzzle=path.name):
                self.assertEqual(uniqueness_check(clues, n, timeout=10), (True, 1))


if __name__ == "__main__":
    unittest.main()
