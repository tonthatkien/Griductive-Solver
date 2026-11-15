"""GameEngine: nạp puzzle, giữ nhãn ẩn + clue chưa lật, restart. (Scope A)

Ranh giới Engine / Agent (docs/INTERFACES.md, mục 3): Agent chỉ thấy `PublicKB`.
Nhãn Criminal/Innocent và clue của thẻ chưa lật chỉ nằm trong `GameEngine`.
"""
import json
from copy import deepcopy
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union

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
    UNKNOWN,
)

PuzzleSource = Union[str, "PathLike[str]", Dict[str, Any]]


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
        n, characters, labels, clues, initial = self._parse_puzzle(data)

        self._n = n
        self._characters = characters
        self._labels = labels
        self._clues = clues
        self._initial_revealed = initial
        self._loaded = True
        self.restart()

    def restart(self) -> None:
        """Trả ván về trạng thái ban đầu: chỉ các thẻ `initially_revealed` được lật."""
        self._require_loaded()
        self._revealed = set(self._initial_revealed)

    # ------------------------------------------------------------------ truy vấn công khai
    @property
    def n(self) -> int:
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
        self._require_loaded()
        return cell in self._revealed

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
        if not self._loaded:
            raise RuntimeError("Chưa nạp puzzle: gọi load_puzzle() trước")

    @staticmethod
    def _read_source(source: PuzzleSource) -> Dict[str, Any]:
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
    def _parse_puzzle(data: Dict[str, Any]):
        """Parse + kiểm tra toàn bộ puzzle, chưa đụng tới state của engine."""
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
            raise ValueError(f"'characters' có ô trùng: {sorted(c for c in set(cells) if cells.count(c) > 1)}")
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
        return n, characters, labels, clues, initial_sorted