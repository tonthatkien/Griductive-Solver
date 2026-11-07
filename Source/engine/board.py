"""Lưới N x N và tọa độ. (Scope A, việc A1 - đã viết sẵn phần cơ bản, cần review/bổ sung)

Quy ước (CẢ NHÓM PHẢI TUÂN THEO):
  - Cell id: "<cột><hàng>", cột là chữ cái A.., hàng là số 1.. từ trên xuống. VD "C2".
  - Index row-major: idx = (hàng-1)*N + cột_idx, bắt đầu từ 0.
  - Biến SAT của nhân vật tại cell = idx + 1  (primary variables: 1..N*N).
  - Biến phụ (auxiliary) bắt đầu từ N*N + 1.
"""
from typing import List, Tuple

COLS = "ABCDEFGHIJ"


def parse_cell(cell: str) -> Tuple[int, int]:
    """'C2' -> (row=1, col=2) (0-based)."""
    col = COLS.index(cell[0].upper())
    row = int(cell[1:]) - 1
    return row, col


def cell_id(row: int, col: int) -> str:
    return f"{COLS[col]}{row + 1}"


def all_cells(n: int) -> List[str]:
    """Thứ tự row-major."""
    return [cell_id(r, c) for r in range(n) for c in range(n)]


def in_bounds(n: int, row: int, col: int) -> bool:
    return 0 <= row < n and 0 <= col < n


def cell_index(cell: str, n: int) -> int:
    r, c = parse_cell(cell)
    return r * n + c


def var_of(cell: str, n: int) -> int:
    """Biến SAT (1-based) của nhân vật ở ô cell."""
    return cell_index(cell, n) + 1


def cell_of_var(var: int, n: int) -> str:
    return all_cells(n)[var - 1]


def row_cells(n: int, row_number: int) -> List[str]:
    """row_number 1-based."""
    return [cell_id(row_number - 1, c) for c in range(n)]


def col_cells(n: int, col_letter: str) -> List[str]:
    c = COLS.index(col_letter.upper())
    return [cell_id(r, c) for r in range(n)]


def neighbor_cells(n: int, cell: str) -> List[str]:
    """8 hướng, không gồm chính nó, theo thứ tự row-major."""
    r0, c0 = parse_cell(cell)
    out = []
    for r in range(r0 - 1, r0 + 2):
        for c in range(c0 - 1, c0 + 2):
            if (r, c) != (r0, c0) and in_bounds(n, r, c):
                out.append(cell_id(r, c))
    return out
