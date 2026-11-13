"""Semantic evaluator: kiểm tra tính đúng đắn của clue trên một assignment đầy đủ.

Module này thực hiện đánh giá trực tiếp ngữ nghĩa của từng clue mà KHÔNG sử dụng
CNF encoder (theo yêu cầu kiểm chứng độc lập của Task D5 và D6).
Dùng chung cho brute force checker và kiểm chứng chéo với encoder trong test.
"""
from typing import Any, Callable, Dict, List, Sequence, Tuple

from engine import board
from engine.clue import Clue
from engine.constants import CRIMINAL, INNOCENT, STATUSES

# Toán tử so sánh hợp lệ cho clue COMPARE
COMPARE_OPS = ("GT", "GE", "EQ", "LE", "LT")

# Giá trị chẵn/lẻ hợp lệ cho clue PARITY
PARITY_VALUES = ("EVEN", "ODD")


def _extract_clue_data(clue: Any) -> Tuple[str, Dict[str, Any]]:
    """Trích xuất loại clue và từ điển tham số từ đối tượng Clue hoặc dict.

    Args:
        clue: Đối tượng Clue hoặc dict đại diện cho clue.

    Returns:
        Tuple gồm (clue_type, params_dict).

    Raises:
        TypeError: Nếu clue không phải là Clue hoặc dict.
        ValueError: Nếu clue thiếu trường 'type'.
    """
    if isinstance(clue, Clue):
        return clue.type, dict(clue.params)
    if isinstance(clue, dict):
        params = dict(clue)
        clue_type = params.pop("type", None)
        if not clue_type:
            raise ValueError("Clue dict thiếu trường 'type'")
        return clue_type, params
    raise TypeError(f"Clue phải là Clue hoặc dict, nhận được: {type(clue).__name__}")


def resolve_region_cells(region: Dict[str, Any], n: int) -> List[str]:
    """Phân giải đặc tả region thành danh sách cell ID duy nhất theo thứ tự row-major.

    Hỗ trợ cả chuẩn docs/INTERFACES.md và engine/clue.py:
      - row: {"number": 1} hoặc {"index": 1}
      - col: {"letter": "B"} hoặc {"index": "B"}
      - neighbors: {"cell": "C2"}
      - list / cells: {"cells": ["A1", "B2"]}

    Bắt lỗi vùng rỗng, ô trùng lặp, ô ngoài lưới, hoặc sai kiểu dữ liệu
    theo docs/INTERFACES.md mục 2.4 và docs/REVIEW_GUIDE.md.

    Args:
        region: Dict mô tả vùng.
        n: Kích thước lưới n x n.

    Returns:
        Danh sách cell ID không trùng, không rỗng, sắp xếp theo row-major.

    Raises:
        ValueError: Nếu region sai cấu trúc, có ô trùng lặp, ô ngoài lưới, hoặc rỗng.
    """
    if not isinstance(region, dict) or "type" not in region:
        raise ValueError(f"Đặc tả region không hợp lệ: {region!r}")

    rtype = region["type"]
    if rtype == "row":
        num = region.get("number") if "number" in region else region.get("index")
        if num is None:
            raise ValueError(f"Region 'row' cần trường 'number' hoặc 'index': {region}")
        if isinstance(num, bool) or not isinstance(num, int):
            raise ValueError(
                f"Số hàng (row number) phải là số nguyên (int), nhận được: {num!r} "
                f"({type(num).__name__})"
            )
        if not (1 <= num <= n):
            raise ValueError(f"Số hàng {num} nằm ngoài phạm vi lưới [1, {n}]")
        cells = board.row_cells(n, num)
    elif rtype == "col":
        letter = region.get("letter") if "letter" in region else region.get("index")
        if letter is None:
            raise ValueError(f"Region 'col' cần trường 'letter' hoặc 'index': {region}")
        if not isinstance(letter, str) or len(letter) != 1 or not letter.isupper():
            raise ValueError(
                f"Ký tự cột (col letter) phải là chữ cái viết hoa 1 ký tự, nhận được: {letter!r}"
            )
        if letter not in board.COLS[:n]:
            raise ValueError(f"Cột {letter!r} nằm ngoài phạm vi lưới {n}x{n}")
        cells = board.col_cells(n, letter)
    elif rtype == "neighbors":
        cell = region.get("cell")
        if cell is None:
            raise ValueError(f"Region 'neighbors' cần trường 'cell': {region}")
        if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
            raise ValueError(f"Ô tâm {cell!r} trong neighbors không hợp lệ cho lưới {n}x{n}")
        cells = board.neighbor_cells(n, cell)
    elif rtype in ("list", "cells"):
        raw_cells = region.get("cells")
        if raw_cells is None:
            raise ValueError(f"Region '{rtype}' thiếu danh sách 'cells': {region}")
        if not isinstance(raw_cells, (list, tuple)):
            raise ValueError(f"Trường 'cells' phải là list hoặc tuple, nhận được: {raw_cells!r}")
        # Kiểm tra từng ô hợp lệ trước khi hash để tránh TypeError với kiểu unhashable
        for c in raw_cells:
            if not isinstance(c, str) or not board.is_valid_cell(c, n):
                raise ValueError(f"Cell {c!r} trong region không hợp lệ cho lưới {n}x{n}")
        # Bắt buộc kiểm tra trùng lặp theo docs/INTERFACES.md mục 2.4 quy tắc 8
        if len(raw_cells) != len(set(raw_cells)):
            raise ValueError(f"Các ô trong region '{rtype}' không được trùng nhau: {raw_cells}")
        cells = list(raw_cells)
    else:
        raise ValueError(f"Loại region không hợp lệ: {rtype!r}")

    order = {c: i for i, c in enumerate(board.all_cells(n))}
    resolved = sorted(cells, key=lambda c: order[c])
    if not resolved:
        raise ValueError(f"Vùng không được rỗng (0 ô hợp lệ): {region!r}")
    return resolved


