"""B6: independent counting, standard corpus and intentional failure demos."""

import hashlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.constants import CRIMINAL, INCONSISTENT, INNOCENT
from logic.agent import SOLVED, STUCK
from tools.brute_force import count_solutions
from tools.puzzle_check import DATA, audit_dataset, main, puzzle_digest, semantic_count


def fact(cell: str, status: str = CRIMINAL) -> Clue:
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

    def test_non_boolean_evaluator_is_rejected(self) -> None:
        for result in (None, 0, 1, "False"):
            with self.subTest(result=result), \
                    patch("tools.puzzle_check.evaluate", return_value=result):
                with self.assertRaisesRegex(TypeError, "must return bool"):
                    semantic_count((fact("A1"),), 3)

    def test_preflight_reaches_bad_clue_after_early_contradiction(self) -> None:
        broken = fact("C3")

        def evaluator(clue: Clue, assignment: dict[str, bool], n: int) -> bool:
            if clue is broken:
                raise RuntimeError("late clue error")
            return False

        with patch("tools.puzzle_check.evaluate", side_effect=evaluator):
            with self.assertRaisesRegex(RuntimeError, "late clue error"):
                semantic_count((fact("A1"), broken), 3)

    def test_unknown_demo_has_clear_error_before_audit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "demo_cases").mkdir()
            (root / "demo_cases" / "new_case.json").write_text("{}", encoding="utf-8")
            with patch("tools.puzzle_check.DATA", root), \
                    patch("tools.puzzle_check.audit_puzzle") as audit:
                with self.assertRaisesRegex(ValueError, "Missing demo expectation: new_case.json"):
                    audit_dataset()
                audit.assert_not_called()


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
                self.assertEqual(row["agent_status"], SOLVED)
                for key in ("clues_only", "clues_plus_initial_facts"):
                    self.assertEqual(row[key]["semantic_count_exact"], 1)
                    self.assertTrue(row[key]["agreement"])

    def test_failure_demos_have_expected_counts_and_no_reveals(self) -> None:
        demos = {Path(r["path"]).stem: r for r in self.report["results"]
                 if r["path"].startswith("demo_cases/")}
        self.assertEqual(set(demos), {"ambiguous", "inconsistent"})
        for name, status, count in (("ambiguous", STUCK, 256),
                                    ("inconsistent", INCONSISTENT, 0)):
            row = demos[name]
            self.assertTrue(row["passes_expectation"])
            self.assertEqual(row["agent_status"], status)
            self.assertEqual(row["accepted_steps"], 0)
            self.assertEqual(row["initial_proved"], row["final_proved"])
            self.assertEqual(row["clues_only"]["semantic_count_exact"], count)

    def test_report_structure_and_normalized_content_hashes(self) -> None:
        self.assertTrue(self.report["all_passed"])
        self.assertEqual(self.report["standard_puzzles"], 9)
        self.assertEqual(self.report["intentional_demos"], 2)
        self.assertEqual(len(self.report["results"]), 11)
        for row in self.report["results"]:
            content = (DATA / row["path"]).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(json.loads(json.dumps(self.report)), self.report)


class PortableReportTests(unittest.TestCase):
    """Exercise newline normalization and CLI encoding without repository docs."""

    def test_digest_ignores_only_crlf_conversion_not_content_changes(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "puzzle.json"
            lf = '{"title": "Vụ án"}\n'.encode("utf-8")
            path.write_bytes(lf)
            expected = puzzle_digest(path)
            path.write_bytes(lf.replace(b"\n", b"\r\n"))
            self.assertEqual(puzzle_digest(path), expected)
            path.write_bytes(lf.replace(b"title", b"other"))
            self.assertNotEqual(puzzle_digest(path), expected)

    def test_out_writes_utf8_without_bom_or_crlf(self) -> None:
        report = {"all_passed": True, "title": "Vụ án"}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "reports" / "result.json"
            with patch("sys.argv", ["puzzle_check", "--out", str(output)]), \
                    patch("tools.puzzle_check.audit_dataset", return_value=report), \
                    patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(main(), 0)
                self.assertEqual(stdout.getvalue(), "")
            raw = output.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r\n", raw)
            self.assertTrue(raw.endswith(b"\n"))
            self.assertEqual(json.loads(raw.decode("utf-8")), report)

    def test_failed_audit_still_writes_report_and_returns_nonzero(self) -> None:
        report = {"all_passed": False}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            with patch("sys.argv", ["puzzle_check", "--out", str(output)]), \
                    patch("tools.puzzle_check.audit_dataset", return_value=report):
                self.assertEqual(main(), 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)

    def test_default_stdout_remains_json(self) -> None:
        report = {"all_passed": True}
        with patch("sys.argv", ["puzzle_check"]), \
                patch("tools.puzzle_check.audit_dataset", return_value=report), \
                patch("sys.stdout", new_callable=io.StringIO) as stdout:
            self.assertEqual(main(), 0)
            self.assertEqual(json.loads(stdout.getvalue()), report)


if __name__ == "__main__":
    unittest.main()
