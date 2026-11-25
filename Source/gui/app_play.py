"""PlayMixin: người chơi chọn clue, đoán verdict, xin Hint. (Scope F)

Mixin của MainWindow: dùng self.engine, self.agent, self.grid, ... do MainWindow khai báo.
Đếm số lần bị từ chối verdict (_wrong_attempts) và số lần xin Hint (_hints_used) để tính sao.
"""
import time
from typing import Optional

from PySide6.QtCore import QPointF, QTimer

from engine.game_state import ACCEPTED, CONTRADICTED, NOT_PROVABLE
from gui.clue_text import STATUS_VN, cells_of_clue, format_clue_text
from gui.solver_driver import agent_counters

HINT_SHOW_MS = 7000


class PlayMixin:
    # ---- chọn clue / highlight ---------------------------------------------------------
    def _select_clue(self, clue_id: Optional[str]) -> None:
        for card in self.grid.cards.values():
            card.set_highlight("")
        clue = self._clue_of(clue_id) if clue_id else None
        if clue is None:
            self.clue_list.clear_selection()
            return
        self.sound.play("clue")
        cells = cells_of_clue(clue, self.kb.n)
        for cell in cells:
            self.grid.cards[cell].set_highlight("target")
        if clue.owner not in cells:
            self.grid.cards[clue.owner].set_highlight("source")
        self.clue_list.select(clue_id)
        text = format_clue_text(clue, self.names)
        self.conan.say(text, "think")
        self._say(f"Manh mối của {self.names[clue.owner]} ({clue.owner}): {text}")

    # ---- người chơi đoán verdict ----------------------------------------------------------
    def _on_card_clicked(self, cell: str) -> None:
        if self._busy or self._auto_running() or self.kb is None:
            return
        if cell in self.kb.proved:
            clue = next((c for c in self.kb.revealed_clues if c.owner == cell), None)
            if clue:
                self._select_clue(clue.id)
            return
        self._clear_hint()
        card = self.grid.cards[cell]
        self.sound.play("radial")
        self.radial.open_at(cell, self.names[cell], QPointF(card.mapTo(self.backdrop, card.rect().center())))

    def _on_verdict_chosen(self, cell: str, verdict: str) -> None:
        self.sound.play("click")
        before = agent_counters(self.agent)

        def work():
            t0 = time.perf_counter()
            status = self.engine.submit_verdict(cell, verdict, self.agent.classify)
            return status, (time.perf_counter() - t0) * 1000

        def done(result, error) -> None:
            if error:
                self._show_error(error)
                return
            status, ms = result
            self._dpll_ms += ms
            self._on_verdict_result(cell, verdict, status, ms, before)

        self._say(f"Đang chứng minh: {self.names[cell]} ({cell}) là {STATUS_VN[verdict].lower()}...")
        self._run(work, done)

    def _on_verdict_result(self, cell: str, verdict: str, status: str, ms: float, before) -> None:
        who = f"{self.names[cell]} ({cell})"
        word = STATUS_VN[verdict].lower()
        card = self.grid.cards[cell]
        if status == ACCEPTED:
            self._step_no += 1
            self._refresh(animate={cell})
            self.sound.play("correct")
            clue = next((c for c in self.kb.revealed_clues if c.owner == cell), None)
            used = agent_counters(self.agent)["sat_calls"] - before["sat_calls"]
            self.notebook.add_entry(self._step_no, "Người chơi", who, cell, verdict, [],
                                    len(self.kb.revealed_clues) - 1,
                                    format_clue_text(clue, self.names) if clue else "", ms,
                                    note=f"SAT calls: +{used}")
            self._say(f"ACCEPTED: {who} là {word}. Thẻ được lật, manh mối mới đã lộ.", "ok")
            self.conan.say("Chính xác! Suy luận không có kẽ hở.", "happy")
            if clue:
                QTimer.singleShot(1100, lambda: self._select_clue(clue.id))
            self._after_progress()
        elif status == NOT_PROVABLE:
            self._wrong_attempts += 1
            card.shake()
            self.sound.play("not_provable")
            self.toast.popup("Chưa đủ bằng chứng!", "shake")
            self.notebook.add_note(f"NOT_PROVABLE: chưa thể kết luận {who} là {word}.", "#7a5a1a")
            self._say(f"NOT_PROVABLE: với manh mối hiện có, chưa ép buộc được {who} là {word} "
                      f"(cũng chưa ép buộc điều ngược lại). Thẻ vẫn úp.", "warn")
        elif status == CONTRADICTED:
            self._wrong_attempts += 1
            card.shake()
            self.effect.play("contradict")
            self.sound.play("thunder")
            self.conan.say("Khoan đã! Kết luận này đi ngược với những gì logic đã chứng minh.", "shock")
            self.notebook.add_note(f"CONTRADICTED: kết luận ngược lại mới bị ép buộc ở {who}.", "#a3121f")
            self._say(f"CONTRADICTED: điều NGƯỢC LẠI mới là hệ quả bắt buộc đối với {who}. Thẻ vẫn úp.", "bad")
        self._update_stats()

    # ---- hint --------------------------------------------------------------------------
    def _on_hint(self) -> None:
        self._clear_hint()
        self.radial.close_menu()
        self._say("Đồng hồ gây mê đang ngắm mục tiêu...")
        self._run(lambda: self.agent.hint(self.engine.get_public_kb()), self._on_hint_done)

    def _on_hint_done(self, result, error) -> None:
        if error:
            self._show_error(error)
            return
        if result is None:
            self.sound.play("not_provable")
            self.conan.say("Hiện chưa ai bị ép buộc bởi manh mối đang có.", "shake")
            self._say("Hint: chưa có ô nào có thể chứng minh được ngay (agent sẽ dừng ở STUCK).", "warn")
            return
        self._hints_used += 1
        self.sound.play("hint")
        cell, _verdict, clue_ids = result            # cố ý KHÔNG hiển thị verdict
        self._hint_cell = cell
        self.grid.cards[cell].set_hint(True)
        if clue_ids:
            self._select_clue(clue_ids[0])
        self.conan.say(f"Hãy chú ý {self.names[cell]} ({cell}): có thể chứng minh được ngay!", "think")
        self._say(f"Hint: {self.names[cell]} ({cell}) đang bị ép buộc bởi các manh mối đã lật. "
                  f"Tự kết luận nhé!", "ok")
        self._hint_timer.start(HINT_SHOW_MS)

    def _clear_hint(self) -> None:
        if self._hint_cell and self._hint_cell in self.grid.cards:
            self.grid.cards[self._hint_cell].set_hint(False)
        self._hint_cell = None
