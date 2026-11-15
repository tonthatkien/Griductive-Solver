"""B2 tests: explicit evaluator doubles are separate from real D5/D6 integration."""

import ast
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
from itertools import islice
from math import comb
from pathlib import Path
from unittest.mock import patch

from engine import board
from engine.clue import COUNT_TYPES, PAIR_TYPES, Clue, clue_from_dict
from engine.constants import CRIMINAL, INNOCENT
from engine.game_state import GameEngine
from logic import semantic
from tools import brute_force as bf

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"


def make_clue(kind: str = "FACT", **params: object) -> Clue:
    """Create constraints using the project's actual Clue constructor."""
    return clue_from_dict("A1", {"type": kind, **params})


def fact_double(clue: Clue, assignment: dict[str, bool], n: int) -> bool:
    """Test double for FACT ONLY; not a replacement implementation of D5."""
    if clue.type != "FACT":
        raise NotImplementedError(f"Test double does not support {clue.type}")
    return assignment[clue.params["target"]] == (clue.params["status"] == CRIMINAL)


def make_puzzle(n: int = 3) -> dict:
    """Create a valid full puzzle with repeated A1 facts and arbitrary hidden labels."""
    return {
        "n": n,
        "characters": [
            {
                "cell": cell, "name": f"Person {index:02d}", "profession": "Tester",
                "criminal": False,
                "clue": {"type": "FACT", "target": "A1", "status": INNOCENT},
            }
            for index, cell in enumerate(board.all_cells(n))
        ],
        "initially_revealed": ["A1"],
    }


class EnumerationTests(unittest.TestCase):
    """Verify exhaustive Cartesian-product enumeration, including fresh dictionaries."""

    def test_all_assignments_are_complete_distinct_and_boolean(self) -> None:
        for n, expected_count in ((3, 512), (4, 65536)):
            with self.subTest(n=n):
                cells = board.all_cells(n)
                signatures = set()
                for assignment in bf.iter_assignments(n):
                    self.assertEqual(list(assignment), cells)
                    self.assertTrue(all(type(value) is bool for value in assignment.values()))
                    signatures.add(tuple(assignment.values()))
                self.assertEqual(len(signatures), expected_count)

    def test_order_is_deterministic_false_before_true(self) -> None:
        first = list(islice(bf.iter_assignments(3), 3))
        self.assertEqual(first, list(islice(bf.iter_assignments(3), 3)))
        self.assertEqual(list(first[0].values()), [False] * 9)
        self.assertEqual(list(first[1].values()), [False] * 8 + [True])
        self.assertEqual(list(first[2].values()), [False] * 7 + [True, False])
        first[0]["A1"] = True
        self.assertFalse(first[1]["A1"])

    def test_unsupported_and_noninteger_sizes_fail(self) -> None:
        for n in (0, -1, 1, 2, 5, True, 3.0, "3", None):
            with self.subTest(n=n), self.assertRaises(ValueError):
                bf.iter_assignments(n)


