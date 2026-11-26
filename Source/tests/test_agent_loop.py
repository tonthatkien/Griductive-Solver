"""Kiểm thử E2: chọn forced, cập nhật public KB, dừng đúng và không đoán."""

import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from engine import board
from engine.clue import Clue, clue_from_dict
from engine.constants import (
    ACCEPTED, CONTRADICTED, CRIMINAL, INCONSISTENT, INNOCENT, NOT_PROVABLE, UNKNOWN,
)
from engine.game_state import GameEngine, PublicKB
from logic.agent import LogicAgent, SOLVED, STUCK, TIMEOUT
from logic.cnf_encoder import Encoder
from tools.brute_force import check_public_kb

DATA = Path(__file__).resolve().parents[1] / "data"


def fact(cell: str, status: str) -> Clue:
    """Tạo clue chỉ dùng thông tin công khai."""
    return clue_from_dict("A1", {"type": "FACT", "target": cell, "status": status})


def chain_puzzle(n: int = 3) -> dict:
    """Mỗi lần lật thẻ mới lộ FACT về ô tiếp theo."""
    cells = board.all_cells(n)
    values = {c: i % 2 == 0 for i, c in enumerate(cells)}
    characters = []
    for i, cell in enumerate(cells):
        target = cells[min(i + 1, len(cells) - 1)]
        characters.append({
            "cell": cell, "name": f"Person {i:02d}", "profession": "Tester",
            "criminal": values[cell],
            "clue": {"type": "FACT", "target": target,
                     "status": CRIMINAL if values[target] else INNOCENT},
        })
    return {"n": n, "characters": characters, "initially_revealed": [cells[0]]}


def loaded(data: dict | None = None) -> GameEngine:
    """Nạp engine thật cho test."""
    engine = GameEngine()
    engine.load_puzzle(chain_puzzle() if data is None else data)
    return engine


def ambiguous_puzzle() -> dict:
    """Mọi clue chỉ nhắc trạng thái A1 đã biết, các thẻ úp không bị ép."""
    data = chain_puzzle()
    for character in data["characters"]:
        character["clue"] = {"type": "FACT", "target": "A1", "status": CRIMINAL}
    return data


class PublicEngineProxy:
    """Chỉ có get_public_kb/submit_verdict, không có n/characters/nhãn/clue ẩn."""

    def __init__(self, engine: GameEngine) -> None:
        self._source = engine
        self.calls: list[tuple[str, str]] = []
        self.before_submit: list[PublicKB] = []

    def get_public_kb(self) -> PublicKB:
        """Lấy snapshot mới từ engine thật."""
        return self._source.get_public_kb()

    def submit_verdict(
        self, cell: str, verdict: str, classify: Callable[[PublicKB, str], str]
    ) -> str:
        """Ghi nhận trạng thái ngay trước khi engine kiểm chứng verdict."""
        self.calls.append((cell, verdict))
        self.before_submit.append(self.get_public_kb())
        return self._source.submit_verdict(cell, verdict, classify)


class SnapshotEngine:
    """Engine giả có kết quả submit cố định để kiểm tra các trường hợp lỗi hợp đồng."""

    def __init__(self, before: PublicKB, after: PublicKB, response: str = ACCEPTED) -> None:
        self.before, self.after, self.response = before, after, response
        self.calls = 0

    def get_public_kb(self) -> PublicKB:
        """Snapshot trước hoặc sau lần nộp đầu tiên."""
        return deepcopy(self.after if self.calls else self.before)

    def submit_verdict(
        self, cell: str, verdict: str, classify: Callable[[PublicKB, str], str]
    ) -> str:
        """Mô phỏng phản hồi cố định của engine."""
        self.calls += 1
        return self.response


