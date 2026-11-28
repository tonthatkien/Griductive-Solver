"""Kiểm thử E1: entailment, thống kê, timeout và ranh giới PublicKB."""

import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.constants import (
    ACCEPTED, CONTRADICTED, CRIMINAL, INCONSISTENT, INNOCENT, NOT_PROVABLE, UNKNOWN,
)
from engine.game_state import GameEngine, PublicKB
from logic.agent import LogicAgent, SAT, TIMEOUT, UNSAT
from logic.cnf_encoder import Encoder
from logic.dpll import DPLLSolver, SolveResult, SolverStats
from tools.brute_force import check_public_kb

DATA = Path(__file__).resolve().parents[1] / "data"
SAMPLE = DATA / "puzzles_3x3" / "p01.json"


def clue(kind: str = "FACT", **params: object) -> Clue:
    """Tạo clue công khai theo schema chung."""
    return clue_from_dict("A1", {"type": kind, **params})


def kb(*clues: Clue, proved: dict[str, str] | None = None, n: int = 3) -> PublicKB:
    """Tạo PublicKB độc lập với nhãn ẩn và engine."""
    return PublicKB(n, tuple(clues), dict(proved or {}))


def outcome(sat: bool = True, *, timed_out: bool = False, value: int = 1) -> SolveResult:
    """Kết quả DPLL giả để kiểm tra orchestration và cộng dồn thống kê."""
    stats = SolverStats(value, value + 1, value + 2, value / 10)
    return SolveResult(sat, {} if sat else None, stats, timed_out)


class ClassificationTests(unittest.TestCase):
    """Kiểm tra ý nghĩa logic của bốn verdict bằng encoder và solver thật."""

    def test_empty_kb_returns_unknown_not_model_value(self) -> None:
        self.assertEqual(LogicAgent().classify(kb(), "A1"), UNKNOWN)

    def test_fact_criminal(self) -> None:
        self.assertEqual(LogicAgent().classify(kb(clue(target="A1", status=CRIMINAL)), "A1"),
                         CRIMINAL)

    def test_fact_innocent(self) -> None:
        self.assertEqual(LogicAgent().classify(kb(clue(target="A1", status=INNOCENT)), "A1"),
                         INNOCENT)

    def test_inconsistent_kb_does_not_entail_a_verdict_for_other_cell(self) -> None:
        public = kb(clue(target="A1", status=CRIMINAL), proved={"A1": INNOCENT})
        agent = LogicAgent()
        self.assertEqual(agent.classify(public, "B2"), INCONSISTENT)
        self.assertEqual(agent.sat_calls, 1)

    def test_proved_verdict_is_still_checked_for_consistency(self) -> None:
        for status in (CRIMINAL, INNOCENT):
            with self.subTest(status=status):
                self.assertEqual(LogicAgent().classify(kb(proved={"A1": status}), "A1"), status)
        public = kb(clue(target="B1", status=INNOCENT),
                    proved={"A1": CRIMINAL, "B1": CRIMINAL})
        self.assertEqual(LogicAgent().classify(public, "A1"), INCONSISTENT)

    def test_assignment_from_one_model_is_not_entailment(self) -> None:
        # (A or B) and (not A or B): B forced, A vẫn có thể True hoặc False.
        public = kb(
            clue("AT_LEAST", region={"type": "list", "cells": ["A1", "B1"]}, k=1),
            clue("COMPARE", region1={"type": "list", "cells": ["A1"]}, op="LE",
                 region2={"type": "list", "cells": ["B1"]}),
        )
        agent = LogicAgent()
        self.assertEqual(agent.classify(public, "B1"), CRIMINAL)
        self.assertEqual(agent.classify(public, "A1"), UNKNOWN)

    def test_primary_target_is_not_confused_with_auxiliary_variables(self) -> None:
        public = kb(clue("PARITY", region={"type": "row", "number": 1}, parity="EVEN"))
        self.assertGreater(Encoder(3).build_kb(public).num_vars, 9)
        agent = LogicAgent()
        self.assertEqual(agent.classify(public, "C3"), UNKNOWN)
        self.assertEqual([q.assumptions for q in agent.last_queries], [(), (-9,), (9,)])

    def test_supported_board_sizes_include_5x5(self) -> None:
        for n in (1, 3, 4, 5):
            with self.subTest(n=n):
                target = board.all_cells(n)[-1]
                self.assertEqual(LogicAgent().classify(kb(proved={target: INNOCENT}, n=n),
                                                       target), INNOCENT)

    def test_updated_public_kb_rebuilds_constraints_without_stale_cache(self) -> None:
        public = kb()
        agent = LogicAgent()
        self.assertEqual(agent.classify(public, "A1"), UNKNOWN)
        public.proved["A1"] = CRIMINAL
        self.assertEqual(agent.classify(public, "A1"), CRIMINAL)
        public.proved["A1"] = INNOCENT
        self.assertEqual(agent.classify(public, "A1"), INNOCENT)

    def test_public_kb_and_clue_params_are_unchanged(self) -> None:
        public = kb(clue("AT_MOST", region={"type": "list", "cells": ["A1", "B1"]}, k=0))
        before = deepcopy(asdict(public))
        agent = LogicAgent()
        agent.classify(public, "A1")
        agent.classify(public, "C3")
        self.assertEqual(asdict(public), before)

    def test_repeat_calls_are_deterministic(self) -> None:
        public = kb(clue("SAME_STATUS", cell1="A1", cell2="B1"), proved={"A1": CRIMINAL})
        agent = LogicAgent()
        snapshots = []
        for _ in range(2):
            self.assertEqual(agent.classify(public, "B1"), CRIMINAL)
            snapshots.append([(q.assumptions, q.status, q.stats.decisions,
                               q.stats.propagations, q.stats.backtracks)
                              for q in agent.last_queries])
        self.assertEqual(*snapshots)


