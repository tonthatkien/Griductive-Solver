"""Clue + Region. (Scope A viết; Scope C, D dùng để encode/evaluate)

Định dạng clue trong file JSON (xem docs/INTERFACES.md):

  FACT       {"cell": "A1", "status": "CRIMINAL"|"INNOCENT"}
  SAME       {"a": "A1", "b": "B2"}
  DIFFERENT  {"a": "A1", "b": "B2"}
  EXACTLY    {"region": <region>, "k": 2}
  AT_LEAST   {"region": <region>, "k": 2}
  AT_MOST    {"region": <region>, "k": 2}
  -- Extension (gợi ý, nhóm có thể đổi) --
  PARITY     {"region": <region>, "parity": "EVEN"|"ODD"}      # số criminal chẵn/lẻ
  COMPARE    {"left": <region>, "right": <region>, "op": "GT"|"GE"|"EQ"|"LE"|"LT"}

  <region> = {"type": "row", "index": 2}
           | {"type": "col", "index": "B"}
           | {"type": "neighbors", "cell": "C2"}
           | {"type": "cells", "cells": ["A1", "B3"]}
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from engine import board


@dataclass(frozen=True)
class Clue:
    id: str            # vd "clue_C2"
    owner: str         # cell của nhân vật sở hữu clue
    type: str          # xem danh sách trên
    params: Dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


CORE_TYPES = ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST")
EXT_TYPES = ("PARITY", "COMPARE")


def clue_from_dict(owner: str, d: dict) -> Clue:
    """Tạo Clue từ dict JSON {"type":..., ...params}. id = f"clue_{owner}"."""
    d = dict(d)
    t = d.pop("type")
    return Clue(id=f"clue_{owner}", owner=owner, type=t, params=d)


def resolve_region(region: dict, n: int) -> List[str]:
    """Region spec -> list cell id (không trùng, giữ thứ tự row-major).
    Scope A viết; Scope C, D dùng cho encoder + evaluator; Scope F dùng cho highlight.
    """
    t = region["type"]
    if t == "row":
        cells = board.row_cells(n, int(region["index"]))
    elif t == "col":
        cells = board.col_cells(n, region["index"])
    elif t == "neighbors":
        cells = board.neighbor_cells(n, region["cell"])
    elif t == "cells":
        cells = list(region["cells"])
    else:
        raise ValueError(f"Unknown region type: {t}")
    order = {c: i for i, c in enumerate(board.all_cells(n))}
    return sorted(set(cells), key=lambda c: order[c])


def clue_cells(clue: Clue, n: int) -> List[str]:
    """TODO(A2): các ô mà clue nhắc tới (để GUI highlight).
    FACT -> [cell]; SAME/DIFFERENT -> [a, b]; counting/PARITY -> resolve_region;
    COMPARE -> left + right.
    """
    raise NotImplementedError


def validate_clue(clue: Clue, n: int) -> None:
    """TODO(A2): raise ValueError nếu sai. Kiểm tra:
       - cell nằm trong lưới, region không rỗng, cell trong 'cells' không trùng
       - 0 <= k <= |region| với EXACTLY/AT_LEAST/AT_MOST
       - type hợp lệ, status hợp lệ
    """
    raise NotImplementedError
