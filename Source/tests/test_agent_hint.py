"""E5: hint công khai, đủ chứng minh, deterministic và không lật thẻ."""

import unittest
from copy import deepcopy
from dataclasses import asdict

from engine.clue import clue_from_dict
from engine.constants import CRIMINAL, INNOCENT
from engine.game_state import PublicKB
from logic.agent import LogicAgent
from tests.test_agent_loop import DATA, ambiguous_puzzle, chain_puzzle, loaded
from tools.brute_force import check_public_kb


def clue(owner: str, target: str, status: str = CRIMINAL):
    """FACT với ID riêng theo thẻ sở hữu."""
    return clue_from_dict(owner, {"type": "FACT", "target": target, "status": status})


class HintTests(unittest.TestCase):
    """Kiểm tra kết quả và tính đủ/cần của các clue bằng oracle độc lập."""

    def test_returns_gui_tuple_and_first_forced_row_major(self) -> None:
        public = PublicKB(3, (clue("A1", "A2"), clue("B1", "B1", INNOCENT)))
        cell, verdict, ids = LogicAgent().hint(public)
        self.assertEqual((cell, verdict, ids), ("B1", INNOCENT, ["clue_B1"]))

    def test_skips_proved_and_unknown(self) -> None:
        public = PublicKB(3, (clue("A1", "C3"),), {"A1": CRIMINAL})
        self.assertEqual(LogicAgent().hint(public), ("C3", CRIMINAL, ["clue_A1"]))

    def test_transitive_proof_keeps_clue_not_directly_mentioning_target(self) -> None:
        relation = clue_from_dict("B1", {
            "type": "SAME_STATUS", "cell1": "B1", "cell2": "C1",
        })
        public = PublicKB(3, (clue("A1", "C1"), relation), {"A1": INNOCENT})
        result = LogicAgent().hint(public)
        self.assertEqual(result, ("B1", CRIMINAL, ["clue_A1", "clue_B1"]))

    def test_removes_irrelevant_and_redundant_clues_deterministically(self) -> None:
        public = PublicKB(3, (clue("A1", "B1"), clue("B1", "B1"),
                              clue("C1", "C3")), {"A1": INNOCENT})
        agent = LogicAgent()
        self.assertEqual(agent.hint(public), ("B1", CRIMINAL, ["clue_B1"]))
        self.assertEqual(agent.hint(public), agent.hint(public))

    def test_proved_context_is_kept_while_minimizing(self) -> None:
        relation = clue_from_dict("B1", {
            "type": "DIFFERENT_STATUS", "cell1": "A1", "cell2": "B1",
        })
        public = PublicKB(3, (clue("A1", "A1"), relation), {"A1": CRIMINAL})
        self.assertEqual(LogicAgent().hint(public), ("B1", INNOCENT, ["clue_B1"]))

    def test_ambiguous_solved_and_inconsistent_have_no_hint(self) -> None:
        for public in (PublicKB(3), loaded(ambiguous_puzzle()).get_public_kb(),
                       PublicKB(1, (), {"A1": CRIMINAL}),
                       PublicKB(3, (clue("A1", "A1", INNOCENT),), {"A1": CRIMINAL})):
            with self.subTest(public=public):
                self.assertIsNone(LogicAgent().hint(public))

    def test_snapshot_engine_trace_and_solve_status_are_not_changed(self) -> None:
        engine = loaded()
        agent = LogicAgent()
        agent.step(engine)
        public = engine.get_public_kb()
        before = deepcopy(asdict(public))
        trace = deepcopy(agent.trace)
        status = agent.solve_status
        agent.hint(public)
        self.assertEqual(asdict(public), before)
        self.assertEqual(asdict(engine.get_public_kb()), before)
        self.assertEqual(agent.trace, trace)
        self.assertEqual(agent.solve_status, status)

    def test_hidden_labels_and_unrevealed_clues_cannot_affect_hint(self) -> None:
        data = chain_puzzle()
        first = loaded(data).get_public_kb()
        for person in data["characters"][1:]:
            person["criminal"] = not person["criminal"]
            person["clue"] = {"type": "FACT", "target": "C3", "status": INNOCENT}
        second = loaded(data).get_public_kb()
        self.assertEqual(LogicAgent().hint(first), LogicAgent().hint(second))

    def test_invalid_input_is_rejected(self) -> None:
        for public in (None, {}, loaded(), PublicKB(0), PublicKB(3, proved=[])):
            with self.subTest(public=public), self.assertRaises(ValueError):
                LogicAgent().hint(public)

    def test_timeout_in_selection_does_not_produce_hint(self) -> None:
        engine = loaded()
        before = asdict(engine.get_public_kb())
        with self.assertRaises(TimeoutError):
            LogicAgent(timeout=0).hint(engine.get_public_kb())
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_timeout_in_explanation_does_not_return_unverified_clues(self) -> None:
        from unittest.mock import patch
        agent = LogicAgent()
        original = agent.next_forced

        def select(public):
            result = original(public)
            agent.timeout = 0
            return result

        with patch.object(agent, "next_forced", side_effect=select):
            with self.assertRaises(TimeoutError):
                agent.hint(loaded().get_public_kb())

    def test_all_repository_hints_are_public_and_forced(self) -> None:
        from engine.game_state import GameEngine
        for path in sorted(DATA.glob("puzzles_*/*.json")):
            with self.subTest(path=path):
                engine = GameEngine()
                engine.load_puzzle(path)
                public = engine.get_public_kb()
                agent = LogicAgent(timeout=10)
                result = agent.hint(public)
                self.assertIsNotNone(result)
                cell, verdict, ids = result
                self.assertNotIn(cell, public.proved)
                self.assertEqual(agent.classify(public, cell), verdict)
                selected = tuple(c for c in public.revealed_clues if c.id in ids)
                reduced = PublicKB(public.n, selected, public.proved)
                self.assertEqual(agent.classify(reduced, cell), verdict)
                for omitted in selected:
                    smaller = PublicKB(public.n, tuple(c for c in selected if c is not omitted),
                                       public.proved)
                    self.assertNotEqual(agent.classify(smaller, cell), verdict)
                if public.n <= 4:
                    self.assertEqual(check_public_kb(reduced).classifications[cell], verdict)


if __name__ == "__main__":
    unittest.main()
