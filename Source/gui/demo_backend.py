"""Backend GIẢ chỉ để xem/thử GUI khi engine + logic thật chưa xong (chạy: python main.py --demo).

!!! KHÔNG NỘP !!!  File này tự suy luận bằng vét cạn nên vi phạm tinh thần "DPLL tự cài".
Xóa file này (và cờ --demo trong main.py) trước khi đóng gói. Nó có cùng giao diện với
GameEngine / LogicAgent theo docs/INTERFACES.md để GUI không phải sửa gì khi ghép code thật.
"""
import itertools
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from engine import board
from engine.character import Character
from engine.clue import Clue, clue_from_dict, resolve_region
from engine.game_state import (ACCEPTED, CONTRADICTED, CRIMINAL, INCONSISTENT, INNOCENT,
                               NOT_PROVABLE, UNKNOWN, PublicKB)
from logic.agent import TraceEntry

DEMO_PUZZLE_PATH = Path(__file__).resolve().parent / "demo_puzzle.json"


def _eval(clue: Clue, a: Dict[str, bool], n: int) -> bool:
    p, t = clue.params, clue.type
    if t == "FACT":
        return a[p["cell"]] == (p["status"] == CRIMINAL)
    if t == "SAME":
        return a[p["a"]] == a[p["b"]]
    if t == "DIFFERENT":
        return a[p["a"]] != a[p["b"]]
    k = sum(a[c] for c in resolve_region(p["region"], n))
    return {"EXACTLY": k == p["k"], "AT_LEAST": k >= p["k"], "AT_MOST": k <= p["k"]}[t]


class DemoEngine:
    def __init__(self) -> None:
        self.n = 0
        self.title = ""
        self._solution: Dict[str, bool] = {}
        self._clues: Dict[str, Clue] = {}
        self._initial: List[str] = []
        self.characters: Dict[str, Character] = {}
        self.revealed: List[str] = []

    def load_puzzle(self, path: Optional[str] = None) -> None:
        with open(path or DEMO_PUZZLE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        self.n, self.title = data["n"], data.get("title", "")
        self.characters, self._solution, self._clues = {}, {}, {}
        for ch in data["characters"]:
            cell = ch["cell"]
            self.characters[cell] = Character(cell, ch["name"], ch["profession"], ch["criminal"])
            self._solution[cell] = ch["criminal"]
            self._clues[cell] = clue_from_dict(cell, ch["clue"])
        self._initial = list(data["initially_revealed"])
        self.restart()

    def restart(self) -> None:
        self.revealed = []
        for ch in self.characters.values():
            ch.revealed = False
        for cell in self._initial:
            self._reveal(cell)

    def _reveal(self, cell: str) -> None:
        self.characters[cell].revealed = True
        self.revealed.append(cell)

    def get_public_kb(self) -> PublicKB:
        return PublicKB(
            n=self.n,
            revealed_clues=[self._clues[c] for c in self.revealed],
            proved={c: (CRIMINAL if self._solution[c] else INNOCENT) for c in self.revealed})

    def submit_verdict(self, cell: str, verdict: str, classify_fn) -> str:
        status = classify_fn(self.get_public_kb(), cell)
        if status == verdict:
            assert (verdict == CRIMINAL) == self._solution[cell]
            self._reveal(cell)
            return ACCEPTED
        return NOT_PROVABLE if status == UNKNOWN else CONTRADICTED

    def unsolved_cells(self) -> List[str]:
        return [c for c in board.all_cells(self.n) if not self.characters[c].revealed]

    def is_solved(self) -> bool:
        return not self.unsolved_cells()


class DemoAgent:
    """Cùng chữ ký với LogicAgent; suy luận bằng vét cạn (chỉ cho demo)."""

    def __init__(self) -> None:
        self.sat_calls = 0
        self.total_decisions = 0
        self.total_propagations = 0
        self.total_backtracks = 0
        self._cache: Dict[tuple, List[Dict[str, bool]]] = {}

    def _models(self, kb: PublicKB) -> List[Dict[str, bool]]:
        key = (tuple(c.id for c in kb.revealed_clues), tuple(sorted(kb.proved.items())))
        if key not in self._cache:
            cells = board.all_cells(kb.n)
            found = []
            for bits in itertools.product((False, True), repeat=len(cells)):
                a = dict(zip(cells, bits))
                if all(a[c] == (v == CRIMINAL) for c, v in kb.proved.items()) and \
                        all(_eval(c, a, kb.n) for c in kb.revealed_clues):
                    found.append(a)
            self._cache[key] = found
        return self._cache[key]

    def classify(self, kb: PublicKB, cell: str) -> str:
        models = self._models(kb)
        self.sat_calls += 2
        if not models:
            return INCONSISTENT
        values = {m[cell] for m in models}
        if values == {True}:
            return CRIMINAL
        if values == {False}:
            return INNOCENT
        return UNKNOWN

    def next_forced(self, kb: PublicKB) -> Optional[Tuple[str, str]]:
        for cell in board.all_cells(kb.n):
            if cell not in kb.proved:
                s = self.classify(kb, cell)
                if s in (CRIMINAL, INNOCENT):
                    return cell, s
        return None

    def hint(self, kb: PublicKB):
        forced = self.next_forced(kb)
        if not forced:
            return None
        return forced[0], forced[1], [c.id for c in kb.revealed_clues][-1:]

    def auto_solve(self, engine) -> List[TraceEntry]:
        raise NotImplementedError("GUI chạy từng bước bằng next_forced + submit_verdict")