class StatisticsAndTimeoutTests(unittest.TestCase):
    """Mỗi truy vấn được lưu và timeout không bị biến thành một verdict."""

    def test_base_and_assumption_queries_record_exact_stats(self) -> None:
        results = [outcome(value=1), outcome(value=2), outcome(False, value=3)]
        public = kb(clue("PARITY", region={"type": "row", "number": 1}, parity="EVEN"))
        expected = Encoder(3).build_kb(public)
        with patch.object(DPLLSolver, "solve", side_effect=results) as solve:
            agent = LogicAgent(timeout=0.25)
            self.assertEqual(agent.classify(public, "C3"), INNOCENT)
        self.assertEqual(agent.sat_calls, 3)
        self.assertEqual([q.status for q in agent.last_queries], [SAT, SAT, UNSAT])
        self.assertEqual([q.assumptions for q in agent.last_queries], [(), (-9,), (9,)])
        self.assertEqual(agent.total_decisions, 6)
        self.assertEqual(agent.total_propagations, 9)
        self.assertEqual(agent.total_backtracks, 12)
        self.assertAlmostEqual(agent.total_runtime, 0.6)
        for call in solve.call_args_list:
            self.assertEqual(call.args, (expected.clauses, expected.num_vars))
            self.assertEqual(call.kwargs["timeout"], 0.25)
        results[0].stats.decisions = 999
        self.assertEqual(agent.sat_queries[0].stats.decisions, 1)

    def test_criminal_proof_stops_after_second_query(self) -> None:
        with patch.object(DPLLSolver, "solve", side_effect=[outcome(), outcome(False)]) as solve:
            agent = LogicAgent()
            self.assertEqual(agent.classify(kb(), "B1"), CRIMINAL)
        self.assertEqual(solve.call_count, 2)
        self.assertEqual(agent.sat_calls, 2)

    def test_counters_accumulate_and_last_queries_reset(self) -> None:
        agent = LogicAgent()
        agent.classify(kb(proved={"A1": CRIMINAL}), "A1")
        first_queries = list(agent.last_queries)
        agent.classify(kb(), "A1")
        self.assertEqual(agent.sat_calls, 5)
        self.assertEqual(len(agent.sat_queries), 5)
        self.assertEqual(len(agent.last_queries), 3)
        self.assertEqual(agent.total_decisions,
                         sum(q.stats.decisions for q in agent.sat_queries))
        self.assertEqual(agent.total_propagations,
                         sum(q.stats.propagations for q in agent.sat_queries))
        self.assertEqual(agent.total_backtracks,
                         sum(q.stats.backtracks for q in agent.sat_queries))
        self.assertAlmostEqual(agent.total_runtime,
                               sum(q.stats.runtime for q in agent.sat_queries))
        self.assertEqual([q.status for q in first_queries], [SAT, UNSAT])

    def test_timeout_at_any_query_raises_and_records_partial_stats(self) -> None:
        for phase in range(3):
            results = [outcome() for _ in range(phase)] + [outcome(False, timed_out=True)]
            with self.subTest(phase=phase), patch.object(DPLLSolver, "solve", side_effect=results):
                agent = LogicAgent()
                with self.assertRaises(TimeoutError):
                    agent.classify(kb(), "A1")
                self.assertEqual(agent.sat_calls, phase + 1)
                self.assertEqual(agent.last_queries[-1].status, TIMEOUT)
                self.assertEqual(agent.total_decisions, phase + 1)

    def test_timeout_flag_takes_precedence_over_sat_flag(self) -> None:
        with patch.object(DPLLSolver, "solve", return_value=outcome(True, timed_out=True)):
            with self.assertRaises(TimeoutError):
                LogicAgent().classify(kb(), "A1")

    def test_real_solver_zero_timeout_does_not_claim_inconsistency(self) -> None:
        agent = LogicAgent(timeout=0)
        with self.assertRaises(TimeoutError):
            agent.classify(kb(), "A1")
        self.assertEqual(agent.sat_calls, 1)
        self.assertEqual(agent.last_queries[0].status, TIMEOUT)

    def test_solver_exception_propagates(self) -> None:
        with patch.object(DPLLSolver, "solve", side_effect=RuntimeError("solver bug")):
            agent = LogicAgent()
            with self.assertRaisesRegex(RuntimeError, "solver bug"):
                agent.classify(kb(), "A1")
        self.assertEqual(agent.sat_calls, 1)
        self.assertEqual(agent.last_queries, [])


