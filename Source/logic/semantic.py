"""Semantic evaluator: kiểm tra tính đúng đắn của clue trên một assignment.
"""
import operator
from typing import Any, Callable, Dict, List, Sequence, Tuple

from engine import board
from engine.clue import (
    Clue,
    COMPARE_OPS,
    DEFAULT_STATUS,
    PARITIES,
    _check_region,
)
from engine.constants import CRIMINAL, STATUSES

# Bảng ánh xạ toán tử so sánh cho clue COMPARE 
_COMPARE_FUNCS: Dict[str, Callable[[int, int], bool]] = {
    "GT": operator.gt,
    "GE": operator.ge,
    "EQ": operator.eq,
    "LE": operator.le,
    "LT": operator.lt,
}

# Giữ alias PARITY_VALUES để đảm bảo tương thích ngược
PARITY_VALUES = PARITIES


def _extract_clue_data(clue: Any) -> Tuple[str, Dict[str, Any]]:
    """Trích xuất loại clue và từ điển tham số từ đối tượng Clue hoặc dict.

    Args:
        clue: Đối tượng Clue hoặc dict đại diện cho clue.

    Returns:
        Tuple gồm (clue_type, params_dict).

    Raises:
        TypeError: Nếu clue không phải là Clue hoặc dict.
        ValueError: Nếu clue thiếu trường 'type' hoặc trường 'type' không phải chuỗi (str).
    """
    if isinstance(clue, Clue):
        clue_type = clue.type
        params = dict(clue.params)
    elif isinstance(clue, dict):
        params = dict(clue)
        clue_type = params.pop("type", None)
        if clue_type is None:
            raise ValueError("Clue dict thiếu trường 'type'")
    else:
        raise TypeError(f"Clue phải là Clue hoặc dict, nhận được: {type(clue).__name__}")

    if not isinstance(clue_type, str):
        raise ValueError(
            f"Trường 'type' của clue phải là chuỗi ký tự (str), nhận được: {clue_type!r} "
            f"({type(clue_type).__name__})"
        )

    return clue_type, params


def resolve_region_cells(region: Dict[str, Any], n: int) -> List[str]:
    """Phân giải đặc tả region thành danh sách cell ID duy nhất theo thứ tự row-major.

    Tái sử dụng logic kiểm tra và phân giải vùng từ engine.clue._check_region để đảm bảo
    đồng nhất 100% với game engine và loại bỏ mã trùng lặp.

    Args:
        region: Dict mô tả vùng.
        n: Kích thước lưới n x n.

    Returns:
        Danh sách cell ID không trùng, không rỗng, sắp xếp theo thứ tự row-major.

    Raises:
        ValueError: Nếu region sai cấu trúc, có ô trùng lặp, ô ngoài lưới, hoặc rỗng.
    """
    return _check_region(region, n, "region")