class NextForcedTests(unittest.TestCase):
    """Chỉ chọn ô chưa proved đầu tiên theo row-major và không sửa snapshot."""

    def test_row_major_not_alphabetical_or_clue_order(self) -> None:
        public = PublicKB(3, (fact("A2", INNOCENT), fact("B1", CRIMINAL)),
                          {"A1": INNOCENT})
        self.assertEqual(LogicAgent().next_forced(public), ("B1", CRIMINAL))

    def test_skips_proved_cells_and_selects_innocent(self) -> None:
        public = PublicKB(3, (fact("A1", CRIMINAL), fact("B1", INNOCENT)),
                          {"A1": CRIMINAL})
        self.assertEqual(LogicAgent().next_forced(public), ("B1", INNOCENT))

    def test_unknown_cells_are_skipped_until_a_forced_cell(self) -> None:
        self.assertEqual(LogicAgent().next_forced(PublicKB(3, (fact("C3", INNOCENT),))),
                         ("C3", INNOCENT))

    def test_empty_and_ambiguous_public_kb_return_none(self) -> None:
        for public in (PublicKB(3), loaded(ambiguous_puzzle()).get_public_kb()):
            with self.subTest(public=public):
                self.assertIsNone(LogicAgent().next_forced(public))

    def test_inconsistent_kb_returns_no_verdict(self) -> None:
        public = PublicKB(3, (fact("A1", INNOCENT),), {"A1": CRIMINAL})
        agent = LogicAgent()
        self.assertIsNone(agent.next_forced(public))
        self.assertEqual(agent.sat_calls, 1)

    def test_all_proved_returns_none_but_still_checks_consistency(self) -> None:
        agent = LogicAgent()
        public = PublicKB(1, (), {"A1": CRIMINAL})
        self.assertIsNone(agent.next_forced(public))
        bad = PublicKB(1, (fact("A1", INNOCENT),), {"A1": CRIMINAL})
        self.assertIsNone(agent.next_forced(bad))
        self.assertEqual(agent.sat_calls, 2)
        self.assertEqual(agent.last_queries[-1].status, "UNSAT")

    def test_snapshot_is_not_mutated(self) -> None:
        public = loaded().get_public_kb()
        before = deepcopy(asdict(public))
        LogicAgent().next_forced(public)
        self.assertEqual(asdict(public), before)

    def test_same_public_information_gives_same_choice(self) -> None:
        data = chain_puzzle()
        first = loaded(data).get_public_kb()
        for character in data["characters"][1:]:
            character["criminal"] = not character["criminal"]
            character["clue"] = {"type": "FACT", "target": "C3", "status": CRIMINAL}
        second = loaded(data).get_public_kb()
        self.assertEqual(LogicAgent().next_forced(first), LogicAgent().next_forced(second))

    def test_invalid_public_inputs_fail(self) -> None:
        for public in (None, {}, GameEngine(), PublicKB(True), PublicKB(0),
                       PublicKB(3.0), PublicKB(11), PublicKB(3, proved=[]),
                       PublicKB(3, proved={"Z9": CRIMINAL}),
                       PublicKB(3, proved={"A1": UNKNOWN})):
            with self.subTest(public=public), self.assertRaises(ValueError):
                LogicAgent().next_forced(public)

    def test_unknown_classifier_status_is_not_returned_as_a_verdict(self) -> None:
        agent = LogicAgent()
        with patch.object(agent, "_classify_kb", return_value="INVALID"):
            with self.assertRaises(RuntimeError):
                agent.next_forced(PublicKB(3))

    def test_next_forced_builds_and_checks_kb_once_per_scan(self) -> None:
        agent = LogicAgent()
        public = PublicKB(3, (fact("C1", CRIMINAL),))
        with patch.object(Encoder, "build_kb", autospec=True,
                          side_effect=Encoder.build_kb) as build_kb:
            self.assertEqual(agent.next_forced(public), ("C1", CRIMINAL))
        self.assertEqual(build_kb.call_count, 1)
        self.assertEqual([q.assumptions for q in agent.last_queries],
                         [(), (-1,), (1,), (-2,), (2,), (-3,)])
        self.assertEqual(agent.sat_calls, 6)

    def test_timeout_propagates_without_a_choice(self) -> None:
        with self.assertRaises(TimeoutError):
            LogicAgent(timeout=0).next_forced(loaded().get_public_kb())


