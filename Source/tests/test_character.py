"""Test cho engine/character.py (việc A3): Character và parse_character."""
import unittest
from dataclasses import FrozenInstanceError
from typing import Optional

from engine.character import Character, parse_character

N = 3


def raw(**overrides) -> dict:
    """Một mục `characters` hợp lệ ở ô B1; ghi đè khóa bằng overrides, giá trị None nghĩa là xóa khóa."""
    data = {
        "cell": "B1",
        "name": "Bea",
        "profession": "Cook",
        "criminal": False,
        "clue": {"type": "SAME_STATUS", "cell1": "A1", "cell2": "C2"},
    }
    for key, value in overrides.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    return data


class CharacterTest(unittest.TestCase):
    def test_holds_only_public_fields(self):
        char = Character("B1", "Bea", "Cook")
        self.assertEqual(set(vars(char)), {"cell", "name", "profession"})
        self.assertFalse(hasattr(char, "criminal"))
        self.assertFalse(hasattr(char, "clue"))

    def test_is_immutable(self):
        char = Character("B1", "Bea", "Cook")
        with self.assertRaises(FrozenInstanceError):
            char.name = "Other"  # type: ignore[misc]

    def test_repr_does_not_leak_secrets(self):
        text = repr(parse_character(raw(criminal=True), N)[0]).lower()
        self.assertNotIn("criminal", text)
        self.assertNotIn("clue", text)


class ParseCharacterValidTest(unittest.TestCase):
    def test_returns_public_part_hidden_label_and_clue(self):
        char, criminal, clue = parse_character(raw(criminal=True), N)
        self.assertEqual(char, Character("B1", "Bea", "Cook"))
        self.assertIs(criminal, True)
        self.assertEqual((clue.id, clue.owner, clue.type), ("clue_B1", "B1", "SAME_STATUS"))
        self.assertEqual(clue.params, {"cell1": "A1", "cell2": "C2"})

    def test_hidden_label_false(self):
        self.assertIs(parse_character(raw(criminal=False), N)[1], False)

    def test_extra_unknown_keys_are_ignored(self):
        char, _, _ = parse_character({**raw(), "note": "x"}, N)
        self.assertEqual(char.cell, "B1")

    def test_clue_without_status_uses_default_later(self):
        clue = parse_character(raw(clue={"type": "EXACTLY",
                                         "region": {"type": "row", "number": 1}, "k": 1}), N)[2]
        self.assertNotIn("status", clue.params)  # loader không ghi đè; clue_status() lo mặc định


class ParseCharacterInvalidTest(unittest.TestCase):
    def assert_invalid(self, data, n: int = N, contains: Optional[str] = None):
        with self.assertRaises(ValueError) as ctx:
            parse_character(data, n)
        if contains is not None:
            self.assertIn(contains, str(ctx.exception))

    def test_not_an_object(self):
        for bad in ("A1", None, 5, [], ["A1"]):
            with self.subTest(data=bad):
                self.assert_invalid(bad)

    def test_missing_required_keys(self):
        for key in ("cell", "name", "profession", "criminal", "clue"):
            with self.subTest(missing=key):
                self.assert_invalid(raw(**{key: None}))

    def test_bad_cell(self):
        for bad in ("D1", "A4", "b1", "B01", "", None, 5):
            with self.subTest(cell=bad):
                self.assert_invalid({**raw(), "cell": bad})

    def test_bad_name_or_profession(self):
        for key in ("name", "profession"):
            for bad in ("", "   ", None, 5):
                with self.subTest(key=key, value=bad):
                    self.assert_invalid({**raw(), key: bad})

    def test_criminal_must_be_bool(self):
        for bad in ("true", "false", 0, 1, None, "CRIMINAL"):
            with self.subTest(criminal=bad):
                self.assert_invalid({**raw(), "criminal": bad})

    def test_clue_must_be_object_with_type(self):
        for bad in ("FACT", None, [], {}, {"cell1": "A1", "cell2": "C2"}):
            with self.subTest(clue=bad):
                self.assert_invalid({**raw(), "clue": bad})

    def test_invalid_clue_error_names_the_character_cell(self):
        bad_k = {"type": "EXACTLY", "region": {"type": "row", "number": 1}, "k": 99}
        self.assert_invalid(raw(clue=bad_k), contains="B1")

    def test_fact_without_status_is_invalid(self):
        self.assert_invalid(raw(clue={"type": "FACT", "target": "A1"}))

    def test_clue_using_old_names_is_invalid(self):
        self.assert_invalid(raw(clue={"type": "SAME", "a": "A1", "b": "C2"}))
        self.assert_invalid(raw(clue={"type": "FACT", "cell": "A1", "status": "CRIMINAL"}))

    def test_cell_checked_against_grid_size(self):
        self.assert_invalid(raw(cell="C3"), n=2)


if __name__ == "__main__":
    unittest.main()