def _validate_k(k: Any, num_cells: int) -> int:
    """Kiểm tra k là số nguyên và nằm trong phạm vi [0, |R|].

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

    Ngăn ngừa lỗi ép kiểu âm thầm.

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
    """Đánh giá trực tiếp clue FACT.

    Điều kiện: target có trạng thái bằng status (CRIMINAL / INNOCENT).
    """
    _, params = _extract_clue_data(clue)
    if "target" not in params:
        raise ValueError(f"FACT clue thiếu ô mục tiêu 'target': {params}")
    target = params["target"]
    if not isinstance(target, str) or not board.is_valid_cell(target, n):
        raise ValueError(f"Ô target {target!r} không hợp lệ hoặc không nằm trong lưới {n}x{n}")

    if "status" not in params:
        raise ValueError(f"FACT clue bắt buộc phải có trường 'status': {params}")
    status = params["status"]
    if status not in STATUSES:
        raise ValueError(f"Status không hợp lệ: {status!r}. Cần thuộc {STATUSES}")

    val = _get_cell_bool(assignment, target)
    expected_bool = (status == CRIMINAL)
    return val == expected_bool


def eval_same_status(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue SAME_STATUS.

    Điều kiện: cell1 và cell2 có cùng trạng thái (cùng True hoặc cùng False),
    với cell1 khác cell2 theo quy ước docs/INTERFACES.md mục 2.4.
    """
    _, params = _extract_clue_data(clue)
    if "cell1" not in params or "cell2" not in params:
        raise ValueError(f"Clue SAME_STATUS thiếu cell1/cell2: {params}")
    c1, c2 = params["cell1"], params["cell2"]
    if (
        not isinstance(c1, str)
        or not isinstance(c2, str)
        or not board.is_valid_cell(c1, n)
        or not board.is_valid_cell(c2, n)
    ):
        raise ValueError(
            f"Ô không hợp lệ trong clue SAME_STATUS: ({c1!r}, {c2!r}) trên lưới {n}x{n}"
        )
    if c1 == c2:
        raise ValueError(
            f"Clue SAME_STATUS yêu cầu 2 ô khác nhau, nhận được trùng ô: {c1!r}"
        )

    val1 = _get_cell_bool(assignment, c1)
    val2 = _get_cell_bool(assignment, c2)
    return val1 == val2