class CountingWithDoubleTests(unittest.TestCase):
    """Exercise search mechanics using controlled predicates, not the real evaluator."""

    def test_empty_constraint_set_counts_all_models(self) -> None:
        for n, expected in ((3, 512), (4, 65536)):
            with self.subTest(n=n), patch.object(bf, "evaluate") as evaluator:
                result = bf.count_solutions([], n)
                self.assertEqual(result.assignments_checked, expected)
                self.assertEqual(result.satisfying_assignments, expected)
                self.assertEqual(result.status, bf.MULTIPLE)
                self.assertTrue(result.exhaustive)
                self.assertTrue(result.count_is_exact)
                self.assertIsNone(result.unique_solution)
                self.assertGreaterEqual(result.runtime, 0)
                evaluator.assert_not_called()

    def test_contradictory_facts_are_unsat(self) -> None:
        clues = [make_clue(target="A1", status=status) for status in (CRIMINAL, INNOCENT)]
        with patch.object(bf, "evaluate", side_effect=fact_double):
            result = bf.count_solutions(clues, 3, stop_after_two=True)
        self.assertEqual((result.status, result.satisfying_assignments), (bf.UNSAT, 0))
        self.assertEqual(result.assignments_checked, 512)
        self.assertTrue(result.exhaustive)
        self.assertIsNone(result.unique_solution)

    def test_unique_solution_requires_full_search_in_both_modes(self) -> None:
        expected = {cell: index % 2 == 0 for index, cell in enumerate(board.all_cells(3))}
        clues = [make_clue(target=c, status=CRIMINAL if v else INNOCENT)
                 for c, v in expected.items()]
        for early in (False, True):
            with self.subTest(early=early), patch.object(bf, "evaluate", side_effect=fact_double):
                result = bf.count_solutions(iter(clues), 3, stop_after_two=early)
            self.assertEqual((result.status, result.satisfying_assignments), (bf.UNIQUE, 1))
            self.assertEqual(result.unique_solution, expected)
            self.assertEqual(result.assignments_checked, 512)
            self.assertTrue(result.exhaustive)

    def test_one_fact_leaves_256_models(self) -> None:
        with patch.object(bf, "evaluate", side_effect=fact_double):
            result = bf.count_solutions([make_clue(target="A1", status=CRIMINAL)], 3)
        self.assertEqual(result.satisfying_assignments, 256)
        self.assertIsNone(result.unique_solution)

    def test_early_stop_is_a_lower_bound(self) -> None:
        result = bf.count_solutions([], 4, stop_after_two=True)
        self.assertEqual(result.satisfying_assignments, 2)
        self.assertEqual(result.assignments_checked, 2)
        self.assertEqual(result.status, bf.MULTIPLE)
        self.assertFalse(result.exhaustive)
        self.assertFalse(result.count_is_exact)
        self.assertIsNone(result.unique_solution)

    def test_second_model_on_last_assignment_is_exact(self) -> None:
        # The first eight cells are fixed, so only the last two assignments satisfy.
        known = {cell: True for cell in board.all_cells(3)[:-1]}
        result = bf.count_solutions([], 3, known_statuses=known, stop_after_two=True)
        self.assertEqual(result.satisfying_assignments, 2)
        self.assertEqual(result.assignments_checked, 512)
        self.assertTrue(result.count_is_exact)

    def test_known_statuses_can_define_a_public_subset(self) -> None:
        result = bf.count_solutions([], 3, known_statuses={"B2": False})
        self.assertEqual(result.satisfying_assignments, 256)
        self.assertEqual(result.assignments_checked, 512)

    def test_every_evaluator_call_receives_complete_boolean_assignment(self) -> None:
        seen = []

        def predicate(clue: Clue, assignment: dict[str, bool], n: int) -> bool:
            bf.validate_assignment(assignment, n)
            self.assertIsInstance(clue, Clue)
            seen.append(tuple(assignment.values()))
            return True

        with patch.object(bf, "evaluate", side_effect=predicate):
            result = bf.count_solutions([make_clue(target="A1", status=CRIMINAL)], 3)
        self.assertEqual(len(set(seen)), 512)
        self.assertEqual(result.satisfying_assignments, 512)

    def test_errors_are_not_converted_to_unsat(self) -> None:
        for error in (NotImplementedError("D5"), ValueError("bad input"), RuntimeError("bug")):
            with self.subTest(error=error), patch.object(bf, "evaluate", side_effect=error):
                with self.assertRaises(type(error)):
                    bf.count_solutions([make_clue(target="A1", status=CRIMINAL)], 3)

    def test_unsupported_evaluator_clue_not_hidden_after_false_clue(self) -> None:
        clues = [make_clue(target="A1", status=CRIMINAL),
                 make_clue("PARITY", region={"type": "row", "number": 1}, parity="EVEN")]
        with patch.object(bf, "evaluate", side_effect=fact_double):
            with self.assertRaises(NotImplementedError):
                bf.count_solutions(clues, 3)

    def test_nonboolean_evaluator_results_fail(self) -> None:
        for value in (None, 0, 1, "False", [], {}):
            with self.subTest(value=value), patch.object(bf, "evaluate", return_value=value):
                with self.assertRaises(TypeError):
                    bf.count_solutions([make_clue(target="A1", status=CRIMINAL)], 3)

    def test_default_counting_status_is_added_without_mutating_clue(self) -> None:
        clue = make_clue("EXACTLY", region={"type": "row", "number": 1}, k=0)
        before = deepcopy(clue.params)
        with patch.object(bf, "evaluate", return_value=True) as evaluator:
            bf.count_solutions([clue], 3, stop_after_two=True)
        self.assertEqual(evaluator.call_args.args[0].params["status"], CRIMINAL)
        self.assertEqual(clue.params, before)


