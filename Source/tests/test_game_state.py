"""Test cho engine/character.py + engine/game_state.py (việc A3): load_puzzle, restart."""
import json
import tempfile
import unittest
import ast
from copy import deepcopy
from pathlib import Path
from engine import board
from engine.character import Character
from engine.game_state import CRIMINAL, INNOCENT, GameEngine, PublicKB

P01_PATH = Path(__file__).resolve().parents[1] / "data" / "puzzles_3x3" / "p01.json"


def p01() -> dict:
    with P01_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def loaded_engine() -> GameEngine:
    engine = GameEngine()
    engine.load_puzzle(P01_PATH)
    return engine


class LoadPuzzleTest(unittest.TestCase):
    def test_load_from_path_str_and_dict(self):
        for source in (P01_PATH, str(P01_PATH), p01()):
            with self.subTest(source=type(source).__name__):
                engine = GameEngine()
                engine.load_puzzle(source)
                self.assertEqual(engine.n, 3)
                self.assertEqual(len(engine.characters), 9)

    def test_characters_are_public_and_row_major(self):
        engine = loaded_engine()
        self.assertEqual([c.cell for c in engine.characters],
                         ["A1", "B1", "C1", "A2", "B2", "C2", "A3", "B3", "C3"])
        cells = [c.cell for c in engine.characters]
        self.assertEqual(cells, board.all_cells(engine.n))

    def test_characters_in_shuffled_order_are_sorted_on_load(self):
        data = p01()
        data["characters"].reverse()
        engine = GameEngine()
        engine.load_puzzle(data)
        self.assertEqual(engine.characters[0].cell, "A1")
        self.assertEqual(engine.characters[-1].cell, "C3")

    def test_loading_dict_does_not_alias_caller_data(self):
        data = p01()
        engine = GameEngine()
        engine.load_puzzle(data)
        data["characters"][0]["clue"]["target"] = "C3"
        self.assertEqual(engine.get_public_kb().revealed_clues[0].params["target"], "B2")

    def test_methods_before_load_raise_runtime_error(self):
        engine = GameEngine()
        for call in (engine.restart, engine.get_public_kb, lambda: engine.n,
                     lambda: engine.is_revealed("A1")):
            with self.subTest(call=call):
                with self.assertRaises(RuntimeError):
                    call()


class InitialStateTest(unittest.TestCase):
    def test_initially_revealed_cards_are_face_up(self):
        engine = loaded_engine()
        self.assertEqual(engine.revealed_cells, ["A1", "C1"])
        self.assertTrue(engine.is_revealed("A1"))
        self.assertFalse(engine.is_revealed("B2"))

    def test_public_kb_has_revealed_clues_and_proved_only(self):
        kb = loaded_engine().get_public_kb()
        self.assertIsInstance(kb, PublicKB)
        self.assertEqual(kb.n, 3)
        self.assertEqual(kb.proved, {"A1": CRIMINAL, "C1": INNOCENT})
        self.assertEqual([c.owner for c in kb.revealed_clues], ["A1", "C1"])
        self.assertEqual([c.type for c in kb.revealed_clues], ["FACT", "EXACTLY"])

    def test_hidden_labels_and_unrevealed_clues_are_not_exposed(self):
        engine = loaded_engine()
        self.assertEqual(set(vars(engine.characters[0])), {"cell", "name", "profession"})
        kb = engine.get_public_kb()
        self.assertNotIn("B2", kb.proved)
        self.assertNotIn("B2", [c.owner for c in kb.revealed_clues])


NOISE_TEXT = "Tôi thích trồng hoa."


def p01_with_noise(cell: str = "B2") -> dict:
    """p01 mà thẻ ở `cell` được thay bằng clue NOISE (chỉ để test nạp/lật thẻ)."""
    data = p01()
    for character in data["characters"]:
        if character["cell"] == cell:
            character["clue"] = {"type": "NOISE", "text": NOISE_TEXT}
    return data


class NoiseCardTest(unittest.TestCase):
    def test_puzzle_with_noise_card_loads(self):
        engine = GameEngine()
        engine.load_puzzle(p01_with_noise())
        self.assertEqual(len(engine.characters), 9)

    def test_face_down_noise_card_is_not_in_public_kb(self):
        engine = GameEngine()
        engine.load_puzzle(p01_with_noise())
        kb = engine.get_public_kb()
        self.assertNotIn("B2", [c.owner for c in kb.revealed_clues])
        self.assertNotIn("B2", kb.proved)

    def test_flipped_noise_card_reaches_public_kb_with_its_text(self):
        engine = GameEngine()
        engine.load_puzzle(p01_with_noise())
        engine._revealed.add("B2")  # giả lập lật thẻ, giống các test khác trong file
        kb = engine.get_public_kb()
        clue = next(c for c in kb.revealed_clues if c.owner == "B2")
        self.assertEqual((clue.type, clue.params), ("NOISE", {"text": NOISE_TEXT}))
        self.assertEqual(kb.proved["B2"], CRIMINAL)

    def test_noise_card_without_text_is_rejected(self):
        data = p01_with_noise()
        for character in data["characters"]:
            if character["cell"] == "B2":
                character["clue"].pop("text")
        with self.assertRaises(ValueError):
            GameEngine().load_puzzle(data)