def eval_different_status(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue DIFFERENT_STATUS.

    Điều kiện: cell1 và cell2 có trạng thái khác nhau (một True một False),
    với cell1 khác cell2 theo quy ước docs/INTERFACES.md mục 2.4.
    """
    _, params = _extract_clue_data(clue)
    if "cell1" not in params or "cell2" not in params:
        raise ValueError(f"Clue DIFFERENT_STATUS thiếu cell1/cell2: {params}")
    c1, c2 = params["cell1"], params["cell2"]
    if (
        not isinstance(c1, str)
        or not isinstance(c2, str)
        or not board.is_valid_cell(c1, n)
        or not board.is_valid_cell(c2, n)
    ):
        raise ValueError(
            f"Ô không hợp lệ trong clue DIFFERENT_STATUS: ({c1!r}, {c2!r}) trên lưới {n}x{n}"
        )
    if c1 == c2:
        raise ValueError(
            f"Clue DIFFERENT_STATUS yêu cầu 2 ô khác nhau, nhận được trùng ô: {c1!r}"
        )

    val1 = _get_cell_bool(assignment, c1)
    val2 = _get_cell_bool(assignment, c2)
    return val1 != val2


def _count_clue_status(
    clue: Any, assignment: Dict[str, bool], n: int
) -> Tuple[int, int]:
    """Trích xuất tham số và đếm số ô khớp trạng thái cho clue đếm (EXACTLY, AT_LEAST, AT_MOST).

    Returns:
        Tuple gồm (count, k).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue đếm thiếu 'region': {params}")
    if "k" not in params:
        raise ValueError(f"Clue đếm thiếu 'k': {params}")

    cells = resolve_region_cells(params["region"], n)
    k = _validate_k(params["k"], len(cells))
    status = params.get("status", DEFAULT_STATUS)
    if status not in STATUSES:
        raise ValueError(
            f"Status không hợp lệ trong clue đếm: {status!r}. Phải thuộc {STATUSES}"
        )
    count = count_status_matches(cells, status, assignment)
    return count, k


def eval_exactly(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue EXACTLY.

    Điều kiện: số ô trong region có trạng thái status đúng bằng k (0 <= k <= |R|).
    Ghi chú: hàm này được thiết kế để gọi trực tiếp hoặc thông qua evaluate().
    """
    count, k = _count_clue_status(clue, assignment, n)
    return count == k


def eval_at_least(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue AT_LEAST.

    Điều kiện: số ô trong region có trạng thái status >= k (0 <= k <= |R|).
    Ghi chú: hàm này được thiết kế để gọi trực tiếp hoặc thông qua evaluate().
    """
    count, k = _count_clue_status(clue, assignment, n)
    return count >= k


def eval_at_most(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue AT_MOST.

    Điều kiện: số ô trong region có trạng thái status <= k (0 <= k <= |R|).
    Ghi chú: hàm này được thiết kế để gọi trực tiếp hoặc thông qua evaluate().
    """
    count, k = _count_clue_status(clue, assignment, n)
    return count <= k


def eval_parity(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue extension PARITY.

    Điều kiện: số ô trong region có trạng thái status là chẵn (EVEN) hoặc lẻ (ODD).
    Quy ước docs/INTERFACES.md: count = 0 được tính là EVEN (chẵn).
    """
    _, params = _extract_clue_data(clue)
    if "region" not in params:
        raise ValueError(f"Clue PARITY thiếu 'region': {params}")
    if "parity" not in params:
        raise ValueError(f"Clue PARITY thiếu 'parity': {params}")
    parity = params["parity"]
    if parity not in PARITIES:
        raise ValueError(f"Giá trị parity {parity!r} không hợp lệ, cần thuộc {PARITIES}")

    status = params.get("status", DEFAULT_STATUS)
    if status not in STATUSES:
        raise ValueError(
            f"Status không hợp lệ trong clue PARITY: {status!r}. Phải thuộc {STATUSES}"
        )

    cells = resolve_region_cells(params["region"], n)
    count = count_status_matches(cells, status, assignment)

    if parity == "EVEN":
        return count % 2 == 0
    return count % 2 == 1


def eval_compare(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá trực tiếp clue extension COMPARE.

    Điều kiện: so sánh count(region1) op count(region2) cho trạng thái status.
    Toán tử hợp lệ: GT (>), GE (>=), EQ (==), LE (<=), LT (<).
    """
    _, params = _extract_clue_data(clue)
    if "region1" not in params:
        raise ValueError(f"Clue COMPARE thiếu 'region1': {params}")
    if "region2" not in params:
        raise ValueError(f"Clue COMPARE thiếu 'region2': {params}")

    op = params.get("op")
    if op not in COMPARE_OPS or op not in _COMPARE_FUNCS:
        raise ValueError(f"Toán tử so sánh {op!r} không hợp lệ, cần thuộc {COMPARE_OPS}")

    status = params.get("status", DEFAULT_STATUS)
    if status not in STATUSES:
        raise ValueError(
            f"Status không hợp lệ trong clue COMPARE: {status!r}. Phải thuộc {STATUSES}"
        )

    cells1 = resolve_region_cells(params["region1"], n)
    cells2 = resolve_region_cells(params["region2"], n)
    count1 = count_status_matches(cells1, status, assignment)
    count2 = count_status_matches(cells2, status, assignment)

    return _COMPARE_FUNCS[op](count1, count2)


CLUE_EVALUATORS: Dict[str, Callable[[Any, Dict[str, bool], int], bool]] = {
    "FACT": eval_fact,
    "SAME_STATUS": eval_same_status,
    "DIFFERENT_STATUS": eval_different_status,
    "EXACTLY": eval_exactly,
    "AT_LEAST": eval_at_least,
    "AT_MOST": eval_at_most,
    "PARITY": eval_parity,
    "COMPARE": eval_compare,
}


def evaluate(clue: Any, assignment: Dict[str, bool], n: int) -> bool:
    """Đánh giá clue đúng hay sai dựa trên assignment, KHÔNG gọi CNF encoder.

    Args:
        clue: Đối tượng Clue hoặc dict đại diện cho clue.
        assignment: Dict ánh xạ cell id -> bool (True = CRIMINAL, False = INNOCENT).
            Nhận assignment đầy đủ hoặc assignment một phần (tối thiểu chứa các ô
            mà clue nhắc tới).
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
        True nếu assignment thỏa mãn các clues, False nếu có ít nhất một clue vi phạm.
    """
    return all(evaluate(clue, assignment, n) for clue in clues)
