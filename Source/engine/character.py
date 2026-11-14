"""Character: phần CÔNG KHAI của một nhân vật. (Scope A)

Nhãn Criminal/Innocent và clue là thông tin BÍ MẬT: chỉ `GameEngine` giữ,
nên không nằm trong `Character`. Module này chỉ parse một mục trong
`characters` của file puzzle (xem docs/INTERFACES.md, mục 2 và 2.4).
"""
from dataclasses import dataclass
from typing import Any, Tuple

from engine import board
from engine.clue import Clue, clue_from_dict, validate_clue


@dataclass(frozen=True)
class Character:
    """Thông tin công khai của nhân vật: ô, tên, nghề. Không có nhãn ẩn, không có clue."""

    cell: str
    name: str
    profession: str


def _require_text(data: dict, key: str, where: str) -> str:
    """Lấy `data[key]`, phải là chuỗi không rỗng."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: '{key}' phải là chuỗi không rỗng, nhận {value!r}")
    return value


def parse_character(data: Any, n: int) -> Tuple[Character, bool, Clue]:
    """Parse một mục `characters` của file puzzle.

    Args:
        data: dict dạng {"cell", "name", "profession", "criminal", "clue"}.
        n: kích thước lưới (n x n).

    Returns:
        (Character công khai, nhãn ẩn `criminal` (True = Criminal), Clue đã validate).
        Hai phần sau là bí mật: chỉ GameEngine được giữ.

    Raises:
        ValueError: thiếu khóa, sai kiểu, ô ngoài lưới, hoặc clue không hợp lệ.
    """
    if not isinstance(data, dict):
        raise ValueError(f"character phải là object JSON, nhận {data!r}")

    cell = data.get("cell")
    if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
        raise ValueError(f"character: ô {cell!r} không hợp lệ hoặc ngoài lưới {n}x{n}")
    where = f"character {cell}"

    name = _require_text(data, "name", where)
    profession = _require_text(data, "profession", where)

    criminal = data.get("criminal")
    if not isinstance(criminal, bool):
        raise ValueError(f"{where}: 'criminal' phải là true/false, nhận {criminal!r}")

    clue_data = data.get("clue")
    if not isinstance(clue_data, dict) or "type" not in clue_data:
        raise ValueError(f"{where}: thiếu 'clue' hoặc clue thiếu 'type'")
    clue = clue_from_dict(cell, clue_data)
    try:
        validate_clue(clue, n)
    except ValueError as exc:
        raise ValueError(f"{where}: clue không hợp lệ: {exc}") from exc

    return Character(cell=cell, name=name, profession=profession), criminal, clue