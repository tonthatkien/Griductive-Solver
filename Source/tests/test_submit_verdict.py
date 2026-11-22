"""Test cho GameEngine.submit_verdict (việc A5): ACCEPTED / NOT_PROVABLE / CONTRADICTED.

NOTE(E1): LogicAgent.classify chưa có, nên các test dưới dùng classify GIẢ (`fixed`,
`oracle`, `Recorder`). Khi E1 xong và có trên main, bỏ comment khối "Test tích hợp" ở cuối
file để chạy engine + Encoder + DPLL + agent thật, rồi có thể giảm bớt phụ thuộc vào classify giả.
"""
import unittest
from pathlib import Path
from typing import Callable, List, Tuple

from engine.constants import (
    ACCEPTED,
    CONTRADICTED,
    CRIMINAL,
    INCONSISTENT,
    INNOCENT,
    NOT_PROVABLE,
    UNKNOWN,
)
from engine.game_state import GameEngine, PublicKB

P01_PATH = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"

# Nghiệm thật của p01 (nhãn ẩn): criminal = A1, B2, C2, C3.
P01_LABELS = {
    "A1": CRIMINAL, "B1": INNOCENT, "C1": INNOCENT,
    "A2": INNOCENT, "B2": CRIMINAL, "C2": CRIMINAL,
    "A3": INNOCENT, "B3": INNOCENT, "C3": CRIMINAL,
}


def loaded_engine() -> GameEngine:
    engine = GameEngine()
    engine.load_puzzle(P01_PATH)
    return engine


# ---------------------------------------------------------------- classify GIẢ
def fixed(value) -> Callable[[PublicKB, str], str]:
    """classify giả: luôn trả `value`, bất kể KB và ô."""
    return lambda kb, cell: value


def oracle(kb: PublicKB, cell: str) -> str:
    """classify giả 'toàn tri': trả đúng nhãn thật (tra bảng P01_LABELS), không suy luận gì."""
    return P01_LABELS[cell]


class Recorder:
    """classify giả ghi lại các lần gọi, để kiểm tra engine đưa gì cho Agent."""

    def __init__(self, result: str = UNKNOWN):
        self.result = result
        self.calls: List[Tuple[object, str]] = []

    def __call__(self, kb, cell):
        self.calls.append((kb, cell))
        return self.result


def snapshot(engine: GameEngine):
    return engine.revealed_cells, engine.get_public_kb()


class AcceptedTest(unittest.TestCase):
    def test_accepted_flips_card_and_reveals_clue(self):
        engine = loaded_engine()
        self.assertEqual(engine.submit_verdict("B2", CRIMINAL, fixed(CRIMINAL)), ACCEPTED)
        self.assertTrue(engine.is_revealed("B2"))
        kb = engine.get_public_kb()
        self.assertEqual(kb.proved["B2"], CRIMINAL)
        self.assertIn("B2", [c.owner for c in kb.revealed_clues])
        self.assertEqual(engine.revealed_cells, ["A1", "C1", "B2"])

    def test_accepted_for_innocent_cell(self):
        engine = loaded_engine()
        self.assertEqual(engine.submit_verdict("B1", INNOCENT, fixed(INNOCENT)), ACCEPTED)
        self.assertEqual(engine.get_public_kb().proved["B1"], INNOCENT)

    def test_returned_constants_are_the_contract_strings(self):
        self.assertEqual((ACCEPTED, NOT_PROVABLE, CONTRADICTED),
                         ("ACCEPTED", "NOT_PROVABLE", "CONTRADICTED"))

    def test_only_the_submitted_cell_is_flipped(self):
        engine = loaded_engine()
        engine.submit_verdict("B2", CRIMINAL, fixed(CRIMINAL))
        for cell in ("A2", "B1", "B3", "C2", "C3", "A3"):
            self.assertFalse(engine.is_revealed(cell), cell)

    def test_full_solve_with_oracle_reveals_every_card(self):
        engine = loaded_engine()
        # Thứ tự lật theo cách suy luận của p01 (B2, C2, C3 -> B1, B3 -> A3 -> A2)
        for cell in ("B2", "C2", "C3", "B1", "B3", "A3", "A2"):
            with self.subTest(cell=cell):
                self.assertEqual(engine.submit_verdict(cell, P01_LABELS[cell], oracle), ACCEPTED)
        self.assertEqual(len(engine.revealed_cells), 9)
        self.assertEqual(engine.get_public_kb().proved, P01_LABELS)
        self.assertEqual(len(engine.get_public_kb().revealed_clues), 9)