class RestartTest(unittest.TestCase):
    def test_restart_returns_to_initial_state(self):
        engine = loaded_engine()
        engine._revealed.update({"B2", "C2"})  # giả lập lật thẻ; A4 sẽ thay bằng flip thật
        self.assertEqual(len(engine.revealed_cells), 4)
        engine.restart()
        self.assertEqual(engine.revealed_cells, ["A1", "C1"])
        self.assertEqual(engine.get_public_kb().proved, {"A1": CRIMINAL, "C1": INNOCENT})

    def test_load_puzzle_resets_previous_game(self):
        engine = loaded_engine()
        engine._revealed.add("B2")
        engine.load_puzzle(P01_PATH)
        self.assertEqual(engine.revealed_cells, ["A1", "C1"])

    def test_failed_load_keeps_previous_game(self):
        engine = loaded_engine()
        bad = p01()
        bad["initially_revealed"] = []
        with self.assertRaises(ValueError):
            engine.load_puzzle(bad)
        self.assertEqual(engine.n, 3)
        self.assertEqual(engine.revealed_cells, ["A1", "C1"])


class InvalidPuzzleTest(unittest.TestCase):
    def assert_invalid(self, mutate):
        data = p01()
        mutate(data)
        with self.assertRaises(ValueError):
            GameEngine().load_puzzle(data)

    def test_bad_n(self):
        for bad in (None, "3", 0, -1, True, 3.0):
            with self.subTest(n=bad):
                self.assert_invalid(lambda d, b=bad: d.__setitem__("n", b))

    def test_missing_n_or_characters(self):
        self.assert_invalid(lambda d: d.pop("n"))
        self.assert_invalid(lambda d: d.pop("characters"))

    def test_wrong_number_of_characters(self):
        self.assert_invalid(lambda d: d["characters"].pop())
        self.assert_invalid(lambda d: d["characters"].append(deepcopy(d["characters"][0])))

    def test_duplicate_cell(self):
        self.assert_invalid(lambda d: d["characters"][1].__setitem__("cell", "A1"))

    def test_cell_outside_grid(self):
        self.assert_invalid(lambda d: d["characters"][0].__setitem__("cell", "D1"))

    def test_names_not_increasing_row_major(self):
        self.assert_invalid(lambda d: d["characters"][1].__setitem__("name", "Aaron"))

    def test_duplicate_names(self):
        self.assert_invalid(lambda d: d["characters"][1].__setitem__("name", "Abel"))

    def test_missing_or_bad_character_fields(self):
        for key in ("cell", "name", "profession", "criminal", "clue"):
            with self.subTest(missing=key):
                self.assert_invalid(lambda d, k=key: d["characters"][2].pop(k))
        for key, bad in (("criminal", "true"), ("criminal", 1), ("name", ""),
                         ("profession", None), ("clue", "FACT")):
            with self.subTest(key=key, bad=bad):
                self.assert_invalid(lambda d, k=key, b=bad: d["characters"][2].__setitem__(k, b))

    def test_clue_without_type_or_invalid(self):
        self.assert_invalid(lambda d: d["characters"][0]["clue"].pop("type"))
        self.assert_invalid(lambda d: d["characters"][4]["clue"].__setitem__("k", 99))
        self.assert_invalid(lambda d: d["characters"][0]["clue"].pop("status"))  # FACT bắt buộc status

    def test_clue_using_old_key_names_is_rejected(self):
        self.assert_invalid(lambda d: d["characters"][0].__setitem__(
            "clue", {"type": "FACT", "cell": "B2", "status": "CRIMINAL"}))

    def test_initially_revealed_rules(self):
        for bad in ([], None, ["A1", "A1"], ["D4"], ["a1"], "A1"):
            with self.subTest(initially_revealed=bad):
                self.assert_invalid(lambda d, b=bad: d.__setitem__("initially_revealed", b))
        self.assert_invalid(lambda d: d.pop("initially_revealed"))


class ParseSourceTest(unittest.TestCase):
    def test_invalid_json_file_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                GameEngine().load_puzzle(path)

    def test_json_root_must_be_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                GameEngine().load_puzzle(path)

    def test_missing_file_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            GameEngine().load_puzzle("does_not_exist.json")


class ConstantsTest(unittest.TestCase):
    def test_game_state_reexports_shared_constants(self):
        from engine import constants
        self.assertIs(CRIMINAL, constants.CRIMINAL)
        self.assertIs(INNOCENT, constants.INNOCENT)


if __name__ == "__main__":
    unittest.main()