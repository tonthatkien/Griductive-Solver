"""Test GameEngine trên bộ puzzle thật trong data.

Các test đơn lẻ nằm ở file khác: load/restart ở test_game_state.py, submit_verdict ở
test_submit_verdict.py, PublicKB ở test_public_kb.py (đều dùng p01 3x3). File này chạy engine
trên MỌI puzzle puzzles_3x3 / 4x4 / 5x5, và đọc nhãn ẩn thẳng từ file JSON (không chạm
engine._labels) nên độc lập với engine.
"""
import json
import unittest
from pathlib import Path
from typing import Callable, Dict, List

from engine import board
from engine.constants import (
    ACCEPTED,
    CONTRADICTED,
    CRIMINAL,
    INCONSISTENT,
    INNOCENT,
    NOT_PROVABLE,
    UNKNOWN,
)
from engine.game_state import GameEngine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
# Puzzle chính: puzzles_NxN/pXX.json. Puzzle lỗi để demo (bad_*, thư mục con) không bị lẫn vào.
PUZZLE_PATHS = sorted(DATA_DIR.glob("puzzles_*x*/p*.json"))


def read_puzzle(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def labels_of(data: dict) -> Dict[str, str]:
    """Nhãn ẩn thật của puzzle, đọc thẳng từ JSON."""
    return {c["cell"]: CRIMINAL if c["criminal"] else INNOCENT for c in data["characters"]}


# (tên hiển thị, đường dẫn, dữ liệu JSON, nhãn ẩn)
PUZZLES = [
    (f"{p.parent.name}/{p.name}", p, read_puzzle(p), labels_of(read_puzzle(p)))
    for p in PUZZLE_PATHS
]


def load_engine(path: Path) -> GameEngine:
    engine = GameEngine()
    engine.load_puzzle(path)
    return engine


def oracle_for(labels: Dict[str, str]) -> Callable:
    """classify giả 'toàn tri': trả đúng nhãn thật, không suy luận."""
    return lambda kb, cell: labels[cell]


def unknown(kb, cell) -> str:
    """classify giả: agent chưa chứng minh được gì."""
    return UNKNOWN


def opposite(verdict: str) -> str:
    return INNOCENT if verdict == CRIMINAL else CRIMINAL


def hidden_cells(engine: GameEngine) -> List[str]:
    """Các ô chưa lật, row-major."""
    return [c for c in board.all_cells(engine.n) if not engine.is_revealed(c)]


def snapshot(engine: GameEngine):
    """Trạng thái công khai của ván, để so sánh trước/sau."""
    kb = engine.get_public_kb()
    return engine.revealed_cells, dict(kb.proved), [c.id for c in kb.revealed_clues]


class PuzzleSetTest(unittest.TestCase):
    def test_puzzles_exist_for_every_grid_size(self):
        self.assertTrue(PUZZLES, f"Không tìm thấy puzzle nào trong {DATA_DIR}")
        self.assertTrue({3, 4, 5} <= {data["n"] for _, _, data, _ in PUZZLES})

    def test_every_puzzle_loads_with_full_grid(self):
        for name, path, data, _ in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                self.assertEqual(engine.n, data["n"])
                self.assertEqual(len(engine.characters), data["n"] ** 2)


class InitialStateTest(unittest.TestCase):
    def test_face_up_cards_match_the_json(self):
        for name, path, data, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                expected = sorted(data["initially_revealed"],
                                  key=lambda c: board.cell_index(c, data["n"]))
                kb = engine.get_public_kb()
                self.assertEqual(engine.revealed_cells, expected)
                self.assertEqual(kb.proved, {c: labels[c] for c in expected})
                self.assertEqual([c.id for c in kb.revealed_clues],
                                 [f"clue_{c}" for c in expected])

    def test_face_up_clues_carry_the_json_parameters(self):
        for name, path, data, _ in PUZZLES:
            with self.subTest(puzzle=name):
                raw = {c["cell"]: c["clue"] for c in data["characters"]}
                for clue in load_engine(path).get_public_kb().revealed_clues:
                    params = {k: v for k, v in raw[clue.owner].items() if k != "type"}
                    self.assertEqual(clue.type, raw[clue.owner]["type"])
                    self.assertEqual(clue.params, params)

    def test_face_down_cards_are_absent_from_the_initial_kb(self):
        for name, path, _, _ in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                kb = engine.get_public_kb()
                for cell in hidden_cells(engine):
                    self.assertNotIn(cell, kb.proved)
                    self.assertNotIn(cell, [c.owner for c in kb.revealed_clues])


class FullGameTest(unittest.TestCase):
    def play(self, engine: GameEngine, labels: Dict[str, str], order: List[str]) -> None:
        oracle = oracle_for(labels)
        for cell in order:
            self.assertEqual(engine.submit_verdict(cell, labels[cell], oracle), ACCEPTED, cell)

    def assert_fully_revealed(self, engine: GameEngine, labels: Dict[str, str]) -> None:
        self.assertEqual(engine.revealed_cells, board.all_cells(engine.n))
        kb = engine.get_public_kb()
        self.assertEqual(kb.proved, labels)
        self.assertEqual(len(kb.revealed_clues), engine.n ** 2)

    def test_flipping_every_card_row_major_reveals_the_whole_grid(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                self.play(engine, labels, hidden_cells(engine))
                self.assert_fully_revealed(engine, labels)

    def test_flipping_in_reverse_order_gives_the_same_final_state(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                self.play(engine, labels, list(reversed(hidden_cells(engine))))
                self.assert_fully_revealed(engine, labels)

    def test_each_accepted_flip_adds_exactly_one_card_to_the_kb(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                for cell in hidden_cells(engine):
                    before = len(engine.revealed_cells)
                    self.play(engine, labels, [cell])
                    kb = engine.get_public_kb()
                    owners = [c.owner for c in kb.revealed_clues]
                    self.assertEqual(len(owners), before + 1)
                    self.assertEqual(owners, engine.revealed_cells)
                    self.assertEqual(set(kb.proved), set(owners))
                    self.assertEqual(kb.proved[cell], labels[cell])

    def test_restart_after_full_game_returns_to_initial_state(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                initial = snapshot(engine)
                self.play(engine, labels, hidden_cells(engine))
                engine.restart()
                self.assertEqual(snapshot(engine), initial)


class RejectionOnRealPuzzlesTest(unittest.TestCase):
    def test_wrong_verdict_is_contradicted_for_every_hidden_cell(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                before = snapshot(engine)
                for cell in hidden_cells(engine):
                    result = engine.submit_verdict(cell, opposite(labels[cell]),
                                                   oracle_for(labels))
                    self.assertEqual(result, CONTRADICTED, cell)
                self.assertEqual(snapshot(engine), before)

    def test_unprovable_cell_is_not_provable_whatever_the_verdict(self):
        for name, path, _, _ in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                before = snapshot(engine)
                for cell in hidden_cells(engine):
                    for verdict in (CRIMINAL, INNOCENT):
                        self.assertEqual(engine.submit_verdict(cell, verdict, unknown),
                                         NOT_PROVABLE, (cell, verdict))
                self.assertEqual(snapshot(engine), before)

    def test_rejections_never_leak_a_hidden_clue(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                for cell in hidden_cells(engine):
                    engine.submit_verdict(cell, opposite(labels[cell]), oracle_for(labels))
                    engine.submit_verdict(cell, labels[cell], unknown)
                kb = engine.get_public_kb()
                for cell in hidden_cells(engine):
                    self.assertNotIn(cell, kb.proved)
                    self.assertNotIn(cell, [c.owner for c in kb.revealed_clues])


def _unsolved(engine: GameEngine) -> List[str]:
    value = engine.unsolved_cells  # chấp nhận cả property lẫn method
    return list(value() if callable(value) else value)


def _solved(engine: GameEngine) -> bool:
    value = engine.is_solved
    return bool(value() if callable(value) else value)


@unittest.skipUnless(
    hasattr(GameEngine, "unsolved_cells") and hasattr(GameEngine, "is_solved"),
    "GameEngine chưa có unsolved_cells / is_solved",
)
class SolvedStateTest(unittest.TestCase):
    def test_initially_unsolved_cells_are_the_face_down_cards(self):
        for name, path, _, _ in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                self.assertEqual(_unsolved(engine), hidden_cells(engine))
                self.assertFalse(_solved(engine))

    def test_unsolved_cells_shrink_by_one_per_accepted_flip(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                for cell in hidden_cells(engine):
                    before = _unsolved(engine)
                    engine.submit_verdict(cell, labels[cell], oracle_for(labels))
                    self.assertEqual(_unsolved(engine), [c for c in before if c != cell])

    def test_is_solved_only_when_the_last_card_is_flipped(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                order = hidden_cells(engine)
                for cell in order[:-1]:
                    engine.submit_verdict(cell, labels[cell], oracle_for(labels))
                    self.assertFalse(_solved(engine), cell)
                engine.submit_verdict(order[-1], labels[order[-1]], oracle_for(labels))
                self.assertTrue(_solved(engine))
                self.assertEqual(_unsolved(engine), [])

    def test_rejections_do_not_change_unsolved_cells(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                before = _unsolved(engine)
                for cell in before:
                    engine.submit_verdict(cell, opposite(labels[cell]), oracle_for(labels))
                    engine.submit_verdict(cell, labels[cell], unknown)
                self.assertEqual(_unsolved(engine), before)

    def test_restart_makes_a_solved_game_unsolved_again(self):
        for name, path, _, labels in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                initial = _unsolved(engine)
                for cell in initial:
                    engine.submit_verdict(cell, labels[cell], oracle_for(labels))
                engine.restart()
                self.assertFalse(_solved(engine))
                self.assertEqual(_unsolved(engine), initial)


class RealAgentIntegrationTest(unittest.TestCase):
    """Engine + LogicAgent thật. Tự SKIP cho tới khi E1 (`classify`) được cài đặt."""

    @classmethod
    def setUpClass(cls):
        try:
            from logic.agent import LogicAgent
            engine = load_engine(PUZZLE_PATHS[0])
            LogicAgent().classify(engine.get_public_kb(), hidden_cells(engine)[0])
        except (ImportError, NotImplementedError):
            raise unittest.SkipTest("LogicAgent.classify (E1) chưa cài đặt")
        cls.agent_class = LogicAgent

    def deduce_until_stuck(self, engine: GameEngine) -> None:
        """Mỗi vòng nộp ô forced đầu tiên (row-major) mà agent chứng minh được."""
        agent = self.agent_class()
        progress = True
        while progress:
            progress = False
            for cell in hidden_cells(engine):
                verdict = agent.classify(engine.get_public_kb(), cell)
                self.assertNotEqual(verdict, INCONSISTENT, cell)
                if verdict in (CRIMINAL, INNOCENT):
                    # Engine tự ném AssertionError nếu verdict lệch nhãn ẩn (agent suy sai).
                    self.assertEqual(engine.submit_verdict(cell, verdict, agent.classify),
                                     ACCEPTED, cell)
                    progress = True
                    break

    def test_agent_never_proves_a_wrong_verdict(self):
        for name, path, _, _ in PUZZLES:
            with self.subTest(puzzle=name):
                self.deduce_until_stuck(load_engine(path))

    def test_agent_solves_every_puzzle_by_deduction(self):
        # Nếu puzzle nào cố ý khó hơn khả năng suy luận thì bỏ test này (hoặc đưa puzzle đó
        # sang thư mục bad_*); còn lại, đây là bằng chứng bộ puzzle giải được theo reveal protocol.
        for name, path, _, _ in PUZZLES:
            with self.subTest(puzzle=name):
                engine = load_engine(path)
                self.deduce_until_stuck(engine)
                self.assertEqual(hidden_cells(engine), [], "agent bị STUCK")


if __name__ == "__main__":
    unittest.main()