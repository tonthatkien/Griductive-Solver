"""Game Engine: giữ lời giải ẩn + clue chưa lật; chỉ phát PublicKB cho Agent. (Scope A)

Quan hệ một chiều:   GameEngine  --PublicKB-->  Logic Agent
Agent KHÔNG được nhận GameEngine, chỉ nhận PublicKB.

TODO(Scope A):
  - load_puzzle(path): đọc JSON (docs/INTERFACES.md), validate clue, tạo Character
  - restart()
  - get_public_kb() -> PublicKB  (chỉ clue đã lật + verdict đã chứng minh)
  - submit_verdict(cell, verdict, classify_fn) -> kết quả (xem docstring)
  - is_solved(), unsolved_cells()
  - kiểm tra nội bộ: verdict được agent chứng minh PHẢI khớp nhãn ẩn (assert, để bắt bug)
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from engine.clue import Clue

CRIMINAL, INNOCENT = "CRIMINAL", "INNOCENT"
UNKNOWN, INCONSISTENT = "UNKNOWN", "INCONSISTENT"
ACCEPTED, NOT_PROVABLE, CONTRADICTED = "ACCEPTED", "NOT_PROVABLE", "CONTRADICTED"


@dataclass
class PublicKB:
    """Thứ DUY NHẤT agent được nhìn thấy."""
    n: int
    revealed_clues: List[Clue] = field(default_factory=list)
    proved: Dict[str, str] = field(default_factory=dict)   # cell -> CRIMINAL/INNOCENT
    # Các ô face-up ban đầu cũng nằm trong proved + revealed_clues.


class GameEngine:
    def __init__(self):
        self.n = 0
        self._solution = {}     # PRIVATE: cell -> bool
        self._clues = {}        # PRIVATE: cell -> Clue (kể cả chưa lật)
        self.characters = {}    # cell -> Character
        self.revealed = []      # thứ tự lật (để hiển thị)

    def load_puzzle(self, path: str) -> None:
        raise NotImplementedError

    def restart(self) -> None:
        raise NotImplementedError

    def get_public_kb(self) -> PublicKB:
        raise NotImplementedError

    def submit_verdict(self, cell: str, verdict: str,
                       classify_fn: Callable[[PublicKB, str], str]) -> str:
        """Người chơi/Agent đề xuất verdict cho cell.

        status = classify_fn(public_kb, cell)  # CRIMINAL / INNOCENT / UNKNOWN (từ Logic Agent)
        - status == verdict            -> ACCEPTED: đánh dấu, lật thẻ, lộ clue của cell
        - status == UNKNOWN            -> NOT_PROVABLE, không đổi state
        - status là verdict ngược lại  -> CONTRADICTED, không đổi state
        Trả về một trong ACCEPTED / NOT_PROVABLE / CONTRADICTED.
        """
        raise NotImplementedError

    def unsolved_cells(self):
        raise NotImplementedError

    def is_solved(self) -> bool:
        raise NotImplementedError