def _validate_k(k: Any, num_cells: int) -> int:
    """Kiểm tra k là số nguyên và nằm trong phạm vi [0, |R|].

    Theo docs/INTERFACES.md mục 2.4 quy tắc 4:
      0 <= k <= |R| với |R| là số ô của vùng (và k là int).

    Args:
        k: Giá trị k cần kiểm tra.
        num_cells: Số lượng ô của vùng (|R|).

    Returns:
        Giá trị k hợp lệ dạng int.

    Raises:
        ValueError: Nếu k không phải là int hoặc nằm ngoài [0, num_cells].
    """
    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError(
            f"Tham số 'k' phải là số nguyên (int), nhận được: {k!r} ({type(k).__name__})"
        )
    if not (0 <= k <= num_cells):
        raise ValueError(
            f"Tham số 'k'={k} nằm ngoài phạm vi cho phép [0, |R|={num_cells}]"
        )
    return k


def _get_cell_bool(assignment: Dict[str, bool], cell: str) -> bool:
    """Lấy giá trị của ô trong assignment và kiểm tra nghiêm ngặt kiểu bool.

    Ngăn ngừa lỗi ép kiểu âm thầm (ví dụ: chuỗi 'False', 'True', số 0, 1, None).

    Args:
        assignment: Dict cell -> bool.
        cell: Tọa độ ô cần lấy.

    Returns:
        Giá trị boolean thuần túy (True hoặc False).

    Raises:
        KeyError: Nếu ô cell không có trong assignment.
        TypeError: Nếu giá trị của ô không phải kiểu bool thuần túy.
    """
    if cell not in assignment:
        raise KeyError(f"Ô {cell} chưa có trong assignment")
    val = assignment[cell]
    if not isinstance(val, bool):
        raise TypeError(
            f"Giá trị của ô {cell!r} trong assignment phải là kiểu bool (True/False), "
            f"nhận được: {val!r} ({type(val).__name__})"
        )
    return val


def count_status_matches(
    cells: Sequence[str],
    status: str,
    assignment: Dict[str, bool],
) -> int:
    """Đếm số ô trong danh sách có trạng thái khớp với status chỉ định.

    Quy ước: True = CRIMINAL, False = INNOCENT.

    Args:
        cells: Danh sách cell ID cần kiểm tra.
        status: CRIMINAL hoặc INNOCENT.
        assignment: Phép gán cell -> bool.

    Returns:
        Số lượng ô có giá trị bằng trạng thái mong muốn.
    """
    if status not in STATUSES:
        raise ValueError(f"Status không hợp lệ: {status!r}. Phải là một trong {STATUSES}")
    expected_bool = (status == CRIMINAL)
    count = 0
    for cell in cells:
        val = _get_cell_bool(assignment, cell)
        if val == expected_bool:
            count += 1
    return count


