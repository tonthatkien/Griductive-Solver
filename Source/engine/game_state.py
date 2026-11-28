"""GameEngine: nạp puzzle, giữ nhãn ẩn + clue chưa lật, restart, submit_verdict. (Scope A)

Ranh giới Engine / Agent (docs/INTERFACES.md, mục 3): Agent chỉ thấy `PublicKB`.
Nhãn Criminal/Innocent và clue của thẻ chưa lật chỉ nằm trong `GameEngine`.
"""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Dict, List, NamedTuple, Set, Tuple, Union

from engine import board
from engine.character import Character, parse_character
from engine.clue import Clue
from engine.constants import (  # noqa: F401  (re-export: giữ import từ engine.game_state)
    ACCEPTED,
    CONTRADICTED,
    CRIMINAL,
    INCONSISTENT,
    INNOCENT,
    NOT_PROVABLE,
    STATUSES,
    UNKNOWN,
)

PuzzleSource = Union[str, "PathLike[str]", Dict[str, Any]]
# LogicAgent.classify(public_kb, cell) -> CRIMINAL | INNOCENT | UNKNOWN | INCONSISTENT
ClassifyFn = Callable[["PublicKB", str], str]


@dataclass(frozen=True)
class PublicKB:
    """Phần DUY NHẤT Agent được thấy (ranh giới Engine / Agent, INTERFACES.md mục 3).

    Gồm đúng ba thứ: kích thước lưới, các clue đã lật, và verdict đã chứng minh của các thẻ
    đã lật. Không chứa nhãn ẩn của thẻ chưa lật, không chứa clue chưa lật, không giữ tham
    chiếu tới `GameEngine`. Agent nhận `PublicKB`, KHÔNG nhận `GameEngine`.

    Mỗi lần `GameEngine.get_public_kb()` trả một bản sao độc lập: sửa `proved` hay `params`
    của clue trong bản này không ảnh hưởng ván chơi.
    """

    n: int
    revealed_clues: Tuple[Clue, ...] = ()
    proved: Dict[str, str] = field(default_factory=dict)  # cell -> CRIMINAL | INNOCENT


class _ParsedPuzzle(NamedTuple):
    """Kết quả parse + kiểm tra puzzle, chưa gắn vào engine."""

    n: int
    characters: Tuple[Character, ...]       # công khai, row-major
    labels: Dict[str, str]                  # BÍ MẬT: cell -> CRIMINAL | INNOCENT
    clues: Dict[str, Clue]                  # BÍ MẬT cho tới khi thẻ được lật
    initial_revealed: Tuple[str, ...]       # row-major


