"""Logic Agent: phân loại trạng thái chỉ từ PublicKB bằng SAT entailment.

E1 kiểm tra KB trước khi thử giả định đối lập; không coi một model SAT là bằng
chứng về trạng thái. Timeout được truyền ra bằng TimeoutError, không thành UNSAT.
E2 chọn ô forced theo row-major và cập nhật PublicKB sau từng verdict ACCEPTED.
Các chức năng E3/E4/E5 vẫn giữ stub, triển khai ở task riêng.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Callable, List, Literal, Protocol

from engine import board
from engine.constants import ACCEPTED, CRIMINAL, INCONSISTENT, INNOCENT, UNKNOWN
from engine.game_state import PublicKB
from logic.cnf_encoder import Encoder, KB
from logic.dpll import DPLLSolver, SolveResult, SolverStats

SAT, UNSAT, TIMEOUT = "SAT", "UNSAT", "TIMEOUT"
SOLVED, STUCK = "SOLVED", "STUCK"


class RevealEngine(Protocol):
    """Hai phương thức công khai duy nhất mà vòng lặp cần từ engine."""

    def get_public_kb(self) -> PublicKB:
        """Lấy snapshot thông tin công khai."""
        ...

    def submit_verdict(
        self, cell: str, verdict: str, classify: Callable[[PublicKB, str], str]
    ) -> str:
        """Engine kiểm chứng verdict trước khi công khai clue tiếp theo."""
        ...


@dataclass(frozen=True)
class SatQuery:
    """Một truy vấn DPLL đã trả kết quả; stats là bản sao độc lập."""

    cell: str
    assumptions: tuple[int, ...]
    status: Literal["SAT", "UNSAT", "TIMEOUT"]
    stats: SolverStats


@dataclass
class TraceEntry:
    """Cấu trúc trace sẵn có, dành cho task E3."""

    step: int
    active_clue_ids: List[str]
    sat_queries: List[tuple] = field(default_factory=list)
    cell: str = ""
    verdict: str = ""
    newly_revealed_clue_id: str = ""


class LogicAgent:
    """Phân loại bằng KB công khai và cộng dồn thống kê các truy vấn SAT.

    timeout là giới hạn giây cho MỖI truy vấn DPLL, None nghĩa là không giới hạn.
    sat_queries lưu lịch sử; last_queries chỉ chứa truy vấn của lần classify gần
    nhất, kể cả truy vấn TIMEOUT. total_runtime cộng tổng thời gian DPLL, không gồm encode.
    """

    def __init__(self, *, timeout: float | None = None) -> None:
        if timeout is not None:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise ValueError("timeout phải là số hoặc None")
            if math.isnan(timeout):
                raise ValueError("timeout không được là NaN")
        self.timeout = timeout
        self._solver = DPLLSolver()
        self.sat_calls = 0
        self.total_decisions = 0
        self.total_propagations = 0
        self.total_backtracks = 0
        self.total_runtime = 0.0
        self.sat_queries: list[SatQuery] = []
        self.last_queries: list[SatQuery] = []
        self.solve_status: str | None = None
        self._selection_status: str | None = None

    def _query(self, kb: KB, cell: str, assumptions: tuple[int, ...] = ()) -> SolveResult:
        self.sat_calls += 1
        result = self._solver.solve(kb.clauses, kb.num_vars,
                                    assumptions=assumptions, timeout=self.timeout)
        status = TIMEOUT if result.timed_out else SAT if result.sat else UNSAT
        stats = replace(result.stats)
        query = SatQuery(cell, assumptions, status, stats)
        self.sat_queries.append(query)
        self.last_queries.append(query)
        self.total_decisions += stats.decisions
        self.total_propagations += stats.propagations
        self.total_backtracks += stats.backtracks
        self.total_runtime += stats.runtime
        if result.timed_out:
            raise TimeoutError(
                f"DPLL quá thời gian khi phân loại {cell}, assumptions={assumptions}"
            )
        return result

    def classify(self, public_kb: PublicKB, cell: str) -> str:
        """Trả CRIMINAL/INNOCENT/UNKNOWN/INCONSISTENT, không đọc dữ liệu ẩn.

        KB UNSAT => INCONSISTENT; KB và giả định Innocent UNSAT => CRIMINAL;
        KB và giả định Criminal UNSAT => INNOCENT; còn lại UNKNOWN.
        Cần tối đa ba SAT calls, dừng ngay khi đã đủ chứng minh.
        Raises: ValueError nếu đầu vào sai; TimeoutError nếu DPLL chưa kết luận.
        """
        self.last_queries = []
        if not isinstance(public_kb, PublicKB):
            raise ValueError("classify chỉ nhận PublicKB")
        n = public_kb.n
        if type(n) is not int or not 1 <= n <= len(board.COLS):
            raise ValueError("Kích thước PublicKB không hợp lệ")
        if not isinstance(public_kb.proved, Mapping):
            raise ValueError("PublicKB.proved phải là mapping")
        if not isinstance(cell, str) or not board.is_valid_cell(cell, n):
            raise ValueError(f"Ô cần phân loại không hợp lệ: {cell!r}")
        kb = Encoder(n).build_kb(public_kb)
        var = board.var_of(cell, n)
        if not self._query(kb, cell).sat:
            return INCONSISTENT
        if not self._query(kb, cell, (-var,)).sat:
            return CRIMINAL
        if not self._query(kb, cell, (var,)).sat:
            return INNOCENT
        return UNKNOWN

    def next_forced(self, public_kb: PublicKB) -> tuple[str, str] | None:
        """Chọn ô chưa chứng minh đầu tiên bị ép theo row-major, không sửa PublicKB.

        Trả None khi STUCK, SOLVED hoặc KB INCONSISTENT; không gửi một verdict từ
        KB mâu thuẫn. Kiểm tra cả trường hợp mọi ô đã proved để không báo SOLVED
        khi snapshot vẫn chứa clue mâu thuẫn. Timeout của classify được truyền ra.
        """
        self._selection_status = None
        if not isinstance(public_kb, PublicKB):
            raise ValueError("next_forced chỉ nhận PublicKB")
        n = public_kb.n
        if type(n) is not int or not 1 <= n <= len(board.COLS):
            raise ValueError("Kích thước PublicKB không hợp lệ")
        if not isinstance(public_kb.proved, Mapping):
            raise ValueError("PublicKB.proved phải là mapping")
        cells = board.all_cells(n)
        remaining = [cell for cell in cells if cell not in public_kb.proved]
        for cell in remaining:
            status = self.classify(public_kb, cell)
            if status == INCONSISTENT:
                self._selection_status = INCONSISTENT
                return None
            if status in (CRIMINAL, INNOCENT):
                return cell, status
            if status != UNKNOWN:
                raise RuntimeError(f"classify trả trạng thái không hợp lệ: {status!r}")
        if not remaining and self.classify(public_kb, cells[0]) == INCONSISTENT:
            self._selection_status = INCONSISTENT
        else:
            self._selection_status = SOLVED if not remaining else STUCK
        return None

    def hint(self, public_kb):
        raise NotImplementedError

    def auto_solve(self, engine: RevealEngine) -> List[TraceEntry]:
        """Lặp chọn forced, nộp verdict và lấy lại PublicKB; trả các bước ACCEPTED.

        solve_status là SOLVED/STUCK/INCONSISTENT khi kết thúc bình thường.
        Timeout đặt trạng thái TIMEOUT rồi ném TimeoutError; không đoán hoặc retry.
        TraceEntry ở E2 chỉ ghi step/cell/verdict và clue đang active; SAT query
        chi tiết và newly_revealed_clue_id dành cho task E3.
        """
        self.solve_status = None
        entries: List[TraceEntry] = []
        try:
            public = engine.get_public_kb()
            while True:
                forced = self.next_forced(public)
                if forced is None:
                    self.solve_status = self._selection_status
                    return entries
                cell, verdict = forced
                if engine.submit_verdict(cell, verdict, self.classify) != ACCEPTED:
                    raise RuntimeError(f"Engine từ chối verdict đã chứng minh: {cell} {verdict}")
                after = engine.get_public_kb()
                if not isinstance(after, PublicKB) or not isinstance(after.proved, Mapping):
                    raise RuntimeError("Engine không trả PublicKB hợp lệ sau ACCEPTED")
                if after.n != public.n or after.proved.get(cell) != verdict:
                    raise RuntimeError("Engine ACCEPTED nhưng chưa cập nhật PublicKB")
                if any(after.proved.get(c) != v for c, v in public.proved.items()):
                    raise RuntimeError("Engine làm mất hoặc đổi verdict đã chứng minh")
                entries.append(TraceEntry(
                    step=len(entries) + 1, active_clue_ids=[c.id for c in public.revealed_clues],
                    cell=cell, verdict=verdict,
                ))
                public = after
        except TimeoutError:
            self.solve_status = TIMEOUT
            raise


def uniqueness_check(all_clues, n: int):
    raise NotImplementedError