class PuzzleWithDoubleTests(unittest.TestCase):
    """Verify full-puzzle scope and separation of hidden labels from public facts."""

    def test_hidden_labels_do_not_constrain_and_input_is_unchanged(self) -> None:
        puzzle = make_puzzle()
        before = deepcopy(puzzle)
        with patch.object(bf, "evaluate", side_effect=fact_double):
            first = bf.check_puzzle(puzzle)
            self.assertEqual(puzzle, before)
            for character in puzzle["characters"][1:]:
                character["criminal"] = True
            second = bf.check_puzzle(puzzle)
        self.assertEqual(first.satisfying_assignments, 256)
        self.assertEqual(second.satisfying_assignments, first.satisfying_assignments)
        self.assertEqual(first.status, bf.MULTIPLE)

    def test_initial_face_up_status_is_a_constraint(self) -> None:
        puzzle = make_puzzle()
        puzzle["characters"][0]["criminal"] = True
        with patch.object(bf, "evaluate", side_effect=fact_double):
            result = bf.check_puzzle(puzzle)
        self.assertEqual(result.status, bf.UNSAT)

    def test_face_down_clue_is_included_in_full_puzzle_check(self) -> None:
        puzzle = make_puzzle()
        puzzle["characters"][-1]["clue"]["status"] = CRIMINAL
        with patch.object(bf, "evaluate", side_effect=fact_double):
            self.assertEqual(bf.check_puzzle(puzzle).status, bf.UNSAT)

    def test_character_array_order_does_not_change_cell_order(self) -> None:
        puzzle = make_puzzle()
        puzzle["characters"].reverse()
        with patch.object(bf, "evaluate", side_effect=fact_double):
            self.assertEqual(bf.check_puzzle(puzzle).satisfying_assignments, 256)


