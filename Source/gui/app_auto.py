"""AutoMixin: Auto Solve / Bước tiếp / Dừng và màn hình hoàn thành. (Scope F)

Mixin của MainWindow: dùng self.engine, self.agent, self.notebook, ... do MainWindow khai báo.
Nhờ Agent suy luận (Auto Solve hoặc Bước tiếp) thì ván chỉ được 1 sao (_auto_used).
"""

from PySide6.QtCore import QTimer

from gui.progress import stars_text
from gui.solver_driver import STEPPED, STUCK, SOLVED, run_step_explained

AUTO_DELAY_MS = 900           # nghỉ thêm sau khi clue trên thẻ đã gõ xong, để kịp đọc


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
        if self._busy or self._staging:
            self._auto_timer.start(150)
        elif self._card_revealing():              # chờ thẻ lật xong và clue gõ xong
            self._auto_waited = True
            self._auto_timer.start(150)
        elif self._auto_waited and self._auto_running():
            self._auto_waited = False             # nghỉ một nhịp để kịp đọc clue rồi mới sang bước kế
            self._auto_timer.start(AUTO_DELAY_MS)
        elif self._auto_running():
            self._step()

    def _card_revealing(self) -> bool:
        """Còn thẻ nào đang lật / đang gõ chữ clue: chờ xong mới sang bước kế."""
        return any(card.is_revealing() for card in self.grid.cards.values())

    def _stop_auto(self) -> None:
        self._auto_active = self._auto_paused = False
        self._auto_timer.stop()
        self._update_controls()

    def _step(self) -> None:
        self._auto_used = True
        step_no = self._step_no + 1
        self._run(lambda: run_step_explained(self.engine, self.agent, step_no), self._on_step_done)

    def _on_step_done(self, result, error) -> None:
        if error:
            self._show_error(error)
            return
        if result.status == STEPPED:
            self._on_stepped(result)
        elif result.status == SOLVED:
            self._finish_solved()
        elif result.status == STUCK:
            self._stop_auto()
            self.sound.play("not_provable")
            self.backdrop.react_bad()
            self.notebook.add_note("Bế tắc: với các manh mối đang có, không còn hồ sơ nào chắc chắn. "
                                   "Agent dừng lại, không đoán mò.", "#7a5a1a")
            self.conan.say("Manh mối hiện có chưa đủ để kết luận thêm ai. Không đoán mò!", "shake")
            self._say("Bế tắc: chưa còn hồ sơ nào chắc chắn với manh mối hiện có.", "warn")
        else:
            self._stop_auto()
            self.effect.play("contradict")
            self.sound.play("thunder")
            self.notebook.add_note("Mâu thuẫn: các manh mối hiện có tự đá nhau, vụ án này bị lỗi.", "#a3121f")
            self._say("Mâu thuẫn: các manh mối không thể cùng đúng (puzzle lỗi).", "bad")

    def _on_stepped(self, result) -> None:
        entry = result.entry
        self._step_no = entry.step
        support = (result.support_clue_ids if result.support_clue_ids is not None
                   else list(entry.active_clue_ids))
        self._present_reveal("Agent", entry.cell, entry.verdict, support, self._after_stepped)

    def _after_stepped(self) -> None:
        if self._solved():
            self._finish_solved()
        elif self._auto_running():
            self._auto_timer.start(150)

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