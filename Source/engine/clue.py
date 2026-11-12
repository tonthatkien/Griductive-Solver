"""Clue + Region. (Scope A viết; Scope C, D dùng để encode/evaluate)

Định dạng clue trong file JSON (xem docs/INTERFACES.md):

  FACT              {"target": "A1", "status": "CRIMINAL"|"INNOCENT"}
  SAME_STATUS       {"cell1": "A1", "cell2": "B2"}
  DIFFERENT_STATUS  {"cell1": "A1", "cell2": "B2"}
  EXACTLY           {"region": <region>, "k": 2, "status": ...}
  AT_LEAST          {"region": <region>, "k": 2, "status": ...}
  AT_MOST           {"region": <region>, "k": 2, "status": ...}
  -- Extension --
  PARITY            {"region": <region>, "parity": "EVEN"|"ODD", "status": ...}
  COMPARE           {"region1": <region>, "region2": <region>,
                     "op": "GT"|"GE"|"EQ"|"LE"|"LT", "status": ...}

  status ∈ {"CRIMINAL", "INNOCENT"}.
    - FACT: BẮT BUỘC có status (không có mặc định).
    - EXACTLY/AT_LEAST/AT_MOST/PARITY/COMPARE: bỏ qua thì mặc định "CRIMINAL" (dùng clue_status()).
    - SAME_STATUS/DIFFERENT_STATUS: không dùng status.

  <region> = {"type": "row", "number": 2}
           | {"type": "col", "letter": "B"}
           | {"type": "neighbors", "cell": "C2"}
           | {"type": "list", "cells": ["A1", "B3"]}
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


CORE_TYPES = ("FACT", "SAME_STATUS", "DIFFERENT_STATUS", "EXACTLY", "AT_LEAST", "AT_MOST")
EXT_TYPES = ("PARITY", "COMPARE")

# Không import từ game_state (game_state đã import clue -> vòng lặp import).
FACT_STATUSES = ("CRIMINAL", "INNOCENT")
COUNT_TYPES = ("EXACTLY", "AT_LEAST", "AT_MOST")
PAIR_TYPES = ("SAME_STATUS", "DIFFERENT_STATUS")
PARITIES = ("EVEN", "ODD")
DEFAULT_STATUS = "CRIMINAL"
COMPARE_OPS = ("GT", "GE", "EQ", "LE", "LT")


def clue_from_dict(owner: str, d: dict) -> Clue:
    """Tạo Clue từ dict JSON {"type":..., ...params}. id = f"clue_{owner}"."""
    d = dict(d)
    t = d.pop("type")
    return Clue(id=f"clue_{owner}", owner=owner, type=t, params=d)


def clue_status(clue: Clue) -> str:
    """status của clue (encoder C và semantic D đều gọi hàm này).

    FACT: bắt buộc có status. SAME_STATUS/DIFFERENT_STATUS: không có status.
    Các loại còn lại: bỏ qua thì mặc định CRIMINAL.

    Raises:
        ValueError: FACT thiếu status, hoặc clue SAME_STATUS/DIFFERENT_STATUS (không dùng status).
    """
    t, p = clue.type, clue.params
    if t in PAIR_TYPES:
        raise ValueError(f"{t} không dùng status")
    if t == "FACT":
        if "status" not in p:
            raise ValueError("FACT: thiếu status (bắt buộc)")
        return p["status"]
    return p.get("status", DEFAULT_STATUS)


def resolve_region(region: dict, n: int) -> List[str]:
    """Region spec -> list cell id (không trùng, giữ thứ tự row-major).
    Scope A viết; Scope C, D dùng cho encoder + evaluator; Scope F dùng cho highlight.
    """
    t = region["type"]
    if t == "row":
        cells = board.row_cells(n, int(region["number"]))
    elif t == "col":
        cells = board.col_cells(n, region["letter"])
    elif t == "neighbors":
        cells = board.neighbor_cells(n, region["cell"])
    elif t == "list":
        cells = list(region["cells"])
    else:
        raise ValueError(f"Unknown region type: {t}")
    order = {c: i for i, c in enumerate(board.all_cells(n))}
    return sorted(set(cells), key=lambda c: order[c])


def _sorted_unique(cells: List[str], n: int) -> List[str]:
    """Bỏ trùng và sắp row-major (ô ngoài lưới -> ValueError từ board.cell_index)."""
    return sorted(set(cells), key=lambda c: board.cell_index(c, n))


def clue_cells(clue: Clue, n: int) -> List[str]:
    """Các ô mà clue nhắc tới (để GUI highlight), không trùng, thứ tự row-major.

    FACT -> [target]; SAME_STATUS/DIFFERENT_STATUS -> [cell1, cell2]; counting/PARITY -> resolve_region;
    COMPARE -> region1 + region2 (hợp của hai vùng).
    Không gồm ô `owner` trừ khi chính clue nhắc tới ô đó.

    Raises:
        ValueError: kiểu clue lạ hoặc ô/vùng ngoài lưới. Muốn kiểm kỹ thì gọi validate_clue trước.
    """
    t, p = clue.type, clue.params
    if t == "FACT":
        cells = [p["target"]]
    elif t in PAIR_TYPES:
        cells = [p["cell1"], p["cell2"]]
    elif t in COUNT_TYPES or t == "PARITY":
        cells = resolve_region(p["region"], n)
    elif t == "COMPARE":
        cells = resolve_region(p["region1"], n) + resolve_region(p["region2"], n)
    else:
        raise ValueError(f"Kiểu clue không hợp lệ: {t!r}")
    return _sorted_unique(cells, n)


def _check_cell(cell: Any, n: int, what: str) -> None:
    """Ô phải là chuỗi đúng dạng chuẩn ('C2') và nằm trong lưới n x n."""
    if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
        raise ValueError(f"{what}: ô {cell!r} không hợp lệ hoặc ngoài lưới {n}x{n}")


def _check_region(region: Any, n: int, what: str) -> List[str]:
    """Kiểm tra region spec; trả về danh sách ô đã resolve. Raises ValueError nếu sai/rỗng."""
    if not isinstance(region, dict) or "type" not in region:
        raise ValueError(f"{what}: region thiếu hoặc sai dạng: {region!r}")
    t = region["type"]
    if t == "row":
        idx = region.get("number")
        if isinstance(idx, bool) or not isinstance(idx, int) or not 1 <= idx <= n:
            raise ValueError(f"{what}: hàng {idx!r} ngoài lưới {n}x{n}")
    elif t == "col":
        idx = region.get("letter")
        if not isinstance(idx, str) or len(idx) != 1 or idx not in board.COLS[:n]:
            raise ValueError(f"{what}: cột {idx!r} ngoài lưới {n}x{n}")
    elif t == "neighbors":
        _check_cell(region.get("cell"), n, what)
    elif t == "list":
        raw = region.get("cells")
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"{what}: region 'list' có 'cells' rỗng hoặc không phải list")
        for c in raw:
            _check_cell(c, n, what)
        if len(set(raw)) != len(raw):
            raise ValueError(f"{what}: region 'list' có ô trùng: {raw!r}")
    else:
        raise ValueError(f"{what}: kiểu region lạ: {t!r}")
    cells = resolve_region(region, n)
    if not cells:  # vd neighbors của lưới 1x1
        raise ValueError(f"{what}: region rỗng: {region!r}")
    return cells


def _check_status(p: dict, what: str) -> None:
    """status là tùy chọn (mặc định CRIMINAL); nếu có thì phải thuộc FACT_STATUSES."""
    if "status" in p and p["status"] not in FACT_STATUSES:
        raise ValueError(f"{what}: status {p['status']!r} phải thuộc {FACT_STATUSES}")


def validate_clue(clue: Clue, n: int) -> None:
    """Raise ValueError nếu clue sai; hợp lệ thì trả về None. Kiểm tra:
       - owner và mọi ô nhắc tới nằm trong lưới (đúng dạng chuẩn, vd 'C2' chứ không 'c2')
       - region đúng kiểu, không rỗng; 'cells' không có ô trùng
       - 0 <= k <= |region| với EXACTLY/AT_LEAST/AT_MOST (k là int, không phải bool)
       - SAME/DIFFERENT: hai ô khác nhau (clue về một ô với chính nó vô nghĩa)
       - type, parity, op hợp lệ; status hợp lệ: FACT bắt buộc có, các clue đếm/PARITY/COMPARE
         tùy chọn (mặc định CRIMINAL), SAME_STATUS/DIFFERENT_STATUS không dùng; thiếu tham số cũng báo ValueError (không KeyError)
    """
    t, p = clue.type, clue.params
    _check_cell(clue.owner, n, "owner")
    if t == "FACT":
        _check_cell(p.get("target"), n, t)
        if "status" not in p:
            raise ValueError(f"{t}: thiếu status (bắt buộc với FACT)")
        _check_status(p, t)
    elif t in PAIR_TYPES:
        _check_cell(p.get("cell1"), n, t)
        _check_cell(p.get("cell2"), n, t)
        if p["cell1"] == p["cell2"]:
            raise ValueError(f"{t}: hai ô phải khác nhau, nhận {p['cell1']!r}")
    elif t in COUNT_TYPES:
        size = len(_check_region(p.get("region"), n, t))
        k = p.get("k")
        if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= size:
            raise ValueError(f"{t}: k={k!r} phải là số nguyên trong [0, {size}]")
        _check_status(p, t)
    elif t == "PARITY":
        _check_region(p.get("region"), n, t)
        if p.get("parity") not in PARITIES:
            raise ValueError(f"{t}: parity {p.get('parity')!r} phải thuộc {PARITIES}")
        _check_status(p, t)
    elif t == "COMPARE":
        _check_region(p.get("region1"), n, f"{t}.region1")
        _check_region(p.get("region2"), n, f"{t}.region2")
        if p.get("op") not in COMPARE_OPS:
            raise ValueError(f"{t}: op {p.get('op')!r} phải thuộc {COMPARE_OPS}")
        _check_status(p, t)
    else:
        raise ValueError(f"Kiểu clue không hợp lệ: {t!r}")