class GameEngine:
    """Trạng thái một ván chơi. Gọi `load_puzzle` trước khi dùng các hàm khác."""

    def __init__(self) -> None:
        self._n = 0
        self._characters: Tuple[Character, ...] = ()
        self._labels: Dict[str, str] = {}      # BÍ MẬT: cell -> CRIMINAL | INNOCENT
        self._clues: Dict[str, Clue] = {}      # BÍ MẬT cho tới khi thẻ được lật
        self._initial_revealed: Tuple[str, ...] = ()
        self._revealed: Set[str] = set()
        self._loaded = False

    # ------------------------------------------------------------------ nạp puzzle
    def load_puzzle(self, source: PuzzleSource) -> None:
        """Nạp puzzle từ đường dẫn file JSON hoặc dict đã parse, rồi đặt về trạng thái ban đầu.

        Nếu puzzle sai thì ném ValueError và giữ nguyên ván hiện tại (không nạp dở).

        Raises:
            ValueError: JSON hỏng hoặc puzzle vi phạm quy tắc ở INTERFACES.md mục 2.4.
            FileNotFoundError: đường dẫn không tồn tại.
        """
        data = self._read_source(source)
        puzzle = self._parse_puzzle(data)

        self._n = puzzle.n
        self._characters = puzzle.characters
        self._labels = puzzle.labels
        self._clues = puzzle.clues
        self._initial_revealed = puzzle.initial_revealed
        self._loaded = True
        self.restart()

    def restart(self) -> None:
        """Trả ván về trạng thái ban đầu: chỉ các thẻ `initially_revealed` được lật."""
        self._require_loaded()
        self._revealed = set(self._initial_revealed)

    # ------------------------------------------------------------------ nộp verdict
    def submit_verdict(self, cell: str, verdict: str, classify: ClassifyFn) -> str:
        """Nộp verdict cho một ô chưa lật; engine hỏi `classify` xem Logic Agent chứng minh được gì.

        `classify(public_kb, cell)` (= `LogicAgent.classify`) chỉ nhận `PublicKB`, không nhận
        engine, và trả CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT. Kết quả:

        - ACCEPTED: Agent chứng minh được đúng `verdict`. Ô được lật, clue lộ ra, `verdict`
          vào `proved` của PublicKB.
        - NOT_PROVABLE: Agent trả UNKNOWN (chưa suy ra được). Không đổi state.
        - CONTRADICTED: Agent chứng minh được verdict NGƯỢC với `verdict`. Không đổi state.

        Bắt bug (ném AssertionError, không đổi state): `classify` trả INCONSISTENT hoặc giá
        trị lạ, hoặc verdict nó chứng minh KHÔNG khớp nhãn ẩn (suy luận sai hoặc puzzle sai).

        Args:
            cell: ô cần kết luận, đúng dạng chuẩn ('C2'), nằm trong lưới và chưa lật.
            verdict: CRIMINAL hoặc INNOCENT.
            classify: hàm phân loại của Logic Agent.

        Returns:
            ACCEPTED, NOT_PROVABLE hoặc CONTRADICTED.

        Raises:
            RuntimeError: chưa gọi `load_puzzle`.
            ValueError: ô sai/ngoài lưới/đã lật, hoặc verdict không thuộc {CRIMINAL, INNOCENT}.
            AssertionError: `classify` vi phạm hợp đồng (xem trên).
        """
        self._require_loaded()
        if not isinstance(cell, str) or not board.is_valid_cell(cell, self._n):
            raise ValueError(f"Ô {cell!r} không hợp lệ hoặc ngoài lưới {self._n}x{self._n}")
        if verdict not in STATUSES:
            raise ValueError(f"verdict {verdict!r} phải thuộc {STATUSES}")
        if cell in self._revealed:
            raise ValueError(f"Ô {cell} đã lật, không thể nộp verdict nữa")

        proved = classify(self.get_public_kb(), cell)  # chỉ đưa bản sao PublicKB

        if proved not in (CRIMINAL, INNOCENT, UNKNOWN):
            raise AssertionError(
                f"classify trả {proved!r} cho {cell}: cần CRIMINAL/INNOCENT/UNKNOWN "
                f"(INCONSISTENT nghĩa là KB công khai mâu thuẫn, vốn không thể xảy ra)"
            )
        if proved != UNKNOWN and proved != self._labels[cell]:
            raise AssertionError(
                f"classify chứng minh {cell} là {proved} nhưng nhãn ẩn là {self._labels[cell]}: "
                f"suy luận sai hoặc puzzle không nhất quán"
            )
        if proved == UNKNOWN:
            return NOT_PROVABLE
        if proved != verdict:
            return CONTRADICTED

        self._revealed.add(cell)
        return ACCEPTED

    # ------------------------------------------------------------------ truy vấn công khai
    @property
    def n(self) -> int:
        """Kích thước lưới (n x n)."""
        self._require_loaded()
        return self._n

    @property
    def characters(self) -> Tuple[Character, ...]:
        """Thông tin công khai (ô, tên, nghề) của mọi nhân vật, thứ tự row-major."""
        self._require_loaded()
        return self._characters

    @property
    def revealed_cells(self) -> List[str]:
        """Các ô đã lật, thứ tự row-major."""
        self._require_loaded()
        return sorted(self._revealed, key=lambda c: board.cell_index(c, self._n))

    def is_revealed(self, cell: str) -> bool:
        """True nếu thẻ ở `cell` đã lật. Ô không tồn tại thì trả False (không ném lỗi)."""
        self._require_loaded()
        return cell in self._revealed

    @property
    def unsolved_cells(self) -> List[str]:
        """Các ô chưa lật, thứ tự row-major."""
        self._require_loaded()
        return [c for c in board.all_cells(self._n) if c not in self._revealed]

    def is_solved(self) -> bool:
        """True nếu mọi thẻ đã lật."""
        return not self.unsolved_cells
    
    def get_public_kb(self) -> PublicKB:
        """PublicKB hiện tại: clue + verdict đã chứng minh của các thẻ đã lật (row-major).

        Thẻ face-up ban đầu công khai cả trạng thái lẫn clue (INTERFACES.md, mục 2.3).
        Trả bản sao sâu của clue và dict mới, nên Agent không thể sửa trạng thái engine
        qua kết quả này. Thẻ chưa lật không xuất hiện ở bất kỳ trường nào.

        Raises:
            RuntimeError: chưa gọi `load_puzzle`.
        """
        self._require_loaded()
        cells = self.revealed_cells
        return PublicKB(
            n=self._n,
            revealed_clues=tuple(deepcopy(self._clues[c]) for c in cells),
            proved={c: self._labels[c] for c in cells},
        )

    # ------------------------------------------------------------------ nội bộ
    def _require_loaded(self) -> None:
        """Ném RuntimeError nếu chưa gọi `load_puzzle`."""
        if not self._loaded:
            raise RuntimeError("Chưa nạp puzzle: gọi load_puzzle() trước")

    @staticmethod
    def _read_source(source: PuzzleSource) -> Dict[str, Any]:
        """Đọc puzzle từ dict (bản sao sâu) hoặc file JSON. Raises ValueError nếu JSON hỏng."""
        if isinstance(source, dict):
            return deepcopy(source)
        path = Path(source)
        try:
            with path.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: JSON không hợp lệ: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path}: gốc của file puzzle phải là object JSON")
        return data

    @staticmethod
    def _parse_puzzle(data: Dict[str, Any]) -> _ParsedPuzzle:
        """Parse + kiểm tra toàn bộ puzzle, chưa đụng tới state của engine.

        Raises:
            ValueError: puzzle vi phạm quy tắc ở INTERFACES.md mục 2.4.
        """
        n = data.get("n")
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError(f"'n' phải là số nguyên dương, nhận {n!r}")

        raw = data.get("characters")
        if not isinstance(raw, list) or len(raw) != n * n:
            got = len(raw) if isinstance(raw, list) else raw
            raise ValueError(f"'characters' phải là list đúng {n * n} phần tử, nhận {got!r}")

        parsed = [parse_character(item, n) for item in raw]
        cells = [ch.cell for ch, _, _ in parsed]
        if len(set(cells)) != len(cells):
            dups = sorted(c for c in set(cells) if cells.count(c) > 1)
            raise ValueError(f"'characters' có ô trùng: {dups}")
        parsed.sort(key=lambda item: board.cell_index(item[0].cell, n))

        names = [ch.name.casefold() for ch, _, _ in parsed]
        if any(a >= b for a, b in zip(names, names[1:])):
            raise ValueError("tên character phải tăng dần theo alphabet theo thứ tự row-major")

        initial = data.get("initially_revealed")
        if not isinstance(initial, list) or not initial:
            raise ValueError("'initially_revealed' phải là list không rỗng")
        for cell in initial:
            if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
                raise ValueError(f"'initially_revealed': ô {cell!r} không hợp lệ hoặc ngoài lưới")
        if len(set(initial)) != len(initial):
            raise ValueError(f"'initially_revealed' có ô trùng: {initial!r}")

        characters = tuple(ch for ch, _, _ in parsed)
        labels = {ch.cell: (CRIMINAL if crim else INNOCENT) for ch, crim, _ in parsed}
        clues = {ch.cell: clue for ch, _, clue in parsed}
        initial_sorted = tuple(sorted(initial, key=lambda c: board.cell_index(c, n)))
        return _ParsedPuzzle(n, characters, labels, clues, initial_sorted)