def eval_fact(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue FACT (Task D5).

    Điều kiện: target có trạng thái bằng status (CRIMINAL / INNOCENT).
    """
    _, params = _extract_clue_data(clue)
    target = params.get("target") or params.get("cell")
    if not target:
        raise ValueError(f"FACT clue thiếu ô mục tiêu (target/cell): {params}")
    if not isinstance(target, str) or not board.is_valid_cell(target, n):
        raise ValueError(f"Ô target {target!r} không hợp lệ hoặc không nằm trong lưới {n}x{n}")

    status = params.get("status")
    if status is None:
        raise ValueError(f"FACT clue bắt buộc phải có trường 'status': {params}")
    if status not in STATUSES:
        raise ValueError(f"Status không hợp lệ: {status!r}. Cần thuộc {STATUSES}")

    val = _get_cell_bool(assignment, target)
    expected_bool = (status == CRIMINAL)
    return val == expected_bool


def eval_same_status(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue SAME / SAME_STATUS (Task D5).

    Điều kiện: cell1 và cell2 có cùng trạng thái (cùng True hoặc cùng False),
    với cell1 khác cell2 theo quy ước docs/INTERFACES.md mục 2.4.
    """
    _, params = _extract_clue_data(clue)
    c1 = params.get("cell1") or params.get("a")
    c2 = params.get("cell2") or params.get("b")
    if not c1 or not c2:
        raise ValueError(f"Clue SAME thiếu cell1/cell2 (hoặc a/b): {params}")
    if (
        not isinstance(c1, str)
        or not isinstance(c2, str)
        or not board.is_valid_cell(c1, n)
        or not board.is_valid_cell(c2, n)
    ):
        raise ValueError(f"Ô không hợp lệ trong clue SAME: ({c1!r}, {c2!r}) trên lưới {n}x{n}")
    if c1 == c2:
        raise ValueError(f"Clue SAME yêu cầu 2 ô khác nhau, nhận được trùng ô: {c1!r}")

    val1 = _get_cell_bool(assignment, c1)
    val2 = _get_cell_bool(assignment, c2)
    return val1 == val2


def eval_different_status(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue DIFFERENT / DIFFERENT_STATUS (Task D5).

    Điều kiện: cell1 và cell2 có trạng thái khác nhau, với cell1 khác cell2
    theo quy ước docs/INTERFACES.md mục 2.4.
    """
    _, params = _extract_clue_data(clue)
    c1 = params.get("cell1") or params.get("a")
    c2 = params.get("cell2") or params.get("b")
    if not c1 or not c2:
        raise ValueError(f"Clue DIFFERENT thiếu cell1/cell2 (hoặc a/b): {params}")
    if (
        not isinstance(c1, str)
        or not isinstance(c2, str)
        or not board.is_valid_cell(c1, n)
        or not board.is_valid_cell(c2, n)
    ):
        raise ValueError(f"Ô không hợp lệ trong clue DIFFERENT: ({c1!r}, {c2!r}) trên lưới {n}x{n}")
    if c1 == c2:
        raise ValueError(f"Clue DIFFERENT yêu cầu 2 ô khác nhau, nhận được trùng ô: {c1!r}")

    val1 = _get_cell_bool(assignment, c1)
    val2 = _get_cell_bool(assignment, c2)
    return val1 != val2


def eval_exactly(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue EXACTLY (Task D5).

    Điều kiện: số ô trong region có trạng thái status đúng bằng k (với 0 <= k <= |R|).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue EXACTLY thiếu 'region': {params}")
    if "k" not in params:
        raise ValueError(f"Clue EXACTLY thiếu 'k': {params}")

    cells = resolve_region_cells(params["region"], n)
    k = _validate_k(params["k"], len(cells))
    status = params.get("status", CRIMINAL)
    count = count_status_matches(cells, status, assignment)
    return count == k


def eval_at_least(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue AT_LEAST (Task D5).

    Điều kiện: số ô trong region có trạng thái status >= k (với 0 <= k <= |R|).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue AT_LEAST thiếu 'region': {params}")
    if "k" not in params:
        raise ValueError(f"Clue AT_LEAST thiếu 'k': {params}")

    cells = resolve_region_cells(params["region"], n)
    k = _validate_k(params["k"], len(cells))
    status = params.get("status", CRIMINAL)
    count = count_status_matches(cells, status, assignment)
    return count >= k


def eval_at_most(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue AT_MOST (Task D5).

    Điều kiện: số ô trong region có trạng thái status <= k (với 0 <= k <= |R|).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue AT_MOST thiếu 'region': {params}")
    if "k" not in params:
        raise ValueError(f"Clue AT_MOST thiếu 'k': {params}")

    cells = resolve_region_cells(params["region"], n)
    k = _validate_k(params["k"], len(cells))
    status = params.get("status", CRIMINAL)
    count = count_status_matches(cells, status, assignment)
    return count <= k


def eval_parity(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue extension PARITY (Task D6).

    Điều kiện: số ô trong region có trạng thái status là chẵn (EVEN) hoặc lẻ (ODD).
    Quy ước docs/INTERFACES.md: count = 0 được tính là EVEN (chẵn).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue PARITY thiếu 'region': {params}")
    parity = params.get("parity")
    if parity not in PARITY_VALUES:
        raise ValueError(f"Giá trị parity {parity!r} không hợp lệ, cần thuộc {PARITY_VALUES}")

    cells = resolve_region_cells(params["region"], n)
    status = params.get("status", CRIMINAL)
    count = count_status_matches(cells, status, assignment)

    if parity == "EVEN":
        return count % 2 == 0
    return count % 2 == 1


def eval_compare(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue extension COMPARE (Task D6).

    Điều kiện: so sánh count(region1) op count(region2) cho trạng thái status.
    Toán tử hợp lệ: GT (>), GE (>=), EQ (==), LE (<=), LT (<).
    """
    _, params = _extract_clue_data(clue)
    r1 = params.get("region1") or params.get("left")
    r2 = params.get("region2") or params.get("right")
    if not r1 or not r2:
        raise ValueError(f"Clue COMPARE thiếu region1/region2 (hoặc left/right): {params}")

    op = params.get("op")
    if op not in COMPARE_OPS:
        raise ValueError(f"Toán tử so sánh {op!r} không hợp lệ, cần thuộc {COMPARE_OPS}")

    cells1 = resolve_region_cells(r1, n)
    cells2 = resolve_region_cells(r2, n)
    status = params.get("status", CRIMINAL)
    count1 = count_status_matches(cells1, status, assignment)
    count2 = count_status_matches(cells2, status, assignment)

    if op == "GT":
        return count1 > count2
    if op == "GE":
        return count1 >= count2
    if op == "EQ":
        return count1 == count2
    if op == "LE":
        return count1 <= count2
    if op == "LT":
        return count1 < count2
    return False


# Các bí danh viết ngắn gọn theo tên template trong đề
eval_same = eval_same_status
eval_different = eval_different_status

CLUE_EVALUATORS: Dict[str, Callable[[Any, Dict[str, bool], int], bool]] = {
    "FACT": eval_fact,
    "SAME": eval_same_status,
    "SAME_STATUS": eval_same_status,
    "DIFFERENT": eval_different_status,
    "DIFFERENT_STATUS": eval_different_status,
    "EXACTLY": eval_exactly,
    "AT_LEAST": eval_at_least,
    "AT_MOST": eval_at_most,
    "PARITY": eval_parity,
    "COMPARE": eval_compare,
}


def evaluate(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá clue đúng hay sai dựa trên assignment đầy đủ, KHÔNG gọi CNF encoder.

    Args:
        clue: Đối tượng Clue hoặc dict đại diện cho clue.
        assignment: Dict ánh xạ cell id -> bool (True = CRIMINAL, False = INNOCENT).
        n: Kích thước lưới n x n.

    Returns:
        True nếu assignment thỏa mãn clue, False nếu không thỏa.

    Raises:
        ValueError: Nếu loại clue hoặc tham số không hợp lệ.
        KeyError: Nếu ô cần thiết chưa có trong assignment.
        TypeError: Nếu clue sai kiểu dữ liệu.
    """
    clue_type, _ = _extract_clue_data(clue)
    evaluator = CLUE_EVALUATORS.get(clue_type)
    if evaluator is None:
        raise ValueError(f"Không hỗ trợ loại clue: {clue_type!r}")
    return evaluator(clue, assignment, n)


def evaluate_all(clues: Sequence[Any], assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá tập hợp nhiều clues trên cùng một assignment.

    Dùng cho brute force solver và kiểm tra nghiệm puzzle.

    Args:
        clues: Chuỗi các clues (dạng Clue hoặc dict).
        assignment: Dict ánh xạ cell id -> bool.
        n: Kích thước lưới n x n.

    Returns:
        True nếu assignment thỏa mãn TẤT CẢ các clues, False nếu có ít nhất một clue vi phạm.
    """
    return all(evaluate(clue, assignment, n) for clue in clues)
