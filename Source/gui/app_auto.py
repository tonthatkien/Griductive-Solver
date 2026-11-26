"""AutoMixin: Auto Solve / Bước tiếp / Dừng và màn hình hoàn thành. (Scope F)

Mixin của MainWindow: dùng self.engine, self.agent, self.notebook, ... do MainWindow khai báo.
Nhờ Agent suy luận (Auto Solve hoặc Bước tiếp) thì ván chỉ được 1 sao (_auto_used).
"""

from PySide6.QtCore import QTimer

from gui.clue_text import STATUS_VN, format_clue_text
from gui.progress import stars_text
from gui.solver_driver import STEPPED, STUCK, SOLVED, run_step

AUTO_DELAY_MS = 1100


class AutoMixin:
    # ---- auto solve --------------------------------------------------------------------
    def _on_auto(self) -> None:
        if not self._auto_active:
            self._auto_active, self._auto_paused = True, False
            self._clear_hint()
            self.radial.close_menu()
            self._update_controls()
            self._auto_step()
        elif self._auto_paused:
            self._auto_paused = False
            self._update_controls()
            self._auto_step()
        else:
            self._auto_paused = True
            self._auto_timer.stop()
            self._update_controls()
            self.conan.say("Tạm dừng. Bấm 'Bước tiếp' để đi từng bước.", "think")

    def _auto_step(self) -> None:
        if self._busy:
            self._auto_timer.start(150)
        elif self._auto_running():
            self._step()

    def _stop_auto(self) -> None:
        self._auto_active = self._auto_paused = False
        self._auto_timer.stop()
        self._update_controls()

    def _step(self) -> None:
        self._auto_used = True
        step_no = self._step_no + 1
        self._run(lambda: run_step(self.engine, self.agent, step_no), self._on_step_done)

    def _on_step_done(self, result, error) -> None:
        if error:
            self._show_error(error)
            return
        self._dpll_ms += result.runtime_ms
        if result.status == STEPPED:
            self._on_stepped(result)
        elif result.status == SOLVED:
            self._finish_solved()
        elif result.status == STUCK:
            self._stop_auto()
            self.sound.play("not_provable")
            self.backdrop.react_bad()
            self.notebook.add_note("STUCK: không còn ô nào bị ép buộc. Agent dừng, không đoán.", "#7a5a1a")
            self.conan.say("Manh mối hiện có chưa đủ để kết luận thêm ai. Không đoán mò!", "shake")
            self._say("STUCK: không còn ô nào bị ép buộc bởi tri thức hiện tại.", "warn")
            self._update_stats()
        else:
            self._stop_auto()
            self.effect.play("contradict")
            self.sound.play("thunder")
            self.notebook.add_note("INCONSISTENT: tri thức hiện tại tự mâu thuẫn.", "#a3121f")
            self._say("INCONSISTENT: KB không thỏa mãn được (puzzle lỗi).", "bad")

    def _on_stepped(self, result) -> None:
        self.sound.play("step")
        self.backdrop.react_good()
        entry = result.entry
        self._step_no = entry.step
        self._refresh(animate={entry.cell})
        clue = self._clue_of(entry.newly_revealed_clue_id) if entry.newly_revealed_clue_id else None
        who = f"{self.names[entry.cell]} ({entry.cell})"
        note = "SAT queries được tóm tắt theo định nghĩa entailment" if result.queries_summarized else ""
        self.notebook.add_entry(entry.step, "Agent", who, entry.cell, entry.verdict, entry.sat_queries,
                                len(entry.active_clue_ids), format_clue_text(clue, self.names) if clue else "",
                                result.runtime_ms, note)
        self._say(f"Agent kết luận {who} là {STATUS_VN[entry.verdict].lower()} "
                  f"(KB ∧ phủ định là UNSAT).", "ok")
        self.conan.say(f"{self.names[entry.cell]} là {STATUS_VN[entry.verdict].lower()}. Chắc chắn!", "happy")
        if clue:
            QTimer.singleShot(1100, lambda: self._select_clue(clue.id))
        if self._solved():
            self._finish_solved()
        elif self._auto_running():
            self._auto_timer.start(AUTO_DELAY_MS)

    def _after_progress(self) -> None:
        if self._solved():
            self._finish_solved()

    def _finish_solved(self) -> None:
        self._stop_auto()
        stars = self._record_clear()
        self._refresh()
        self.backdrop.play_dawn(2800)                    # đêm chuyển dần sang bình minh
        QTimer.singleShot(3200, lambda: (self.effect.play("victory"),
                                         self.sound.play("victory")))   # chờ bình minh lên xong
        self.conan.say(f"Vụ án đã được phá! {stars_text(stars)} Sự thật chỉ có một!", "happy")
        self._say(f"Hoàn thành {stars_text(stars)}: mọi nhân vật đã được xác định bằng suy luận, "
                  f"không đoán mò. Bấm Menu để về bản đồ.", "ok")