class InputValidationTests(unittest.TestCase):
    """Dữ liệu sai không được chuyển thành UNSAT hoặc một verdict."""

    def test_invalid_cells_fail_without_sat_call(self) -> None:
        agent = LogicAgent()
        for cell in (None, True, [], "a1", "A01", "D1", "A0"):
            with self.subTest(cell=cell), self.assertRaises(ValueError):
                agent.classify(kb(), cell)
        self.assertEqual(agent.sat_calls, 0)

    def test_invalid_board_sizes_fail(self) -> None:
        for n in (0, -1, 11, True, 3.0, "3"):
            with self.subTest(n=n), self.assertRaises(ValueError):
                LogicAgent().classify(PublicKB(n), "A1")

    def test_engine_and_non_public_inputs_are_rejected(self) -> None:
        for public in (None, {}, GameEngine(), PublicKB(3, proved=[])):
            with self.subTest(public=type(public).__name__), self.assertRaises(ValueError):
                LogicAgent().classify(public, "A1")

    def test_invalid_clues_and_proved_verdicts_fail_before_sat(self) -> None:
        invalid = [
            kb(clue(target="Z9", status=CRIMINAL)),
            kb(clue("UNSUPPORTED")),
            kb(proved={"A1": UNKNOWN}),
            kb(proved={"D1": CRIMINAL}),
        ]
        with patch.object(DPLLSolver, "solve") as solve:
            for public in invalid:
                with self.subTest(public=public), self.assertRaises(ValueError):
                    LogicAgent().classify(public, "A1")
            solve.assert_not_called()

    def test_invalid_timeouts_fail(self) -> None:
        for value in (True, "1", [], float("nan")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                LogicAgent(timeout=value)


class IndependentOracleTests(unittest.TestCase):
    """Đối chiếu mọi ô với B2 semantic brute force độc lập với CNF/DPLL."""

    def test_all_eight_clue_types_and_unsat_against_brute_force(self) -> None:
        row = {"type": "row", "number": 1}
        fixtures = [
            kb(),
            kb(clue(target="A1", status=CRIMINAL)),
            kb(clue("SAME_STATUS", cell1="A1", cell2="B1"), proved={"A1": CRIMINAL}),
            kb(clue("DIFFERENT_STATUS", cell1="A1", cell2="B1"), proved={"A1": CRIMINAL}),
            kb(clue("EXACTLY", region=row, k=0)),
            kb(clue("AT_LEAST", region=row, k=3)),
            kb(clue("AT_MOST", region=row, k=0, status=INNOCENT)),
            kb(clue("PARITY", region=row, parity="EVEN"),
               proved={"A1": CRIMINAL, "B1": INNOCENT}),
            kb(clue("COMPARE", region1={"type": "list", "cells": ["A1"]}, op="GT",
                    region2={"type": "list", "cells": ["B1"]})),
            kb(clue(target="A1", status=INNOCENT), proved={"A1": CRIMINAL}),
        ]
        for index, public in enumerate(fixtures):
            expected = check_public_kb(public).classifications
            agent = LogicAgent()
            for cell in board.all_cells(public.n):
                with self.subTest(fixture=index, cell=cell):
                    self.assertEqual(agent.classify(public, cell), expected[cell])

    def test_all_3x3_and_4x4_initial_public_states_against_brute_force(self) -> None:
        for n in (3, 4):
            for path in sorted((DATA / f"puzzles_{n}x{n}").glob("*.json")):
                engine = GameEngine()
                engine.load_puzzle(path)
                public = engine.get_public_kb()
                expected = check_public_kb(public).classifications
                agent = LogicAgent()
                for cell in board.all_cells(n):
                    with self.subTest(puzzle=path.name, n=n, cell=cell):
                        self.assertEqual(agent.classify(public, cell), expected[cell])


class EngineIntegrationTests(unittest.TestCase):
    """Chơi một bước bằng classify thật, không triển khai vòng lặp auto_solve."""

    def loaded_engine(self) -> GameEngine:
        """Tạo engine thật từ puzzle mẫu."""
        engine = GameEngine()
        engine.load_puzzle(SAMPLE)
        return engine

    def test_real_agent_proves_first_wave(self) -> None:
        engine = self.loaded_engine()
        agent = LogicAgent()
        for cell in ("B2", "C2", "C3"):
            with self.subTest(cell=cell):
                self.assertEqual(engine.submit_verdict(cell, CRIMINAL, agent.classify), ACCEPTED)

    def test_unknown_verdict_does_not_reveal_card_or_change_state(self) -> None:
        engine = self.loaded_engine()
        before = asdict(engine.get_public_kb())
        self.assertEqual(engine.submit_verdict("A3", INNOCENT, LogicAgent().classify), NOT_PROVABLE)
        self.assertEqual(asdict(engine.get_public_kb()), before)
        self.assertFalse(engine.is_revealed("A3"))

    def test_opposite_forced_verdict_is_contradicted(self) -> None:
        engine = self.loaded_engine()
        before = asdict(engine.get_public_kb())
        self.assertEqual(engine.submit_verdict("B2", INNOCENT, LogicAgent().classify), CONTRADICTED)
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_timeout_does_not_reveal_or_change_engine_state(self) -> None:
        engine = self.loaded_engine()
        before = asdict(engine.get_public_kb())
        with self.assertRaises(TimeoutError):
            engine.submit_verdict("B2", CRIMINAL, LogicAgent(timeout=0).classify)
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_unrevealed_labels_and_clues_cannot_change_verdicts(self) -> None:
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
        original = self.loaded_engine().get_public_kb()
        for character in data["characters"]:
            if character["cell"] not in data["initially_revealed"]:
                character["criminal"] = not character["criminal"]
                character["clue"] = {"type": "FACT", "target": "A3", "status": CRIMINAL}
        altered = GameEngine()
        altered.load_puzzle(data)
        first, second = LogicAgent(), LogicAgent()
        for cell in board.all_cells(3):
            with self.subTest(cell=cell):
                self.assertEqual(first.classify(original, cell),
                                 second.classify(altered.get_public_kb(), cell))


if __name__ == "__main__":
    unittest.main()
