"""Lưới N x N và tọa độ (Scope A, việc A1).

Quy ước (CẢ NHÓM PHẢI TUÂN THEO):
  - Cell id: "<cột><hàng>", cột là chữ cái A.., hàng là số 1.. từ trên xuống. VD "C2".
  - Index row-major: idx = hàng_idx * N + cột_idx, bắt đầu từ 0.
  - Biến SAT primary của nhân vật tại cell = idx + 1  (1..N*N).
  - Biến phụ (auxiliary) bắt đầu từ N*N + 1.
"""
from typing import List, Tuple

COLS = "ABCDEFGHIJ"


def parse_cell(cell: str) -> Tuple[int, int]:
    """'C2' -> (row=1, col=2), 0-based. Không kiểm tra phạm vi lưới.

    Raises:
        ValueError: nếu không đúng dạng <chữ><số>.
    """
    if len(cell) < 2 or not cell[1:].isdigit() or cell[0].upper() not in COLS:
        raise ValueError(f"Cell id không hợp lệ: {cell!r}")
    return int(cell[1:]) - 1, COLS.index(cell[0].upper())


def cell_id(row: int, col: int) -> str:
    """(row=1, col=2) -> 'C2' (0-based vào, id ra)."""
    return f"{COLS[col]}{row + 1}"


def in_bounds(n: int, row: int, col: int) -> bool:
    """True nếu (row, col) 0-based nằm trong lưới n x n."""
    return 0 <= row < n and 0 <= col < n


def is_valid_cell(cell: str, n: int) -> bool:
    """True nếu cell đúng dạng chuẩn (chữ hoa, không số 0 thừa) và nằm trong lưới n x n."""
    try:
        r, c = parse_cell(cell)
    except ValueError:
        return False
    return in_bounds(n, r, c) and cell_id(r, c) == cell


def all_cells(n: int) -> List[str]:
    """Mọi ô của lưới, thứ tự row-major."""
    return [cell_id(r, c) for r in range(n) for c in range(n)]


def cell_index(cell: str, n: int) -> int:
    """Index row-major (0-based) của ô. Raises ValueError nếu ô ngoài lưới."""
    r, c = parse_cell(cell)
    if not in_bounds(n, r, c):
        raise ValueError(f"Ô {cell} ngoài lưới {n}x{n}")
    return r * n + c


def var_of(cell: str, n: int) -> int:
    """Biến SAT primary (1-based) của nhân vật ở ô cell."""
    return cell_index(cell, n) + 1


def cell_of_var(var: int, n: int) -> str:
    """Ngược của var_of. Raises ValueError nếu var không phải biến primary (1..N*N)."""
    if not 1 <= var <= n * n:
        raise ValueError(f"Biến {var} không phải biến primary của lưới {n}x{n}")
    return cell_id(*divmod(var - 1, n))


def first_aux_var(n: int) -> int:
    """Số hiệu biến phụ đầu tiên (N*N + 1)."""
    return n * n + 1


def row_cells(n: int, row_number: int) -> List[str]:
    """Các ô của một hàng (row_number 1-based), từ trái sang phải."""
    if not 1 <= row_number <= n:
        raise ValueError(f"Hàng {row_number} ngoài lưới {n}x{n}")
    return [cell_id(row_number - 1, c) for c in range(n)]


def col_cells(n: int, col_letter: str) -> List[str]:
    """Các ô của một cột (chữ cái), từ trên xuống."""
    c = COLS.find(col_letter.upper())
    if col_letter == "" or not 0 <= c < n:
        raise ValueError(f"Cột {col_letter!r} ngoài lưới {n}x{n}")
    return [cell_id(r, c) for r in range(n)]


def neighbor_cells(n: int, cell: str) -> List[str]:
    """8 hướng, không gồm chính nó, theo thứ tự row-major. Raises ValueError nếu ô ngoài lưới."""
    cell_index(cell, n)  # chỉ để validate
    r0, c0 = parse_cell(cell)
    return [
        cell_id(r, c)
        for r in range(r0 - 1, r0 + 2)
        for c in range(c0 - 1, c0 + 2)
        if (r, c) != (r0, c0) and in_bounds(n, r, c)
    ]