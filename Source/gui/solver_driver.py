"""Chạy MỘT bước suy luận của Agent để GUI hiển thị từng bước (Auto Solve / Step / Pause).

Không phụ thuộc Qt. Chỉ dùng API công khai theo docs/INTERFACES.md:
  agent.next_forced(public_kb), engine.submit_verdict(cell, verdict, agent.classify)
Nếu LogicAgent sau này có `step(engine) -> TraceEntry | None` thì driver dùng luôn
(đề xuất cho E2/E3: trace thật gồm SAT queries; hiện fallback chỉ tóm tắt theo định nghĩa).
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

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


def agent_counters(agent) -> Dict[str, int]:
    """Đọc bộ đếm tích lũy của agent (thiếu thuộc tính thì coi là 0)."""
    return {k: getattr(agent, f"total_{k}" if k != "sat_calls" else k, 0)
            for k in ("sat_calls", "decisions", "propagations", "backtracks")}


def _diff(before: Dict[str, int], after: Dict[str, int]) -> Dict[str, int]:
    return {k: after[k] - before[k] for k in before}


def _clue_ids(kb: PublicKB) -> List[str]:
    return [c.id for c in kb.revealed_clues]


def run_step(engine, agent, step_no: int) -> StepResult:
    """Thực hiện một bước: chọn ô forced đầu tiên (row-major) và gửi verdict cho engine."""
    if not engine.unsolved_cells():
        return StepResult(SOLVED)
    kb = engine.get_public_kb()
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
        first = engine.unsolved_cells()[0]
        status = INCONSISTENT if agent.classify(kb, first) == INCONSISTENT else STUCK
        return StepResult(status, deltas=_diff(counters, agent_counters(agent)),
                          runtime_ms=runtime_ms)
    after = engine.get_public_kb()
    new_ids = [i for i in _clue_ids(after) if i not in before_ids]
    if new_ids and not entry.newly_revealed_clue_id:
        entry.newly_revealed_clue_id = new_ids[0]
    entry.step = step_no
    return StepResult(STEPPED, entry, new_ids, _diff(counters, agent_counters(agent)),
                      runtime_ms, summarized)