class InputValidationTests(unittest.TestCase):
    """Invalid schemas fail before the evaluator is called."""

    def test_mixed_case_names_follow_engine_alphabetical_order(self) -> None:
        puzzle = make_puzzle()
        names = ["alice", "Bob", "charlie", "Dave", "eve", "Frank", "grace", "Heidi", "ivan"]
        for character, name in zip(puzzle["characters"], names):
            character["name"] = name
        GameEngine().load_puzzle(puzzle)
        self.assertEqual(bf.check_puzzle(puzzle).satisfying_assignments, 256)

    def test_duplicate_names_are_rejected_like_engine(self) -> None:
        for name in ("Person 00", "person 00"):
            puzzle = make_puzzle()
            puzzle["characters"][1]["name"] = name
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    GameEngine().load_puzzle(puzzle)
                with self.assertRaises(ValueError):
                    bf.check_puzzle(puzzle)

    def test_invalid_puzzles_fail_before_evaluation(self) -> None:
        invalid = [None, [], {}, {"n": 5}, {"n": True}]
        mutations = [
            lambda p: p["characters"].pop(),
            lambda p: p["characters"][1].update(cell="A1"),
            lambda p: p["characters"][1].update(cell="D1"),
            lambda p: p["characters"][1].update(cell="a1"),
            lambda p: p["characters"][1].update(cell=[]),
            lambda p: p["characters"][1].pop("clue"),
            lambda p: p["characters"][1].update(clue={}),
            lambda p: p["characters"][1].update(clue="FACT"),
            lambda p: p["characters"][1].pop("criminal"),
            lambda p: p["characters"][1].update(criminal=0),
            lambda p: p["characters"][1].update(criminal="false"),
            lambda p: p["characters"][1].update(name=""),
            lambda p: p["characters"][1].update(name="AAA"),
            lambda p: p["characters"][1].pop("profession"),
            lambda p: p.pop("initially_revealed"),
            lambda p: p.update(initially_revealed=[]),
            lambda p: p.update(initially_revealed=["A1", "A1"]),
            lambda p: p.update(initially_revealed=["D1"]),
            lambda p: p.update(initially_revealed=[[]]),
        ]
        for mutate in mutations:
            puzzle = make_puzzle()
            mutate(puzzle)
            invalid.append(puzzle)
        with patch.object(bf, "evaluate") as evaluator:
            for puzzle in invalid:
                with self.subTest(puzzle=puzzle), self.assertRaises(ValueError):
                    bf.check_puzzle(puzzle)
            evaluator.assert_not_called()

    def test_invalid_clues_are_not_unsat(self) -> None:
        invalid = [
            {}, Clue("x", "A1", "FACT", []), make_clue("UNKNOWN"), make_clue([]),
            make_clue("SAME", a="A1", b="B1"),
            make_clue(target="A1"), make_clue(cell="A1", status=CRIMINAL),
            make_clue(target="D1", status=CRIMINAL), make_clue(target="A1", status=True),
            make_clue("SAME_STATUS", cell1="A1", cell2="A1"),
            make_clue("DIFFERENT_STATUS", cell1="A1"),
            make_clue("PARITY", region={"type": "row", "number": 1}, parity="ODDD"),
            make_clue("COMPARE", region1={"type": "row", "number": 1}, op="GT"),
            make_clue("COMPARE", region1={"type": "row", "number": 1},
                      region2={"type": "col", "letter": "A"}, op="NE"),
        ]
        for count in (None, True, 1.0, -1, 4, "1"):
            invalid.append(make_clue("EXACTLY", region={"type": "row", "number": 1}, k=count))
        with patch.object(bf, "evaluate") as evaluator:
            for clue in invalid:
                with self.subTest(clue=clue), self.assertRaises(ValueError):
                    bf.count_solutions([clue], 3)
            evaluator.assert_not_called()

    def test_invalid_regions_fail(self) -> None:
        regions = [
            None, [], {}, {"type": "unknown"}, {"type": "row", "index": 1},
            {"type": "row", "number": True}, {"type": "row", "number": 0},
            {"type": "row", "number": 4}, {"type": "col", "letter": "a"},
            {"type": "col", "letter": "AB"}, {"type": "col", "letter": 1},
            {"type": "col", "letter": "D"}, {"type": "neighbors", "cell": "A01"},
            {"type": "cells", "cells": ["A1"]}, {"type": "list", "cells": []},
            {"type": "list", "cells": "A1"}, {"type": "list", "cells": ["A1", "A1"]},
            {"type": "list", "cells": ["D1"]}, {"type": "list", "cells": [[]]},
        ]
        for region in regions:
            with self.subTest(region=region), self.assertRaises(ValueError):
                bf.count_solutions([make_clue("EXACTLY", region=region, k=0)], 3)

    def test_invalid_assignment_types_and_cells_fail(self) -> None:
        good = dict.fromkeys(board.all_cells(3), False)
        invalid = [None, [], {}, {"A1": False}, {**good, "D1": False}]
        invalid.extend({**good, "A1": value} for value in (0, 1, "False", None))
        for assignment in invalid:
            with self.subTest(assignment=assignment), self.assertRaises(ValueError):
                bf.validate_assignment(assignment, 3)
        bf.validate_assignment(good, 3)

    def test_invalid_known_statuses_fail(self) -> None:
        for known in ([], {"D1": False}, {"A1": 1}, {"A1": "CRIMINAL"}):
            with self.subTest(known=known), self.assertRaises(ValueError):
                bf.count_solutions([], 3, known_statuses=known)

    def test_early_stop_flag_requires_boolean(self) -> None:
        for value in (0, 1, "False", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bf.count_solutions([], 3, stop_after_two=value)


class IndependenceTests(unittest.TestCase):
    """Check source boundaries and actual imported dependencies in a fresh process."""

    def test_no_solver_or_encoder_import_or_call(self) -> None:
        tree = ast.parse(Path(bf.__file__).read_text(encoding="utf-8"))
        forbidden = ("dpll", "cnf_encoder", "pysat", "z3", "sympy")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(any(part in (node.module or "") for part in forbidden))
            elif isinstance(node, ast.Import):
                self.assertFalse(any(part in alias.name
                                     for alias in node.names for part in forbidden))
            elif isinstance(node, ast.Call):
                self.assertFalse(any(part in ast.unparse(node.func) for part in forbidden))

    def test_import_does_not_load_solver_encoder_or_gui(self) -> None:
        code = (
            "import sys; from tools import brute_force; "
            "assert not any(m in sys.modules for m in "
            "['logic.dpll', 'logic.cnf_encoder', 'gui.app'])"
        )
        subprocess.run([sys.executable, "-c", code], check=True,
                       cwd=Path(bf.__file__).resolve().parents[1])


class CommandLineWithDoubleTests(unittest.TestCase):
    """Verify JSON reporting and failure exit codes without pretending D5 is ready."""

    def test_exhaustive_json_report(self) -> None:
        output = StringIO()
        with patch("sys.argv", ["brute_force", "puzzle.json"]), \
                patch.object(Path, "open", return_value=StringIO(json.dumps(make_puzzle()))), \
                patch.object(bf, "evaluate", side_effect=fact_double), redirect_stdout(output):
            bf.main()
        report = json.loads(output.getvalue())
        self.assertEqual(report["satisfying_assignments"], 256)
        self.assertEqual(report["assignments_checked"], 512)
        self.assertTrue(report["count_is_exact"])
        self.assertEqual(report["status"], bf.MULTIPLE)

    def test_early_stop_json_reports_lower_bound(self) -> None:
        output = StringIO()
        with patch("sys.argv", ["brute_force", "puzzle.json", "--stop-after-two"]), \
                patch.object(Path, "open", return_value=StringIO(json.dumps(make_puzzle()))), \
                patch.object(bf, "evaluate", side_effect=fact_double), redirect_stdout(output):
            bf.main()
        report = json.loads(output.getvalue())
        self.assertEqual(report["satisfying_assignments"], 2)
        self.assertFalse(report["count_is_exact"])
        self.assertFalse(report["exhaustive"])

    def test_missing_evaluator_exits_with_error_and_no_result(self) -> None:
        output, errors = StringIO(), StringIO()
        with patch("sys.argv", ["brute_force", "puzzle.json"]), \
                patch.object(Path, "open", return_value=StringIO(json.dumps(make_puzzle()))), \
                patch.object(bf, "evaluate", side_effect=NotImplementedError), \
                redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as caught:
                bf.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("D5/D6", errors.getvalue())

    def test_empty_type_error_is_not_reported_as_missing_dependency(self) -> None:
        errors = StringIO()
        with patch("sys.argv", ["brute_force", "puzzle.json"]), \
                patch.object(Path, "open", return_value=StringIO(json.dumps(make_puzzle()))), \
                patch.object(bf, "evaluate", side_effect=TypeError), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as caught:
                bf.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("TypeError", errors.getvalue())
        self.assertNotIn("D5/D6", errors.getvalue())


class RealSemanticIntegrationTests(unittest.TestCase):
    """Real merged D5/D6 evaluator only; unavailable or broken clues fail, never skip."""

    def assert_count(self, clue: Clue, expected: int) -> None:
        """Compare exhaustive counts against independently derived combinatorial counts."""
        result = bf.count_solutions([clue], 3)
        self.assertEqual(result.satisfying_assignments, expected)
        self.assertEqual(result.assignments_checked, 512)
        self.assertTrue(result.exhaustive)

    def test_fact_both_statuses(self) -> None:
        for status in (CRIMINAL, INNOCENT):
            with self.subTest(status=status):
                self.assert_count(make_clue(target="A1", status=status), 256)

    def test_pair_clues(self) -> None:
        for kind in PAIR_TYPES:
            with self.subTest(kind=kind):
                self.assert_count(make_clue(kind, cell1="A1", cell2="B1"), 256)

    def test_cardinality_boundaries_and_innocent_counts(self) -> None:
        for status in (CRIMINAL, INNOCENT):
            for kind in COUNT_TYPES:
                for k in range(4):
                    count = sum(comb(3, i) for i in range(4)
                                if {"EXACTLY": i == k, "AT_LEAST": i >= k,
                                    "AT_MOST": i <= k}[kind]) * 64
                    with self.subTest(status=status, kind=kind, k=k):
                        self.assert_count(make_clue(kind, region={"type": "row", "number": 1},
                                                   k=k, status=status), count)

    def test_all_region_types_and_default_status(self) -> None:
        regions = [
            ({"type": "row", "number": 2}, 3),
            ({"type": "col", "letter": "B"}, 3),
            ({"type": "neighbors", "cell": "A1"}, 3),
            ({"type": "neighbors", "cell": "B1"}, 5),
            ({"type": "neighbors", "cell": "B2"}, 8),
            ({"type": "list", "cells": ["C3", "A1"]}, 2),
            ({"type": "list", "cells": ["A1"]}, 1),
        ]
        for region, size in regions:
            for k in (0, size):
                with self.subTest(region=region, k=k):
                    self.assert_count(make_clue("EXACTLY", region=region, k=k), 2 ** (9 - size))

    def test_parity_even_odd_including_zero(self) -> None:
        region = {"type": "list", "cells": ["A1", "B1"]}
        for status in (CRIMINAL, INNOCENT):
            for parity in ("EVEN", "ODD"):
                with self.subTest(status=status, parity=parity):
                    self.assert_count(make_clue("PARITY", region=region, parity=parity,
                                               status=status), 256)
        assignment = dict.fromkeys(board.all_cells(3), False)
        self.assertTrue(semantic.evaluate(make_clue("PARITY", region=region, parity="EVEN"),
                                          assignment, 3))
        self.assertFalse(semantic.evaluate(make_clue("PARITY", region=region, parity="ODD"),
                                           assignment, 3))

    def test_compare_all_operators_both_statuses(self) -> None:
        # Two disjoint singleton regions have the four equiprobable Boolean pairs.
        for status in (CRIMINAL, INNOCENT):
            for op, expected in (("GT", 128), ("GE", 384), ("EQ", 256),
                                 ("LE", 384), ("LT", 128)):
                with self.subTest(op=op, status=status):
                    self.assert_count(make_clue("COMPARE", status=status, op=op,
                                               region1={"type": "list", "cells": ["A1"]},
                                               region2={"type": "list", "cells": ["B1"]}),
                                      expected)

    def test_compare_overlapping_regions(self) -> None:
        # Common A1 cancels. Two independent two-cell counts agree in 6/16 cases.
        self.assert_count(make_clue("COMPARE", op="EQ",
                                    region1={"type": "row", "number": 1},
                                    region2={"type": "col", "letter": "A"}), 192)

    def test_direct_truth_values_preserve_polarity_and_operators(self) -> None:
        assignment = {cell: cell in ("A1", "B1") for cell in board.all_cells(3)}
        row = {"type": "row", "number": 1}
        cases = [
            (make_clue(target="A1", status=CRIMINAL), True),
            (make_clue(target="A1", status=INNOCENT), False),
            (make_clue(target="C1", status=INNOCENT), True),
            (make_clue(target="C1", status=CRIMINAL), False),
            (make_clue("EXACTLY", region=row, k=2), True),
            (make_clue("EXACTLY", region=row, k=1), False),
            (make_clue("EXACTLY", region=row, k=1, status=INNOCENT), True),
            (make_clue("EXACTLY", region=row, k=2, status=INNOCENT), False),
            (make_clue("AT_LEAST", region=row, k=2), True),
            (make_clue("AT_LEAST", region=row, k=3), False),
            (make_clue("AT_MOST", region=row, k=2), True),
            (make_clue("AT_MOST", region=row, k=1), False),
            (make_clue("PARITY", region=row, parity="EVEN"), True),
            (make_clue("PARITY", region=row, parity="ODD"), False),
            (make_clue("PARITY", region=row, parity="ODD", status=INNOCENT), True),
        ]
        for clue, expected in cases:
            with self.subTest(clue=clue):
                self.assertIs(semantic.evaluate(clue, assignment, 3), expected)
        for left in (False, True):
            for right in (False, True):
                assignment.update(A1=left, B1=right)
                for kind, expected in (("SAME_STATUS", left == right),
                                       ("DIFFERENT_STATUS", left != right)):
                    clue = make_clue(kind, cell1="A1", cell2="B1")
                    with self.subTest(kind=kind, left=left, right=right):
                        self.assertIs(semantic.evaluate(clue, assignment, 3), expected)
                for status in (CRIMINAL, INNOCENT):
                    a = int(left == (status == CRIMINAL))
                    b = int(right == (status == CRIMINAL))
                    expectations = {"GT": a > b, "GE": a >= b, "EQ": a == b,
                                    "LE": a <= b, "LT": a < b}
                    for op, expected in expectations.items():
                        clue = make_clue("COMPARE", op=op, status=status,
                                         region1={"type": "list", "cells": ["A1"]},
                                         region2={"type": "list", "cells": ["B1"]})
                        with self.subTest(op=op, status=status, left=left, right=right):
                            self.assertIs(semantic.evaluate(clue, assignment, 3), expected)

    def test_real_4x4_count(self) -> None:
        result = bf.count_solutions([make_clue("EXACTLY", region={"type": "row", "number": 1},
                                             k=2)], 4)
        self.assertEqual(result.satisfying_assignments, comb(4, 2) * 2 ** 12)
        self.assertEqual(result.assignments_checked, 65536)

    def test_repository_sample_full_puzzle(self) -> None:
        puzzle = json.loads(SAMPLE.read_text(encoding="utf-8"))
        result = bf.check_puzzle(puzzle)
        # Derived from the clue contract, not copied from hidden labels:
        # A1 face-up; B2 FACT; C2 SAME; C3 col C; A3/B3 row 3;
        # A2 col A; B1 is the third innocent neighboring C2.
        expected = {cell: cell in ("A1", "B2", "C2", "C3") for cell in board.all_cells(3)}
        self.assertEqual(result.status, bf.UNIQUE)
        self.assertEqual(result.satisfying_assignments, 1)
        self.assertEqual(result.unique_solution, expected)
        self.assertEqual(result.assignments_checked, 512)

    def test_full_3x3_and_4x4_puzzles_cover_all_solution_classes(self) -> None:
        for n in (3, 4):
            puzzle = make_puzzle(n)
            with self.subTest(n=n, status=bf.MULTIPLE):
                multiple = bf.check_puzzle(puzzle)
                self.assertEqual(multiple.status, bf.MULTIPLE)
                self.assertEqual(multiple.satisfying_assignments, 2 ** (n * n - 1))
                self.assertEqual(multiple.assignments_checked, 2 ** (n * n))
                self.assertTrue(multiple.count_is_exact)
                self.assertIsNone(multiple.unique_solution)
            puzzle["characters"][-1]["clue"]["status"] = CRIMINAL
            with self.subTest(n=n, status=bf.UNSAT):
                unsat = bf.check_puzzle(puzzle, stop_after_two=True)
                self.assertEqual(unsat.status, bf.UNSAT)
                self.assertEqual(unsat.satisfying_assignments, 0)
                self.assertEqual(unsat.assignments_checked, 2 ** (n * n))
                self.assertTrue(unsat.exhaustive)
            expected = {}
            for index, character in enumerate(puzzle["characters"]):
                criminal = index % 2 == 1
                expected[character["cell"]] = criminal
                character["clue"] = {"type": "FACT", "target": character["cell"],
                                     "status": CRIMINAL if criminal else INNOCENT}
            with self.subTest(n=n, status=bf.UNIQUE):
                unique = bf.check_puzzle(puzzle, stop_after_two=True)
                self.assertEqual(unique.status, bf.UNIQUE)
                self.assertEqual(unique.satisfying_assignments, 1)
                self.assertEqual(unique.unique_solution, expected)
                self.assertEqual(unique.assignments_checked, 2 ** (n * n))
                self.assertTrue(unique.exhaustive)

    def test_public_engine_kb_is_distinct_from_complete_puzzle(self) -> None:
        puzzle = json.loads(SAMPLE.read_text(encoding="utf-8"))
        engine = GameEngine()
        engine.load_puzzle(puzzle)
        public = engine.get_public_kb()
        public_before = deepcopy(public)
        result = bf.count_solutions(public.revealed_clues, public.n,
                                    known_statuses={c: s == CRIMINAL
                                                    for c, s in public.proved.items()})
        # A1 and C1 are face-up; the revealed clues force B2, C2, C3. Four cells are free.
        self.assertEqual(result.satisfying_assignments, 16)
        self.assertEqual(result.status, bf.MULTIPLE)
        self.assertEqual(public.proved, public_before.proved)
        self.assertEqual([c.params for c in public.revealed_clues],
                         [c.params for c in public_before.revealed_clues])
        self.assertEqual(bf.check_puzzle(puzzle).satisfying_assignments, 1)

    def test_real_sample_ignores_hidden_labels_and_preserves_input(self) -> None:
        puzzle = json.loads(SAMPLE.read_text(encoding="utf-8"))
        before = deepcopy(puzzle)
        first = bf.check_puzzle(puzzle)
        self.assertEqual(puzzle, before)
        for character in puzzle["characters"]:
            if character["cell"] not in puzzle["initially_revealed"]:
                character["criminal"] = not character["criminal"]
        altered = deepcopy(puzzle)
        second = bf.check_puzzle(puzzle)
        self.assertEqual(puzzle, altered)
        self.assertEqual(second.unique_solution, first.unique_solution)
        self.assertEqual(second.satisfying_assignments, 1)
        self.assertEqual(second.status, first.status)
        self.assertEqual(second.assignments_checked, first.assignments_checked)

    def test_real_sample_cli_exhaustive_and_early_stop(self) -> None:
        for flags in ([], ["--stop-after-two"]):
            with self.subTest(flags=flags):
                process = subprocess.run(
                    [sys.executable, "-m", "tools.brute_force", str(SAMPLE), *flags],
                    cwd=SAMPLE.parents[2], capture_output=True, text=True, check=True,
                )
                report = json.loads(process.stdout)
                self.assertEqual(process.stderr, "")
                self.assertEqual(report["status"], bf.UNIQUE)
                self.assertEqual(report["satisfying_assignments"], 1)
                self.assertEqual(report["assignments_checked"], 512)
                self.assertTrue(report["exhaustive"])
                self.assertTrue(report["count_is_exact"])


if __name__ == "__main__":
    unittest.main()