class NotProvableTest(unittest.TestCase):
    def test_unknown_gives_not_provable_and_keeps_state(self):
        engine = loaded_engine()
        before = snapshot(engine)
        for verdict in (CRIMINAL, INNOCENT):
            with self.subTest(verdict=verdict):
                self.assertEqual(engine.submit_verdict("A3", verdict, fixed(UNKNOWN)),
                                 NOT_PROVABLE)
        self.assertEqual(snapshot(engine), before)
        self.assertFalse(engine.is_revealed("A3"))

    def test_not_provable_even_if_submitted_verdict_is_actually_true(self):
        # Đoán đúng nhãn thật nhưng Agent chưa chứng minh được -> vẫn NOT_PROVABLE.
        engine = loaded_engine()
        self.assertEqual(engine.submit_verdict("A3", INNOCENT, fixed(UNKNOWN)), NOT_PROVABLE)
        self.assertFalse(engine.is_revealed("A3"))


class ContradictedTest(unittest.TestCase):
    def test_opposite_verdict_is_contradicted_and_keeps_state(self):
        engine = loaded_engine()
        before = snapshot(engine)
        self.assertEqual(engine.submit_verdict("B1", CRIMINAL, fixed(INNOCENT)), CONTRADICTED)
        self.assertEqual(engine.submit_verdict("B2", INNOCENT, fixed(CRIMINAL)), CONTRADICTED)
        self.assertEqual(snapshot(engine), before)
        self.assertFalse(engine.is_revealed("B1"))
        self.assertFalse(engine.is_revealed("B2"))

    def test_contradicted_does_not_block_a_later_correct_submit(self):
        engine = loaded_engine()
        self.assertEqual(engine.submit_verdict("B2", INNOCENT, oracle), CONTRADICTED)
        self.assertEqual(engine.submit_verdict("B2", CRIMINAL, oracle), ACCEPTED)


class ClassifyContractViolationTest(unittest.TestCase):
    """Bắt bug: classify vi phạm hợp đồng thì ném AssertionError và KHÔNG đổi state."""

    def assert_bug(self, classify, cell="B2", verdict=CRIMINAL):
        engine = loaded_engine()
        before = snapshot(engine)
        with self.assertRaises(AssertionError):
            engine.submit_verdict(cell, verdict, classify)
        self.assertEqual(snapshot(engine), before)
        self.assertFalse(engine.is_revealed(cell))

    def test_proved_verdict_that_contradicts_hidden_label(self):
        # B2 thật là CRIMINAL; classify 'chứng minh' INNOCENT là suy luận sai.
        self.assert_bug(fixed(INNOCENT), "B2", CRIMINAL)  # sẽ là CONTRADICTED nếu tin classify
        self.assert_bug(fixed(INNOCENT), "B2", INNOCENT)  # sẽ là ACCEPTED nếu tin classify
        self.assert_bug(fixed(CRIMINAL), "B1", CRIMINAL)  # B1 thật là INNOCENT

    def test_inconsistent_kb(self):
        self.assert_bug(fixed(INCONSISTENT))

    def test_garbage_return_values(self):
        for bad in ("MAYBE", "criminal", "", None, 0, ["CRIMINAL"]):
            with self.subTest(value=bad):
                self.assert_bug(fixed(bad))


class InputValidationTest(unittest.TestCase):
    def assert_rejected_before_classify(self, cell, verdict, exc=ValueError):
        engine = loaded_engine()
        rec = Recorder()
        before = snapshot(engine)
        with self.assertRaises(exc):
            engine.submit_verdict(cell, verdict, rec)
        self.assertEqual(rec.calls, [])  # không gọi Agent với input rác
        self.assertEqual(snapshot(engine), before)

    def test_invalid_cell(self):
        for bad in ("D1", "A4", "a1", "A01", "", None, 5):
            with self.subTest(cell=bad):
                self.assert_rejected_before_classify(bad, CRIMINAL)

    def test_invalid_verdict(self):
        for bad in (UNKNOWN, INCONSISTENT, "criminal", "", None, True):
            with self.subTest(verdict=bad):
                self.assert_rejected_before_classify("B2", bad)

    def test_already_revealed_cell(self):
        for cell in ("A1", "C1"):  # face-up ban đầu
            with self.subTest(cell=cell):
                self.assert_rejected_before_classify(cell, CRIMINAL)

    def test_cell_revealed_by_earlier_accept_cannot_be_submitted_again(self):
        engine = loaded_engine()
        engine.submit_verdict("B2", CRIMINAL, oracle)
        with self.assertRaises(ValueError):
            engine.submit_verdict("B2", CRIMINAL, oracle)

    def test_before_load_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            GameEngine().submit_verdict("B2", CRIMINAL, fixed(CRIMINAL))


