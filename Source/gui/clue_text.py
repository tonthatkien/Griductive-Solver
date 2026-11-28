"""Chuyển clue có cấu trúc thành câu tiếng Việt + tính các ô clue nhắc tới. (Scope F)

Khớp schema thật ở docs/INTERFACES.md mục 2.1 và 2.2:
  region: row{number} | col{letter} | neighbors{cell} | list{cells}
  FACT{target,status} | SAME_STATUS/DIFFERENT_STATUS{cell1,cell2}
  EXACTLY/AT_LEAST/AT_MOST{region,k,status?} | PARITY{region,parity,status?}
  COMPARE{region1,op,region2,status?}      (status thiếu => CRIMINAL)

Không phụ thuộc Qt nên test được trong CI (CI không cài PySide6).
"""
import re
from typing import Dict, List, Optional

from engine.clue import Clue, clue_cells, clue_status
from engine.constants import CRIMINAL

STATUS_VN = {"CRIMINAL": "Tội phạm", "INNOCENT": "Vô tội"}
COMPARE_VN = {"GT": "nhiều hơn", "GE": "không ít hơn", "EQ": "bằng",
              "LE": "không nhiều hơn", "LT": "ít hơn"}
PARITY_VN = {"EVEN": "chẵn", "ODD": "lẻ"}
COUNT_WORD_VN = {"EXACTLY": "đúng", "AT_LEAST": "ít nhất", "AT_MOST": "nhiều nhất"}


def _who(cell: str, names: Optional[Dict[str, str]]) -> str:
    return f"{names[cell]} ({cell})" if names and cell in names else cell


def _noun(status: str) -> str:
    """Danh từ đếm theo status của clue: 'tội phạm' hoặc 'người vô tội'."""
    return "tội phạm" if status == CRIMINAL else "người vô tội"


def region_text(region: dict, names: Optional[Dict[str, str]] = None) -> str:
    """Mô tả một region bằng tiếng Việt."""
    t = region["type"]
    if t == "row":
        return f"hàng {region['number']}"
    if t == "col":
        return f"cột {region['letter']}"
    if t == "neighbors":
        return f"những người xung quanh {_who(region['cell'], names)}"
    if t == "list":
        return "các ô " + ", ".join(region["cells"])
    return f"vùng {t}"


_TEXT_KEYS = ("text", "message", "content", "statement", "line", "sentence", "clue", "value", "noise")
_WRAPPED = re.compile(r"^\s*\{\s*noise\s*:\s*(.*?)\s*\}\s*$", re.IGNORECASE | re.DOTALL)


def free_text(clue: Clue) -> Optional[str]:
    """Dòng chữ tự do bên trong clue "nhiễu" (NOISE), không có cấu trúc để diễn giải.

    Tìm theo các khóa quen thuộc trong params (hoặc thuộc tính text của clue), không có thì lấy chuỗi
    đầu tiên; bóc lớp vỏ "{Noise: ...}" nếu dữ liệu lưu nguyên như vậy. Không tìm được thì trả None."""
    params = clue.params
    if isinstance(params, str):
        found = params
    else:
        found = getattr(clue, "text", None)
        if not isinstance(found, str):
            values = params if isinstance(params, dict) else {}
            found = next((values[k] for k in _TEXT_KEYS if isinstance(values.get(k), str)), None)
            if found is None:
                found = next((v for v in values.values() if isinstance(v, str)), None)
    if found is None:
        return None
    match = _WRAPPED.match(found)
    return (match.group(1) if match else found).strip() or None


def format_clue_text(clue: Clue, names: Optional[Dict[str, str]] = None) -> str:
    """Câu mô tả clue (dùng trên thẻ, danh sách clue và sổ tay)."""
    p, t = clue.params, clue.type
    if t == "FACT":
        return f"{_who(p['target'], names)} là {STATUS_VN[clue_status(clue)].lower()}."
    if t in ("SAME_STATUS", "DIFFERENT_STATUS"):
        word = "cùng" if t == "SAME_STATUS" else "khác"
        return f"{_who(p['cell1'], names)} và {_who(p['cell2'], names)} có trạng thái {word} nhau."
    if t in COUNT_WORD_VN:
        noun, reg, k = _noun(clue_status(clue)), region_text(p["region"], names), p["k"]
        if t == "EXACTLY" and k == 0:
            return f"Không có {noun} nào trong {reg}."
        return f"Có {COUNT_WORD_VN[t]} {k} {noun} trong {reg}."
    if t == "PARITY":
        noun = _noun(clue_status(clue))
        return f"Số {noun} trong {region_text(p['region'], names)} là số {PARITY_VN[p['parity']]}."
    if t == "COMPARE":
        noun = _noun(clue_status(clue))
        return (f"Số {noun} ở {region_text(p['region1'], names)} "
                f"{COMPARE_VN[p['op']]} số {noun} ở {region_text(p['region2'], names)}.")
    text = free_text(clue)
    return text if text is not None else f"{t} {p}"


def cells_of_clue(clue: Clue, n: int) -> List[str]:
    """Các ô clue nhắc tới (GUI dùng để highlight), row-major. Dùng thẳng engine.clue.clue_cells."""
    return clue_cells(clue, n)