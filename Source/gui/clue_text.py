"""Chuyển clue có cấu trúc thành câu tiếng Việt + tính các ô clue nhắc tới.

Không phụ thuộc Qt nên test được trong CI (CI không cài PySide6).
"""
from typing import Dict, List, Optional

from engine import board
from engine.clue import Clue, resolve_region

STATUS_VN = {"CRIMINAL": "Tội phạm", "INNOCENT": "Vô tội"}
COMPARE_VN = {"GT": "nhiều hơn", "GE": "không ít hơn", "EQ": "bằng",
              "LE": "không nhiều hơn", "LT": "ít hơn"}


def _who(cell: str, names: Optional[Dict[str, str]]) -> str:
    return f"{names[cell]} ({cell})" if names and cell in names else cell


def region_text(region: dict, names: Optional[Dict[str, str]] = None) -> str:
    """Mô tả một region bằng tiếng Việt."""
    t = region["type"]
    if t == "row":
        return f"hàng {region['index']}"
    if t == "col":
        return f"cột {region['index']}"
    if t == "neighbors":
        return f"những người xung quanh {_who(region['cell'], names)}"
    return "các ô " + ", ".join(region["cells"])


def format_clue_text(clue: Clue, names: Optional[Dict[str, str]] = None) -> str:
    """Câu mô tả clue (dùng trên thẻ, danh sách clue và sổ tay)."""
    p, t = clue.params, clue.type
    if t == "FACT":
        return f"{_who(p['cell'], names)} là {STATUS_VN[p['status']].lower()}."
    if t in ("SAME", "DIFFERENT"):
        word = "cùng" if t == "SAME" else "khác"
        return f"{_who(p['a'], names)} và {_who(p['b'], names)} có trạng thái {word} nhau."
    if t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        reg, k = region_text(p["region"], names), p["k"]
        if t == "EXACTLY" and k == 0:
            return f"Không có tội phạm nào trong {reg}."
        word = {"EXACTLY": "đúng", "AT_LEAST": "ít nhất", "AT_MOST": "nhiều nhất"}[t]
        return f"Có {word} {k} tội phạm trong {reg}."
    if t == "PARITY":
        word = "chẵn" if p["parity"] == "EVEN" else "lẻ"
        return f"Số tội phạm trong {region_text(p['region'], names)} là số {word}."
    if t == "COMPARE":
        return (f"Số tội phạm ở {region_text(p['left'], names)} "
                f"{COMPARE_VN[p['op']]} số tội phạm ở {region_text(p['right'], names)}.")
    return f"{t} {p}"


def cells_of_clue(clue: Clue, n: int) -> List[str]:
    """Các ô clue nhắc tới. Ưu tiên engine.clue.clue_cells (A2); dự phòng khi A2 chưa xong."""
    from engine import clue as clue_module
    try:
        return clue_module.clue_cells(clue, n)
    except NotImplementedError:
        pass
    p, t = clue.params, clue.type
    if t == "FACT":
        cells = [p["cell"]]
    elif t in ("SAME", "DIFFERENT"):
        cells = [p["a"], p["b"]]
    elif t == "COMPARE":
        cells = resolve_region(p["left"], n) + resolve_region(p["right"], n)
    else:
        cells = resolve_region(p["region"], n)
    order = {c: i for i, c in enumerate(board.all_cells(n))}
    return sorted(set(cells), key=lambda c: order[c])
