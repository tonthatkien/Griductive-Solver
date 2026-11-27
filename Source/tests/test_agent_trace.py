"""E3: trace thật, ranh giới public KB và xuất dữ liệu cho GUI/report."""

import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from engine import board
from engine.constants import CRIMINAL, INNOCENT, NOT_PROVABLE
from engine.game_state import PublicKB
from gui.solver_driver import run_step
from logic.agent import LogicAgent, STUCK, TIMEOUT
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver
from tests.test_agent_loop import (
    PublicEngineProxy, SnapshotEngine, ambiguous_puzzle, fact, loaded,
)


class TraceTests(unittest.TestCase):
    """Đối chiếu trace với solver thật và snapshot trước/sau reveal."""

    def test_innocent_trace_contains_all_three_actual_queries(self) -> None:
        agent = LogicAgent()
        entry = agent.step(loaded())
        self.assertEqual(entry.sat_queries, [
            ("KB", "SAT"), ("KB ∧ ¬C_B1", "SAT"), ("KB ∧ C_B1", "UNSAT"),
        ])
        self.assertEqual(entry.verdict, INNOCENT)
        self.assertEqual(agent.sat_calls, 6)  # selection + real engine validation

    def test_criminal_trace_stops_after_opposite_assumption_unsat(self) -> None:
        agent = LogicAgent()
        engine = loaded()
        agent.step(engine)
        entry = agent.step(engine)
        self.assertEqual(entry.sat_queries, [("KB", "SAT"), ("KB ∧ ¬C_C1", "UNSAT")])
        self.assertEqual(entry.verdict, CRIMINAL)
        self.assertEqual(entry.step, 2)

    def test_every_recorded_query_replays_on_pre_reveal_kb(self) -> None:
        proxy = PublicEngineProxy(loaded())
        entries = LogicAgent().auto_solve(proxy)
        solver = DPLLSolver()
        for entry, public in zip(entries, proxy.before_submit):
            kb = Encoder(public.n).build_kb(public)
            for expression, expected in entry.sat_queries:
                assumptions = []
                for term in expression.split(" ∧ ")[1:]:
                    negative = term.startswith("¬")
                    cell = term.removeprefix("¬").removeprefix("C_")
                    var = board.var_of(cell, public.n)
                    assumptions.append(-var if negative else var)
                actual = solver.solve(kb.clauses, kb.num_vars, assumptions=assumptions)
                self.assertEqual("SAT" if actual.sat else "UNSAT", expected)

    def test_clue_ids_are_before_and_after_reveal_not_hidden(self) -> None:
        engine = loaded()
        before = engine.get_public_kb()
        entry = LogicAgent().step(PublicEngineProxy(engine))
        after = engine.get_public_kb()
        self.assertEqual(entry.active_clue_ids, [c.id for c in before.revealed_clues])
        new_ids = {c.id for c in after.revealed_clues} - set(entry.active_clue_ids)
        self.assertEqual(new_ids, {entry.newly_revealed_clue_id})
        self.assertNotIn(entry.newly_revealed_clue_id, entry.active_clue_ids)

    def test_unknown_scan_queries_are_preserved_in_execution_order(self) -> None:
        # Use a 3x3 snapshot with only B1 forced: A1 must be scanned as UNKNOWN.
        before = PublicKB(3, (fact("B1", CRIMINAL),))
        after = PublicKB(3, before.revealed_clues, {"B1": CRIMINAL})
        entry = LogicAgent().step(SnapshotEngine(before, after))
        self.assertEqual(entry.sat_queries, [
            ("KB", "SAT"), ("KB ∧ ¬C_A1", "SAT"), ("KB ∧ C_A1", "SAT"),
            ("KB ∧ ¬C_B1", "UNSAT"),
        ])
        self.assertEqual(entry.newly_revealed_clue_id, "")

    def test_previous_queries_and_later_classify_do_not_pollute_trace(self) -> None:
        agent = LogicAgent()
        engine = loaded()
        agent.classify(engine.get_public_kb(), "C3")
        entry = agent.step(engine)
        saved = asdict(entry)
        agent.classify(engine.get_public_kb(), "C3")
        agent.step(engine)
        self.assertEqual(asdict(entry), saved)
        self.assertEqual(len(entry.sat_queries), 3)

    def test_stuck_and_rejection_do_not_add_entries(self) -> None:
        agent = LogicAgent()
        self.assertIsNone(agent.step(loaded(ambiguous_puzzle())))
        self.assertEqual(agent.solve_status, STUCK)
        self.assertEqual(agent.trace, [])
        public = PublicKB(3, (fact("A1", CRIMINAL),))
        with self.assertRaises(RuntimeError):
            agent.step(SnapshotEngine(public, public, NOT_PROVABLE))
        self.assertEqual(agent.trace, [])

    def test_timeout_preserves_accepted_trace_without_partial_entry(self) -> None:
        agent = LogicAgent()
        engine = loaded()
        first = agent.step(engine)
        agent.timeout = 0
        with self.assertRaises(TimeoutError):
            agent.step(engine)
        self.assertEqual(agent.solve_status, TIMEOUT)
        self.assertEqual(agent.trace, [first])
        self.assertTrue(all(result != TIMEOUT for _, result in first.sat_queries))

    def test_auto_solve_resets_trace_and_exports_json_without_custom_encoder(self) -> None:
        agent = LogicAgent()
        first = agent.auto_solve(loaded())
        saved = json.dumps([asdict(e) for e in first], ensure_ascii=False)
        second = agent.auto_solve(loaded())
        self.assertEqual([e.step for e in second], list(range(1, 9)))
        self.assertEqual(saved, json.dumps([asdict(e) for e in second], ensure_ascii=False))
        self.assertIsNot(first, agent.trace)
        self.assertEqual(len(json.loads(saved)), 8)

    def test_gui_driver_uses_step_with_real_queries(self) -> None:
        engine = PublicEngineProxy(loaded())
        # Adapter supplies the GUI's missing baseline engine API, without changing engine.
        engine.unsolved_cells = lambda: [
            c for c in board.all_cells(3) if c not in engine.get_public_kb().proved
        ]
        agent = LogicAgent()
        with patch.object(agent, "step", wraps=agent.step) as step:
            result = run_step(engine, agent, 1)
        step.assert_called_once_with(engine)
        self.assertFalse(result.queries_summarized)
        self.assertEqual(result.entry, agent.trace[0])
        self.assertEqual(len(result.entry.sat_queries), 3)
        self.assertEqual(result.new_clue_ids, [result.entry.newly_revealed_clue_id])


if __name__ == "__main__":
    unittest.main()