class EngineAgentBoundaryTest(unittest.TestCase):
    def test_classify_receives_a_public_kb_and_the_cell_not_the_engine(self):
        engine = loaded_engine()
        rec = Recorder(UNKNOWN)
        engine.submit_verdict("B2", CRIMINAL, rec)
        self.assertEqual(len(rec.calls), 1)
        kb, cell = rec.calls[0]
        self.assertIsInstance(kb, PublicKB)
        self.assertNotIsInstance(kb, GameEngine)
        self.assertEqual(cell, "B2")

    def test_kb_given_to_classify_hides_the_target_cell(self):
        engine = loaded_engine()
        rec = Recorder(UNKNOWN)
        engine.submit_verdict("B2", CRIMINAL, rec)
        kb, _ = rec.calls[0]
        self.assertNotIn("B2", kb.proved)
        self.assertNotIn("B2", [c.owner for c in kb.revealed_clues])
        self.assertEqual(sorted(kb.proved), ["A1", "C1"])

    def test_classify_cannot_corrupt_the_engine_by_mutating_its_kb(self):
        engine = loaded_engine()

        def evil(kb, cell):
            kb.proved["B2"] = INNOCENT
            kb.proved["A1"] = INNOCENT
            kb.revealed_clues[0].params["target"] = "C3"
            return UNKNOWN

        self.assertEqual(engine.submit_verdict("B2", CRIMINAL, evil), NOT_PROVABLE)
        fresh = engine.get_public_kb()
        self.assertEqual(fresh.proved, {"A1": CRIMINAL, "C1": INNOCENT})
        self.assertEqual(fresh.revealed_clues[0].params["target"], "B2")

    def test_exception_from_classify_propagates_and_keeps_state(self):
        engine = loaded_engine()
        before = snapshot(engine)

        def boom(kb, cell):
            raise RuntimeError("agent crashed")

        with self.assertRaises(RuntimeError):
            engine.submit_verdict("B2", CRIMINAL, boom)
        self.assertEqual(snapshot(engine), before)

    def test_new_clue_appears_in_the_next_kb_given_to_classify(self):
        engine = loaded_engine()
        engine.submit_verdict("B2", CRIMINAL, oracle)
        rec = Recorder(UNKNOWN)
        engine.submit_verdict("C2", CRIMINAL, rec)
        kb, _ = rec.calls[0]
        self.assertEqual(sorted(kb.proved), ["A1", "B2", "C1"])
        self.assertIn("B2", [c.owner for c in kb.revealed_clues])


class RestartAfterSubmitTest(unittest.TestCase):
    def test_restart_undoes_accepted_submits(self):
        engine = loaded_engine()
        engine.submit_verdict("B2", CRIMINAL, oracle)
        engine.submit_verdict("C2", CRIMINAL, oracle)
        engine.restart()
        self.assertEqual(engine.revealed_cells, ["A1", "C1"])
        self.assertEqual(engine.get_public_kb().proved, {"A1": CRIMINAL, "C1": INNOCENT})
        # sau restart nộp lại được
        self.assertEqual(engine.submit_verdict("B2", CRIMINAL, oracle), ACCEPTED)


# ---------------------------------------------------------------------------------
# Test tích hợp (BẬT khi E1 `LogicAgent.classify` có trên main)
#
# NOTE(E1): đang comment vì chưa có logic/agent.py. Khi có thì bỏ comment cả khối này
# (và dòng import), chạy lại; kết quả mong đợi dựa trên p01: từ hai thẻ face-up A1, C1
# thì B2, C2, C3 là CRIMINAL suy ra được (A1: B2 criminal; C1: cột C có đúng 2 criminal
# mà C1 innocent), còn A3 thì chưa chứng minh được ở trạng thái ban đầu.
#
# from logic.agent import LogicAgent
#
#
# class RealAgentIntegrationTest(unittest.TestCase):
#     def test_agent_proves_first_wave_from_initial_cards(self):
#         engine = loaded_engine()
#         classify = LogicAgent().classify
#         for cell in ("B2", "C2", "C3"):
#             with self.subTest(cell=cell):
#                 self.assertEqual(engine.submit_verdict(cell, CRIMINAL, classify), ACCEPTED)
#
#     def test_agent_cannot_prove_a3_at_the_start(self):
#         engine = loaded_engine()
#         self.assertEqual(
#             engine.submit_verdict("A3", INNOCENT, LogicAgent().classify), NOT_PROVABLE
#         )
#
#     def test_agent_contradicts_wrong_verdict(self):
#         engine = loaded_engine()
#         self.assertEqual(
#             engine.submit_verdict("B2", INNOCENT, LogicAgent().classify), CONTRADICTED
#         )


if __name__ == "__main__":
    unittest.main()