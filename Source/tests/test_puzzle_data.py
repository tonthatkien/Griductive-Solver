"""Test nạp toàn bộ puzzle trong data/puzzles_*/*.json.

Không gọi brute_force nên bao phủ được cả 5x5; chỉ kiểm tra file parse
được, nạp qua GameEngine.load_puzzle và cấu trúc khớp với n.
"""
from __future__ import annotations

import glob
import json
import unittest
from pathlib import Path

from engine.game_state import GameEngine

# Source/ is the working directory when unittest runs with `-t .`.
_PUZZLE_GLOB = "data/puzzles_*/*.json"


def _puzzle_paths() -> list[str]:
    return sorted(glob.glob(_PUZZLE_GLOB))


class TestPuzzleDataLoads(unittest.TestCase):
    """Every shipped puzzle must load and expose a consistent board."""

    def test_puzzle_files_exist(self) -> None:
        paths = _puzzle_paths()
        self.assertGreaterEqual(
            len(paths), 9, f"Expected >= 9 puzzles, found {len(paths)}: {paths}"
        )

    def test_each_size_has_at_least_three_puzzles(self) -> None:
        for size in (3, 4, 5):
            with self.subTest(size=size):
                paths = sorted(glob.glob(f"data/puzzles_{size}x{size}/*.json"))
                self.assertGreaterEqual(
                    len(paths),
                    3,
                    f"Expected at least 3 puzzles for {size}x{size}, found {paths}",
                )

    def test_all_puzzles_load(self) -> None:
        paths = _puzzle_paths()
        self.assertTrue(paths, "No puzzle files found")
        for path in paths:
            with self.subTest(puzzle=path):
                engine = GameEngine()
                engine.load_puzzle(path)

    def test_json_shape_matches_size(self) -> None:
        for path in _puzzle_paths():
            with self.subTest(puzzle=path):
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                n = data["n"]
                self.assertIn(n, (3, 4, 5), f"{path}: unexpected n={n}")
                # Board is n*n cells; every character declares a clue.
                self.assertEqual(len(data["characters"]), n * n, path)
                cells = {c["cell"] for c in data["characters"]}
                self.assertEqual(len(cells), n * n, f"{path}: duplicate cells")
                for cell in data["initially_revealed"]:
                    self.assertIn(cell, cells, f"{path}: unknown reveal {cell}")


if __name__ == "__main__":
    unittest.main()