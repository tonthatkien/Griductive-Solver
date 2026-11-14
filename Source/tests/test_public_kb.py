"""Test cho PublicKB / get_public_kb (việc A4): ranh giới Engine / Agent, không rò thông tin."""
import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

from engine.clue import Clue
from engine.constants import CRIMINAL, INNOCENT
from engine.game_state import GameEngine, PublicKB

P01_PATH = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"
ALL_CELLS = ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"]


def loaded_engine() -> GameEngine:
    engine = GameEngine()
    engine.load_puzzle(P01_PATH)
    return engine


def contains_engine(value, seen=None) -> bool:
    """True nếu đâu đó trong `value` (đệ quy) có một GameEngine."""
    seen = seen if seen is not None else set()
    if id(value) in seen:
        return False
    seen.add(id(value))
    if isinstance(value, GameEngine):
        return True
    if isinstance(value, dict):
        return any(contains_engine(v, seen) for v in list(value.keys()) + list(value.values()))
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(contains_engine(v, seen) for v in value)
    if hasattr(value, "__dict__"):
        return contains_engine(vars(value), seen)
    return False


class PublicKBShapeTest(unittest.TestCase):
    def test_has_exactly_n_revealed_clues_and_proved(self):
        self.assertEqual([f.name for f in fields(PublicKB)], ["n", "revealed_clues", "proved"])
        kb = loaded_engine().get_public_kb()
        self.assertEqual(set(vars(kb)), {"n", "revealed_clues", "proved"})

    def test_values_are_plain_public_data(self):
        kb = loaded_engine().get_public_kb()
        self.assertEqual(kb.n, 3)
        self.assertIsInstance(kb.revealed_clues, tuple)
        self.assertTrue(all(isinstance(c, Clue) for c in kb.revealed_clues))
        self.assertEqual(kb.proved, {"A1": CRIMINAL, "C1": INNOCENT})

    def test_is_frozen(self):
        kb = loaded_engine().get_public_kb()
        with self.assertRaises(FrozenInstanceError):
            kb.n = 9  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            kb.proved = {}  # type: ignore[misc]

    def test_before_load_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            GameEngine().get_public_kb()


class NoLeakTest(unittest.TestCase):
    def test_only_revealed_cells_appear_in_proved_and_clues(self):
        engine = loaded_engine()
        kb = engine.get_public_kb()
        hidden = [c for c in ALL_CELLS if not engine.is_revealed(c)]
        self.assertEqual(len(hidden), 7)
        for cell in hidden:
            with self.subTest(cell=cell):
                self.assertNotIn(cell, kb.proved)
                self.assertNotIn(cell, [c.owner for c in kb.revealed_clues])
                self.assertNotIn(f"clue_{cell}", [c.id for c in kb.revealed_clues])

    def test_proved_and_clues_cover_exactly_the_revealed_cells(self):
        engine = loaded_engine()
        engine._revealed.update({"B2", "C3"})  # giả lập lật thẻ; A5 sẽ thay bằng submit_verdict
        kb = engine.get_public_kb()
        self.assertEqual(list(kb.proved), engine.revealed_cells)  # cùng thứ tự row-major
        self.assertEqual([c.owner for c in kb.revealed_clues], engine.revealed_cells)

    def test_proved_values_match_hidden_labels_only_for_revealed_cells(self):
        engine = loaded_engine()
        engine._revealed.add("B2")
        kb = engine.get_public_kb()
        self.assertEqual(kb.proved["B2"], CRIMINAL)   # Eliza là criminal
        self.assertEqual(kb.proved["A1"], CRIMINAL)
        self.assertEqual(kb.proved["C1"], INNOCENT)

    def test_does_not_reference_the_engine(self):
        engine = loaded_engine()
        kb = engine.get_public_kb()
        self.assertFalse(contains_engine(kb))
        self.assertTrue(contains_engine([kb, engine]))  # chính bộ dò này phải bắt được engine

    def test_unrevealed_secrets_not_reachable_through_the_kb_object_graph(self):
        engine = loaded_engine()
        kb = engine.get_public_kb()
        # Nhãn ẩn và clue chưa lật nằm ở engine; KB không được trỏ tới cùng object với engine.
        engine_clues = {id(c) for c in engine._clues.values()}
        engine_param_dicts = {id(c.params) for c in engine._clues.values()}
        for clue in kb.revealed_clues:
            self.assertNotIn(id(clue), engine_clues)
            self.assertNotIn(id(clue.params), engine_param_dicts)
        self.assertIsNot(kb.proved, engine._labels)


class IsolationTest(unittest.TestCase):
    def test_mutating_kb_does_not_change_engine(self):
        engine = loaded_engine()
        kb = engine.get_public_kb()
        kb.proved["B2"] = INNOCENT                         # thêm ô chưa lật
        kb.proved["A1"] = INNOCENT                         # sửa ô đã lật
        kb.revealed_clues[0].params["target"] = "C3"       # sửa clue của Agent
        fresh = engine.get_public_kb()
        self.assertEqual(fresh.proved, {"A1": CRIMINAL, "C1": INNOCENT})
        self.assertEqual(fresh.revealed_clues[0].params["target"], "B2")
        self.assertEqual(engine._labels["A1"], CRIMINAL)
        self.assertEqual(engine._clues["A1"].params["target"], "B2")

    def test_each_call_returns_an_independent_equal_copy(self):
        engine = loaded_engine()
        kb1, kb2 = engine.get_public_kb(), engine.get_public_kb()
        self.assertEqual(kb1, kb2)
        self.assertIsNot(kb1, kb2)
        self.assertIsNot(kb1.proved, kb2.proved)
        self.assertIsNot(kb1.revealed_clues[0], kb2.revealed_clues[0])
        self.assertIsNot(kb1.revealed_clues[0].params, kb2.revealed_clues[0].params)

    def test_earlier_snapshot_is_not_updated_by_later_reveals(self):
        engine = loaded_engine()
        before = engine.get_public_kb()
        engine._revealed.add("B2")
        after = engine.get_public_kb()
        self.assertEqual(sorted(before.proved), ["A1", "C1"])
        self.assertEqual(sorted(after.proved), ["A1", "B2", "C1"])

    def test_kb_can_be_deep_copied_and_survives_restart(self):
        engine = loaded_engine()
        engine._revealed.add("B2")
        kb = engine.get_public_kb()
        clone = deepcopy(kb)
        engine.restart()
        self.assertEqual(clone, kb)
        self.assertEqual(sorted(kb.proved), ["A1", "B2", "C1"])  # snapshot cũ không đổi sau restart
        self.assertEqual(sorted(engine.get_public_kb().proved), ["A1", "C1"])


class AgentBoundaryTest(unittest.TestCase):
    def test_engine_has_no_hidden_label_or_clue_in_public_surface(self):
        engine = loaded_engine()
        public = [name for name in dir(engine) if not name.startswith("_")]
        for name in public:
            self.assertNotIn("criminal", name.lower())
            self.assertNotIn("label", name.lower())
        self.assertNotIn("clues", public)  # chỉ có get_public_kb(), không có getter clue chưa lật

    def test_characters_property_leaks_nothing_hidden(self):
        engine = loaded_engine()
        for char in engine.characters:
            self.assertEqual(set(vars(char)), {"cell", "name", "profession"})


if __name__ == "__main__":
    unittest.main()