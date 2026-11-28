"""Chạy MỘT bước suy luận của Agent để GUI hiển thị từng bước (Auto Solve / Step / Pause). (Scope F)

Không phụ thuộc Qt. Chỉ dùng API công khai theo docs/INTERFACES.md:
  engine.get_public_kb(), engine.submit_verdict(cell, verdict, agent.classify),
  agent.next_forced(public_kb), agent.classify(public_kb, cell)
Nếu LogicAgent có `step(engine) -> TraceEntry | None` thì driver dùng luôn để lấy trace thật
(gồm SAT queries). Chưa có thì fallback: trace chỉ tóm tắt SAT query theo định nghĩa entailment.

Việc còn lại / chưa giải được suy ra từ PublicKB (cell chưa có trong kb.proved),
KHÔNG dùng hàm riêng của engine giả (unsolved_cells...) và KHÔNG đọc dữ liệu ẩn.
"""
import time
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence

from engine import board
from engine.game_state import ACCEPTED, CRIMINAL, INCONSISTENT, PublicKB
from logic.agent import TraceEntry

STEPPED, SOLVED, STUCK = "STEPPED", "SOLVED", "STUCK"


@dataclass
class StepResult:
    status: str                      # STEPPED | SOLVED | STUCK | INCONSISTENT
    entry: Optional[TraceEntry] = None
    new_clue_ids: List[str] = field(default_factory=list)
    deltas: Dict[str, int] = field(default_factory=dict)
    runtime_ms: float = 0.0
    queries_summarized: bool = False  # True nếu SAT queries được tóm tắt, không phải log thật
    support_clue_ids: Optional[List[str]] = None   # manh mối (đã mở) khiến ô này bị ép buộc; None = chưa tính


def agent_counters(agent) -> Dict[str, int]:
    """Đọc bộ đếm tích lũy của agent (thiếu thuộc tính thì coi là 0)."""
    return {k: getattr(agent, f"total_{k}" if k != "sat_calls" else k, 0)
            for k in ("sat_calls", "decisions", "propagations", "backtracks")}


def _diff(before: Dict[str, int], after: Dict[str, int]) -> Dict[str, int]:
    return {k: after[k] - before[k] for k in before}


def _clue_ids(kb: PublicKB) -> List[str]:
    return [c.id for c in kb.revealed_clues]


def unsolved_cells(kb: PublicKB) -> List[str]:
    """Các ô chưa được chứng minh, row-major, tính từ PublicKB."""
    return [c for c in board.all_cells(kb.n) if c not in kb.proved]


def run_step(engine, agent, step_no: int) -> StepResult:
    """Thực hiện một bước: chọn ô forced đầu tiên (row-major) và gửi verdict cho engine."""
    kb = engine.get_public_kb()
    pending = unsolved_cells(kb)
    if not pending:
        return StepResult(SOLVED)
    before_ids, counters, t0 = _clue_ids(kb), agent_counters(agent), time.perf_counter()
    step_fn = getattr(agent, "step", None)
    summarized = False
    if callable(step_fn):
        entry = step_fn(engine)
    else:
        forced = agent.next_forced(kb)
        entry = None
        if forced is not None:
            cell, verdict = forced
            if engine.submit_verdict(cell, verdict, agent.classify) != ACCEPTED:
                raise RuntimeError(f"Agent đưa verdict không được chấp nhận: {cell} {verdict}")
            refuted = f"¬C_{cell}" if verdict == CRIMINAL else f"C_{cell}"
            summarized = True
            entry = TraceEntry(step=step_no, active_clue_ids=before_ids, cell=cell,
                               verdict=verdict,
                               sat_queries=[(f"KB ∧ {refuted}", "UNSAT")])
    runtime_ms = (time.perf_counter() - t0) * 1000
    if entry is None:
        status = INCONSISTENT if agent.classify(kb, pending[0]) == INCONSISTENT else STUCK
        return StepResult(status, deltas=_diff(counters, agent_counters(agent)),
                          runtime_ms=runtime_ms)
    after = engine.get_public_kb()
    new_ids = [i for i in _clue_ids(after) if i not in before_ids]
    if new_ids and not entry.newly_revealed_clue_id:
        entry.newly_revealed_clue_id = new_ids[0]
    entry.step = step_no
    return StepResult(STEPPED, entry, new_ids, _diff(counters, agent_counters(agent)),
                      runtime_ms, summarized)


# ---- giải thích "vì sao": tập manh mối căn cứ -------------------------------------------------
def _with_clues(kb: PublicKB, clues: Sequence):
    """Bản sao PublicKB chỉ giữ các manh mối `clues` (giữ nguyên kiểu tuple/list của kb gốc)."""
    keep = tuple(clues) if isinstance(kb.revealed_clues, tuple) else list(clues)
    return replace(kb, revealed_clues=keep, proved=dict(kb.proved))


def explain_support(agent, kb: PublicKB, cell: str, verdict: str,
                    fallback: Optional[List[str]] = None) -> List[str]:
    """Tập manh mối NHỎ NHẤT (theo nghĩa không bỏ được manh mối nào nữa) vẫn đủ ép buộc `cell` = `verdict`.

    `kb` phải là PublicKB TRƯỚC khi ô `cell` được lật. Cách làm: thử bỏ lần lượt từng manh mối
    (mới nhất trước) rồi hỏi lại agent.classify; bỏ đi mà kết luận vẫn giữ nguyên thì manh mối đó
    không phải căn cứ. Chỉ dùng API công khai (agent.classify), không đọc dữ liệu ẩn.
    Không dựng được kb con (PublicKB không phải dataclass...) hoặc classify lỗi: trả `fallback`
    (mặc định: mọi manh mối đã mở), tức là "không thu hẹp được", vẫn đúng nhưng kém cụ thể.
    """
    clues = list(kb.revealed_clues)
    try:
        keep = list(clues)
        for clue in reversed(clues):
            trial = [c for c in keep if c.id != clue.id]
            if agent.classify(_with_clues(kb, trial), cell) == verdict:
                keep = trial
        return [c.id for c in keep]
    except Exception:                                 # noqa: BLE001 - giải thích chỉ là phần thêm
        return list(fallback) if fallback is not None else [c.id for c in clues]


def snapshot_kb(kb: PublicKB) -> PublicKB:
    """Chụp lại PublicKB để engine có đổi tiếp cũng không ảnh hưởng (không chụp được thì dùng nguyên bản)."""
    try:
        return _with_clues(kb, list(kb.revealed_clues))
    except Exception:                                 # noqa: BLE001
        return kb


def run_step_explained(engine, agent, step_no: int) -> StepResult:
    """run_step + điền `support_clue_ids` (căn cứ của bước vừa chạy). Chạy ở luồng nền."""
    before = snapshot_kb(engine.get_public_kb())
    result = run_step(engine, agent, step_no)
    if result.status == STEPPED and result.entry is not None:
        entry = result.entry
        result.support_clue_ids = explain_support(agent, before, entry.cell, entry.verdict,
                                                  fallback=list(entry.active_clue_ids))
    return result
