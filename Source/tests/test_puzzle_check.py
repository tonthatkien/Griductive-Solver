"""B6: independent counting, standard corpus and intentional failure demos."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import board
from engine.clue import clue_from_dict
from engine.constants import CRIMINAL, INNOCENT
from tools.brute_force import count_solutions
from tools.puzzle_check import DATA, audit_dataset, semantic_count


def fact(cell: str, status: str = CRIMINAL):
    """Build an independent primary fact for reference enumeration."""
    return clue_from_dict(cell, {"type": "FACT", "target": cell, "status": status})


class SemanticEnumerationTests(unittest.TestCase):
    """Compare pruning with B2 exhaustive truth tables, including all clue types."""

    def test_empty_constraints_count_all_assignments(self) -> None:
        self.assertEqual(semantic_count((), 3), 512)

    def test_contradiction_counts_zero(self) -> None:
        self.assertEqual(semantic_count((fact("A1"), fact("A1", INNOCENT)), 3), 0)

    def test_all_eight_clue_types_match_independent_b2(self) -> None:
        region = {"type": "list", "cells": ["A1", "B1", "C1"]}
        specs = [
            {"type": "FACT", "target": "A1", "status": INNOCENT},
            {"type": "SAME_STATUS", "cell1": "A1", "cell2": "C3"},
            {"type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "C3"},
            {"type": "EXACTLY", "region": region, "k": 1},
            {"type": "AT_LEAST", "region": region, "k": 2},
            {"type": "AT_MOST", "region": region, "k": 1},
            {"type": "PARITY", "region": region, "parity": "ODD"},
            {"type": "COMPARE", "region1": region,
             "region2": {"type": "list", "cells": ["A1", "C3"]}, "op": "GT"},
        ]
        for spec in specs:
            clues = (clue_from_dict("A1", spec),)
            with self.subTest(kind=spec["type"]):
                self.assertEqual(semantic_count(clues, 3),
                                 count_solutions(clues, 3).satisfying_assignments)

    def test_5x5_counts_primary_models_without_sat(self) -> None:
        fixed = tuple(fact(cell) for cell in board.all_cells(5)[:-4])
        self.assertEqual(semantic_count(fixed, 5), 16)
        self.assertEqual(semantic_count(fixed + tuple(
            fact(cell, INNOCENT) for cell in board.all_cells(5)[-4:]
        ), 5), 1)

    def test_evaluator_error_is_not_interpreted_as_unsat(self) -> None:
        with patch("tools.puzzle_check.evaluate", side_effect=RuntimeError("bad evaluator")):
            with self.assertRaisesRegex(RuntimeError, "bad evaluator"):
                semantic_count((fact("A1"),), 3)


class DatasetAuditTests(unittest.TestCase):
    """Audit acceptance requires separate expectations for standard and demo puzzles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_dataset()

    def test_all_nine_standard_puzzles_are_unique_solvable_and_labels_valid(self) -> None:
        standard = [r for r in self.report["results"] if r["path"].startswith("puzzles_")]
        self.assertEqual(len(standard), 9)
        for row in standard:
            with self.subTest(path=row["path"]):
                self.assertTrue(row["passes_expectation"])
                self.assertTrue(row["stored_labels_satisfy_all_clues"])
                self.assertEqual(row["agent_status"], "SOLVED")
                for key in ("clues_only", "clues_plus_initial_facts"):
                    self.assertEqual(row[key]["semantic_count_exact"], 1)
                    self.assertTrue(row[key]["agreement"])

    def test_failure_demos_have_expected_counts_and_no_reveals(self) -> None:
        demos = {Path(r["path"]).stem: r for r in self.report["results"]
                 if r["path"].startswith("demo_cases/")}
        self.assertEqual(set(demos), {"ambiguous", "inconsistent"})
        for name, status, count in (("ambiguous", "STUCK", 256),
                                    ("inconsistent", "INCONSISTENT", 0)):
            row = demos[name]
            self.assertTrue(row["passes_expectation"])
            self.assertEqual(row["agent_status"], status)
            self.assertEqual(row["accepted_steps"], 0)
            self.assertEqual(row["initial_proved"], row["final_proved"])
            self.assertEqual(row["clues_only"]["semantic_count_exact"], count)

    def test_report_matches_checked_in_artifact_and_content_hashes(self) -> None:
        import hashlib
        artifact = DATA.parents[1] / "docs" / "puzzle_check_results.json"
        self.assertEqual(self.report, json.loads(artifact.read_text()))
        self.assertTrue(self.report["all_passed"])
        for row in self.report["results"]:
            self.assertEqual(row["sha256"],
                             hashlib.sha256((DATA / row["path"]).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