class AutoSolveTests(unittest.TestCase):
    """Cập nhật KB sau ACCEPTED và dừng ở SOLVED/STUCK/INCONSISTENT."""

    def test_reveal_chain_requires_fresh_kb_at_every_step(self) -> None:
        engine = loaded()
        proxy = PublicEngineProxy(engine)
        agent = LogicAgent()
        entries = agent.auto_solve(proxy)
        cells = board.all_cells(3)
        self.assertEqual(agent.solve_status, SOLVED)
        self.assertEqual([e.cell for e in entries], cells[1:])
        self.assertEqual([e.step for e in entries], list(range(1, 9)))
        self.assertEqual(len(proxy.calls), 8)
        self.assertEqual(len(engine.get_public_kb().proved), 9)
        for entry, before in zip(entries, proxy.before_submit):
            self.assertNotIn(entry.cell, before.proved)
            self.assertEqual(entry.active_clue_ids, [c.id for c in before.revealed_clues])
            expected = check_public_kb(before).classifications[entry.cell]
            self.assertEqual(entry.verdict, expected)

    def test_ambiguous_puzzle_stops_without_guessing_or_revealing(self) -> None:
        engine = loaded(ambiguous_puzzle())
        before = asdict(engine.get_public_kb())
        proxy = PublicEngineProxy(engine)
        agent = LogicAgent()
        self.assertEqual(agent.auto_solve(proxy), [])
        self.assertEqual(agent.solve_status, STUCK)
        self.assertEqual(proxy.calls, [])
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_inconsistent_puzzle_stops_without_submitting(self) -> None:
        data = chain_puzzle()
        data["characters"][0]["clue"] = {"type": "FACT", "target": "A1", "status": INNOCENT}
        engine = loaded(data)
        before = asdict(engine.get_public_kb())
        proxy = PublicEngineProxy(engine)
        agent = LogicAgent()
        self.assertEqual(agent.auto_solve(proxy), [])
        self.assertEqual(agent.solve_status, INCONSISTENT)
        self.assertEqual(proxy.calls, [])
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_partially_solved_then_stuck_returns_only_accepted_steps(self) -> None:
        data = chain_puzzle()
        data["characters"][1]["clue"] = {"type": "FACT", "target": "A1", "status": CRIMINAL}
        engine = loaded(data)
        agent = LogicAgent()
        entries = agent.auto_solve(engine)
        self.assertEqual([(e.cell, e.verdict) for e in entries], [("B1", INNOCENT)])
        self.assertEqual(agent.solve_status, STUCK)
        self.assertEqual(set(engine.get_public_kb().proved), {"A1", "B1"})

    def test_already_solved_state_returns_no_new_steps(self) -> None:
        data = chain_puzzle()
        data["initially_revealed"] = board.all_cells(3)
        proxy = PublicEngineProxy(loaded(data))
        agent = LogicAgent()
        self.assertEqual(agent.auto_solve(proxy), [])
        self.assertEqual(agent.solve_status, SOLVED)
        self.assertEqual(proxy.calls, [])

    def test_all_revealed_but_inconsistent_is_not_reported_solved(self) -> None:
        data = chain_puzzle()
        data["initially_revealed"] = board.all_cells(3)
        data["characters"][0]["clue"] = {"type": "FACT", "target": "A1", "status": INNOCENT}
        agent = LogicAgent()
        self.assertEqual(agent.auto_solve(loaded(data)), [])
        self.assertEqual(agent.solve_status, INCONSISTENT)

    def test_resume_skips_already_proved_cells(self) -> None:
        engine = loaded()
        agent = LogicAgent()
        self.assertEqual(engine.submit_verdict("B1", INNOCENT, agent.classify), ACCEPTED)
        entries = agent.auto_solve(engine)
        self.assertEqual([e.cell for e in entries], board.all_cells(3)[2:])
        self.assertEqual(agent.solve_status, SOLVED)

    def test_agent_can_be_reused_after_stuck_and_solved(self) -> None:
        agent = LogicAgent()
        agent.auto_solve(loaded(ambiguous_puzzle()))
        self.assertEqual(agent.solve_status, STUCK)
        first = agent.auto_solve(loaded())
        second = agent.auto_solve(loaded())
        self.assertEqual(agent.solve_status, SOLVED)
        self.assertEqual([(e.cell, e.verdict) for e in first],
                         [(e.cell, e.verdict) for e in second])
        self.assertGreater(agent.sat_calls, 0)

    def test_rejected_verdict_raises_and_is_not_retried(self) -> None:
        public = PublicKB(3, (fact("A1", CRIMINAL),))
        for response in (NOT_PROVABLE, CONTRADICTED):
            engine = SnapshotEngine(public, public, response)
            agent = LogicAgent()
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                agent.auto_solve(engine)
            self.assertEqual(engine.calls, 1)
            self.assertIsNone(agent.solve_status)

    def test_accepted_without_progress_raises(self) -> None:
        public = PublicKB(3, (fact("A1", CRIMINAL),))
        engine = SnapshotEngine(public, public)
        with self.assertRaisesRegex(RuntimeError, "chưa cập nhật"):
            LogicAgent().auto_solve(engine)
        self.assertEqual(engine.calls, 1)

    def test_accepted_must_not_drop_previously_proved_statuses(self) -> None:
        before = PublicKB(3, (fact("B1", CRIMINAL),), {"A1": CRIMINAL})
        after = PublicKB(3, (fact("B1", CRIMINAL),), {"B1": CRIMINAL})
        engine = SnapshotEngine(before, after)
        with self.assertRaisesRegex(RuntimeError, "làm mất"):
            LogicAgent().auto_solve(engine)
        self.assertEqual(engine.calls, 1)

    def test_board_change_during_submit_raises(self) -> None:
        before = PublicKB(3, (fact("A1", CRIMINAL),))
        after = PublicKB(4, (), {"A1": CRIMINAL})
        with self.assertRaises(RuntimeError):
            LogicAgent().auto_solve(SnapshotEngine(before, after))

    def test_timeout_during_selection_preserves_engine(self) -> None:
        engine = loaded()
        proxy = PublicEngineProxy(engine)
        before = asdict(engine.get_public_kb())
        agent = LogicAgent(timeout=0)
        with self.assertRaises(TimeoutError):
            agent.auto_solve(proxy)
        self.assertEqual(agent.solve_status, TIMEOUT)
        self.assertEqual(proxy.calls, [])
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_engine_callback_is_real_classify_and_timeout_propagates(self) -> None:
        engine = loaded()
        proxy = PublicEngineProxy(engine)
        before = asdict(engine.get_public_kb())
        agent = LogicAgent(timeout=0)
        with patch.object(agent, "next_forced", return_value=("B1", INNOCENT)):
            with self.assertRaises(TimeoutError):
                agent.auto_solve(proxy)
        self.assertEqual(agent.solve_status, TIMEOUT)
        self.assertEqual(proxy.calls, [("B1", INNOCENT)])
        self.assertEqual(asdict(engine.get_public_kb()), before)

    def test_timeout_after_progress_keeps_only_accepted_public_progress(self) -> None:
        engine = loaded()
        agent = LogicAgent()
        original = engine.submit_verdict

        def submit(cell: str, verdict: str, classify: Callable[[PublicKB, str], str]) -> str:
            response = original(cell, verdict, classify)
            agent.timeout = 0
            return response

        with patch.object(engine, "submit_verdict", side_effect=submit) as mock:
            with self.assertRaises(TimeoutError):
                agent.auto_solve(engine)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(agent.solve_status, TIMEOUT)
        self.assertEqual(set(engine.get_public_kb().proved), {"A1", "B1"})

    def test_all_nine_repository_puzzles_solve_with_real_agent(self) -> None:
        for path in sorted(DATA.glob("puzzles_*/*.json")):
            with self.subTest(puzzle=str(path)):
                engine = GameEngine()
                engine.load_puzzle(path)
                before = engine.get_public_kb()
                proxy = PublicEngineProxy(engine)
                agent = LogicAgent(timeout=10)
                entries = agent.auto_solve(proxy)
                final = engine.get_public_kb()
                self.assertEqual(agent.solve_status, SOLVED)
                self.assertEqual(len(final.proved), before.n * before.n)
                self.assertEqual(len(entries), before.n * before.n - len(before.proved))
                self.assertEqual(len({e.cell for e in entries}), len(entries))
                self.assertEqual([(e.cell, e.verdict) for e in entries], proxy.calls)
                for entry in entries:
                    self.assertEqual(final.proved[entry.cell], entry.verdict)
                    self.assertNotIn(entry.verdict, (UNKNOWN, INCONSISTENT))


if __name__ == "__main__":
    unittest.main()
