"""Test cho gui/levels.py (quét màn) và gui/progress.py (sao, tiến độ). Không cần Qt."""
import json
import tempfile
import unittest
from pathlib import Path

from gui.levels import PLACES, SEALED_PLACE, discover_levels
from gui.progress import MAX_STARS, Progress, compute_stars, stars_text


def touch(base: Path, rel: str) -> None:
    """Tạo file RỖNG (không phải JSON hợp lệ): việc quét màn không được mở file."""
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


class DiscoverLevelsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data = Path(self._tmp.name)
        for rel in ("puzzles_3x3/p10.json", "puzzles_3x3/p02.json", "puzzles_3x3/p01.json",
                    "puzzles_3x3/bad_ambiguous.json", "puzzles_3x3/sealed/x.json",
                    "puzzles_3x3/.gitkeep", "puzzles_4x4/p01.json", "puzzles_5x5/p01.json",
                    "puzzles_3x4/p01.json", "notes/p01.json", "readme.json"):
            touch(self.data, rel)

    def test_order_is_size_then_normal_then_sealed_with_natural_sort(self):
        keys = [lv.key for lv in discover_levels(self.data)]
        self.assertEqual(keys, [
            "puzzles_3x3/p01.json", "puzzles_3x3/p02.json", "puzzles_3x3/p10.json",
            "puzzles_3x3/bad_ambiguous.json", "puzzles_3x3/sealed/x.json",
            "puzzles_4x4/p01.json", "puzzles_5x5/p01.json",
        ])

    def test_non_square_and_unrelated_folders_are_ignored(self):
        keys = {lv.key for lv in discover_levels(self.data)}
        self.assertNotIn("puzzles_3x4/p01.json", keys)
        self.assertNotIn("notes/p01.json", keys)

    def test_size_comes_from_folder_name(self):
        sizes = {lv.key: lv.n for lv in discover_levels(self.data)}
        self.assertEqual(sizes["puzzles_3x3/p01.json"], 3)
        self.assertEqual(sizes["puzzles_4x4/p01.json"], 4)
        self.assertEqual(sizes["puzzles_5x5/p01.json"], 5)

    def test_sealed_by_prefix_or_subfolder(self):
        sealed = {lv.key for lv in discover_levels(self.data) if lv.sealed}
        self.assertEqual(sealed, {"puzzles_3x3/bad_ambiguous.json", "puzzles_3x3/sealed/x.json"})

    def test_numbers_titles_tags_and_places(self):
        levels = {lv.key: lv for lv in discover_levels(self.data)}
        p10 = levels["puzzles_3x3/p10.json"]
        self.assertEqual((p10.number, p10.title, p10.tag, p10.code), (10, "Vụ án #10", "#10", "P10"))
        bad = levels["puzzles_3x3/bad_ambiguous.json"]
        self.assertEqual((bad.title, bad.tag, bad.place), ("Hồ sơ niêm phong", "NIÊM PHONG", SEALED_PLACE))
        normal_places = [lv.place for lv in levels.values() if not lv.sealed]
        self.assertEqual(normal_places, [PLACES[i] for i in range(len(normal_places))])

    def test_missing_directory_gives_empty_list(self):
        self.assertEqual(discover_levels(self.data / "nope"), [])

    def test_real_data_directory_has_levels_when_present(self):
        real = Path(__file__).resolve().parents[1] / "data"
        for level in discover_levels(real):
            self.assertTrue(level.path.is_file())
            self.assertGreaterEqual(level.n, 3)


class StarsTest(unittest.TestCase):
    def test_compute_stars(self):
        self.assertEqual(compute_stars(0, 0, False), 3)
        self.assertEqual(compute_stars(1, 0, False), 2)
        self.assertEqual(compute_stars(0, 2, False), 2)
        self.assertEqual(compute_stars(2, 5, False), 1)
        self.assertEqual(compute_stars(0, 0, True), 1)

    def test_stars_text(self):
        self.assertEqual(stars_text(2), "★★☆")
        self.assertEqual(stars_text(0), "☆☆☆")
        self.assertEqual(stars_text(99), "★" * MAX_STARS)


class ProgressTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "progress.json"

    def test_record_keeps_best_and_persists(self):
        progress = Progress(self.path)
        self.assertEqual(progress.stars("puzzles_3x3/p01.json"), 0)
        self.assertEqual(progress.record("puzzles_3x3/p01.json", 2), 2)
        self.assertEqual(progress.record("puzzles_3x3/p01.json", 1), 2)    # không tụt sao
        self.assertEqual(progress.record("puzzles_3x3/p01.json", 3), 3)
        again = Progress(self.path)
        self.assertEqual(again.stars("puzzles_3x3/p01.json"), 3)
        self.assertTrue(again.is_cleared("puzzles_3x3/p01.json"))

    def test_corrupt_or_invalid_file_is_ignored(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(Progress(self.path).stars("a"), 0)
        self.path.write_text(json.dumps({"cleared": {"a": 2, "b": 9, "c": True, "d": "3"}}),
                             encoding="utf-8")
        progress = Progress(self.path)
        self.assertEqual((progress.stars("a"), progress.stars("b"), progress.stars("c"),
                          progress.stars("d")), (2, 0, 0, 0))

    def test_reset_clears_everything(self):
        progress = Progress(self.path)
        progress.record("a", 3)
        progress.reset()
        self.assertEqual(Progress(self.path).stars("a"), 0)

    def test_unwritable_location_does_not_raise(self):
        blocker = Path(self._tmp.name) / "file"
        blocker.write_text("x", encoding="utf-8")
        progress = Progress(blocker / "progress.json")      # cha là file nên không ghi được
        self.assertEqual(progress.record("a", 2), 2)
        self.assertFalse(progress.save())


if __name__ == "__main__":
    unittest.main()
