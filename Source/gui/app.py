"""Vòng lặp GUI chính: cửa sổ, nối GameEngine + LogicAgent với các component. (Scope F)

GUI KHÔNG chứa luật chơi hay suy luận: mọi verdict đi qua engine.submit_verdict(..., agent.classify),
Hint qua agent.hint(public_kb), Auto Solve qua gui.solver_driver.run_step. Việc nặng chạy ở QThread.
"""
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget)

from engine.game_state import ACCEPTED, CONTRADICTED, NOT_PROVABLE, PublicKB
from gui import theme
from gui.clue_text import STATUS_VN, cells_of_clue, format_clue_text
from gui.components import (BeamOverlay, ClueListView, ConanToast, ConanWidget, EffectOverlay, GadgetButton,
                            GridView, NeonTitle, NightBackdrop, NotebookPanel, RadialMenu,
                            TerminalMessage)
from gui.solver_driver import STEPPED, STUCK, SOLVED, agent_counters, run_step
from gui.sound import SoundManager

AUTO_DELAY_MS = 1100
HINT_SHOW_MS = 7000
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Task(QThread):
    """Chạy một hàm nặng (DPLL/SAT) ngoài luồng giao diện để GUI không đứng hình."""

    done = Signal(object, object)       # (kết quả, lỗi)

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn(), None)
        except BaseException as exc:    # noqa: BLE001 - chuyển lỗi về luồng GUI để hiển thị
            self.done.emit(None, exc)


class MainWindow(QMainWindow):
    def __init__(self, engine, agent, puzzle_path: Optional[str] = None, demo: bool = False) -> None:
        super().__init__()
        self.engine, self.agent, self.demo = engine, agent, demo
        self.kb: Optional[PublicKB] = None
        self.names: Dict[str, str] = {}
        self._task: Optional[Task] = None
        self._pending: Optional[Callable] = None
        self._busy = False
        self._auto_active = self._auto_paused = False
        self._step_no, self._dpll_ms = 0, 0.0
        self._baseline = agent_counters(agent)
        self._hint_cell: Optional[str] = None
        self.setWindowTitle("Griductive · Conan Case File" + ("  [DEMO BACKEND]" if demo else ""))
        self.resize(1380, 880)
        self.setMinimumSize(1120, 740)
        self.sound = SoundManager(self)
        self._build_ui()
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_step)
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._clear_hint)
        if puzzle_path or demo:
            QTimer.singleShot(0, lambda: self._load(puzzle_path))
        else:
            QTimer.singleShot(0, self._on_load)

    # ---- dựng giao diện -------------------------------------------------------------
    def _build_ui(self) -> None:
        self.backdrop = NightBackdrop()
        self.setCentralWidget(self.backdrop)
        root = QVBoxLayout(self.backdrop)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = NeonTitle("GRIDUCTIVE · CONAN CASE FILE", px=26, spacing=5.0)
        self.case_label = QLabel("")
        self.case_label.setObjectName("subtitle")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("subtitle")
        header.addWidget(title)
        header.addSpacing(16)
        header.addWidget(self.case_label)
        header.addStretch(1)
        header.addWidget(self.progress_label)

        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedWidth(44)
        self.btn_mute.setToolTip("Bật/tắt âm thanh (phím M)")
        self.btn_mute.clicked.connect(self._toggle_sound)
        header.addWidget(self.btn_mute)

        root.addLayout(header)

        middle = QHBoxLayout()
        middle.setSpacing(16)
        self.grid = GridView()
        middle.addWidget(self.grid, 1)
        middle.addWidget(self._build_sidebar())
        root.addLayout(middle, 1)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.btn_load = GadgetButton("load", "Load", "Nơ đổi giọng", "Tải hồ sơ vụ án mới từ file JSON")
        self.btn_restart = GadgetButton("restart", "Restart", "Giày tăng lực", "Đặt lại ván về trạng thái ban đầu")
        self.btn_hint = GadgetButton("hint", "Hint", "Đồng hồ gây mê", "Chỉ ra ô có thể chứng minh tiếp theo")
        self.btn_auto = GadgetButton("auto", "Auto Solve", "Bóng tăng kích thước", "Agent tự suy luận từng bước")
        for button in (self.btn_load, self.btn_restart, self.btn_hint, self.btn_auto):
            bar.addWidget(button)
            button.clicked.connect(lambda: self.sound.play("click"))
        self.message_label = TerminalMessage()
        bar.addWidget(self.message_label, 1)
        root.addLayout(bar)

        self.beams = BeamOverlay(self.backdrop)
        self.beams.set_resolver(self._cell_center)
        self.radial = RadialMenu(self.backdrop)
        self.toast = ConanToast(self.backdrop)
        self.effect = EffectOverlay(self.backdrop)
        self.backdrop.resized.connect(self._layout_overlays)
        self.grid.cardClicked.connect(self._on_card_clicked)
        self.radial.chosen.connect(self._on_verdict_chosen)
        self.clue_list.clueSelected.connect(self._select_clue)
        self.btn_load.clicked.connect(self._on_load)
        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_hint.clicked.connect(self._on_hint)
        self.btn_auto.clicked.connect(self._on_auto)
        self.btn_step.clicked.connect(self._step)
        self.btn_stop.clicked.connect(self._stop_auto)

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(410)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.notebook = NotebookPanel()
        self.clue_list = ClueListView()
        tabs = QTabWidget()
        tabs.addTab(self.notebook, "Sổ tay")
        tabs.addTab(self.clue_list, "Manh mối")
        layout.addWidget(tabs, 1)
        controls = QHBoxLayout()
        self.btn_step = QPushButton("Bước tiếp ▶")
        self.btn_stop = QPushButton("Dừng Auto")
        controls.addWidget(self.btn_step)
        controls.addWidget(self.btn_stop)
        layout.addLayout(controls)
        self.conan = ConanWidget()
        self.conan.setFixedHeight(150)
        self.conan.typed.connect(lambda: self.sound.play("type"))      # tiếng gõ phím khi Conan nói
        layout.addWidget(self.conan)
        return side

    def _cell_center(self, cell: str) -> Optional[QPointF]:
        card = self.grid.cards.get(cell)
        return QPointF(card.mapTo(self.backdrop, card.rect().center())) if card else None

    def _layout_overlays(self) -> None:
        self.beams.setGeometry(self.backdrop.rect())
        for overlay in (self.radial, self.effect):
            if overlay.isVisible():
                overlay.setGeometry(self.backdrop.rect())

    def _toggle_sound(self) -> None:
        self.btn_mute.setText("🔊" if self.sound.toggle() else "🔇")

    # ---- trạng thái, thông báo --------------------------------------------------------
    def _say(self, text: str, kind: str = "info") -> None:
        self.message_label.set_message(text, kind)

    def _auto_running(self) -> bool:
        return self._auto_active and not self._auto_paused

    def _solved(self) -> bool:
        return self.kb is not None and len(self.kb.proved) >= self.kb.n * self.kb.n

    def _update_controls(self) -> None:
        busy, running, solved = self._busy, self._auto_running(), self._solved()
        free = not busy and not running and not solved
        self.grid.set_input_enabled(free)
        self.btn_hint.setEnabled(free)
        self.btn_load.setEnabled(not busy)
        self.btn_restart.setEnabled(not busy)
        self.btn_step.setEnabled(free)
        self.btn_auto.setEnabled(not solved and (not busy or self._auto_active))
        self.btn_stop.setVisible(self._auto_active)
        self.btn_auto.set_working(running)
        if running:
            self.btn_auto.set_look("pause", "Tạm dừng", "Giữ bóng lại")
        elif self._auto_active:
            self.btn_auto.set_look("auto", "Tiếp tục", "Đá tiếp nào")
        else:
            self.btn_auto.set_look("auto", "Auto Solve", "Bóng tăng kích thước")

    def _run(self, fn: Callable[[], object], on_done: Callable) -> None:
        """Chạy fn ở luồng nền; on_done(result, error) chạy lại ở luồng GUI."""
        if self._task is not None:
            self._task.wait()
        self._busy, self._pending = True, on_done
        self._update_controls()
        self._task = Task(fn)
        self._task.done.connect(self._on_task_done)
        self._task.start()

    def _on_task_done(self, result, error) -> None:
        self._busy = False
        callback, self._pending = self._pending, None
        if callback:
            callback(result, error)
        self._update_controls()

    def _show_error(self, exc: BaseException) -> None:
        self._stop_auto()
        if isinstance(exc, NotImplementedError):
            text = ("Engine/Agent chưa cài đặt hàm này (NotImplementedError).\n"
                    "Chạy `python main.py --demo` để xem giao diện với backend giả.")
        else:
            text = f"{type(exc).__name__}: {exc}"
        self._say(text, "bad")
        QMessageBox.critical(self, "Lỗi", text)

    # ---- nạp / làm lại ván -----------------------------------------------------------
    def _on_load(self) -> None:
        start = DATA_DIR if DATA_DIR.exists() else Path.home()
        path, _ = QFileDialog.getOpenFileName(self, "Chọn hồ sơ vụ án", str(start), "Puzzle (*.json)")
        if path:
            self._load(path)

    def _load(self, path: Optional[str]) -> None:
        self._stop_auto()
        try:
            self.engine.load_puzzle(path)
        except Exception as exc:        # noqa: BLE001
            self._show_error(exc)
            return
        self.case_label.setText(f"Hồ sơ #{Path(path).stem.upper() if path else 'DEMO'}"
                                + (f" · {self.engine.title}" if getattr(self.engine, "title", "") else ""))
        self._after_reset()

    def _on_restart(self) -> None:
        self._stop_auto()
        try:
            self.engine.restart()
        except Exception as exc:        # noqa: BLE001
            self._show_error(exc)
            return
        self._after_reset()

    def _after_reset(self) -> None:
        n, chars = self.engine.n, self.engine.characters
        self.names = {cell: chars[cell].name for cell in chars}
        self.grid.set_board(n, {cell: (chars[cell].name, chars[cell].profession) for cell in chars})
        self.notebook.reset()
        self.beams.clear()
        self._baseline = agent_counters(self.agent)
        self._step_no, self._dpll_ms, self._hint_cell = 0, 0.0, None
        self.radial.close_menu()
        self._refresh()
        self.conan.say("Sự thật chỉ có một! Chọn một hồ sơ úp rồi kết luận, nhưng đừng đoán mò nhé.", "think")
        self._say("Bấm vào hồ sơ úp để kết luận. Bấm hồ sơ đã mở để soi manh mối của nó.")
        self.sound.start_music()
        self._update_controls()

    # ---- cập nhật hiển thị từ PublicKB --------------------------------------------------
    def _refresh(self, animate=()) -> None:
        self.kb = self.engine.get_public_kb()
        by_owner = {clue.owner: clue for clue in self.kb.revealed_clues}
        for cell, card in self.grid.cards.items():
            status = self.kb.proved.get(cell)
            if status is None:
                card.set_face_down()
                continue
            clue = by_owner.get(cell)
            card.set_face_up(status, format_clue_text(clue, self.names) if clue else "", cell in animate)
        self.clue_list.set_clues([(c.id, f"{self.names.get(c.owner, c.owner)} ({c.owner}): "
                                         f"{format_clue_text(c, self.names)}")
                                  for c in self.kb.revealed_clues])
        self.progress_label.setText(f"Đã phá {len(self.kb.proved)}/{self.kb.n ** 2} hồ sơ")
        self._update_stats()
        if animate:
            self.sound.play("flip")

    def _update_stats(self) -> None:
        now = agent_counters(self.agent)
        d = {k: now[k] - self._baseline[k] for k in now}
        self.notebook.set_stats(self._step_no, d["sat_calls"], d["decisions"], d["propagations"],
                                d["backtracks"], self._dpll_ms)

    def _clue_of(self, clue_id: str):
        return next((c for c in self.kb.revealed_clues if c.id == clue_id), None) if self.kb else None

    # ---- chọn clue / highlight ---------------------------------------------------------
    def _select_clue(self, clue_id: Optional[str]) -> None:
        for card in self.grid.cards.values():
            card.set_highlight("")
        clue = self._clue_of(clue_id) if clue_id else None
        if clue is None:
            self.beams.clear()
            self.clue_list.clear_selection()
            return
        self.sound.play("clue")
        cells = cells_of_clue(clue, self.kb.n)
        for cell in cells:
            self.grid.cards[cell].set_highlight("target")
        if clue.owner not in cells:
            self.grid.cards[clue.owner].set_highlight("source")
        self.clue_list.select(clue_id)
        self.beams.show_links(clue.owner, cells)
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
            card.shake()
            self.sound.play("not_provable")
            self.toast.popup("Chưa đủ bằng chứng!", "shake")
            self.notebook.add_note(f"NOT_PROVABLE: chưa thể kết luận {who} là {word}.", "#7a5a1a")
            self._say(f"NOT_PROVABLE: với manh mối hiện có, chưa ép buộc được {who} là {word} "
                      f"(cũng chưa ép buộc điều ngược lại). Thẻ vẫn úp.", "warn")
        elif status == CONTRADICTED:
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
        self._refresh()
        QTimer.singleShot(1500, lambda: (self.effect.play("victory"),
                                         self.sound.play("victory")))   # chờ thẻ cuối lật xong
        self.conan.say("Vụ án đã được phá! Sự thật chỉ có một!", "happy")
        self._say("Hoàn thành: mọi nhân vật đã được xác định bằng suy luận, không đoán mò.", "ok")

    # ---- phím tắt / đóng cửa sổ ----------------------------------------------------------
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.radial.close_menu()
            self.effect.dismiss()
            self._select_clue(None)
        elif event.key() == Qt.Key.Key_M:
            self._toggle_sound()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._stop_auto()
        if self._task is not None:
            self._task.wait(3000)
        super().closeEvent(event)


def run(puzzle_path: Optional[str] = None, demo: bool = False) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    theme.init_fonts()                      # nạp font trong gui/assets/fonts rồi chọn font có sẵn
    app.setStyleSheet(theme.build_qss())
    app.setFont(QFont(theme.FONT_GADGET, 10))
    if demo:
        from gui.demo_backend import DemoAgent, DemoEngine
        engine, agent = DemoEngine(), DemoAgent()
    else:
        from engine.game_state import GameEngine
        from logic.agent import LogicAgent
        engine, agent = GameEngine(), LogicAgent()
    window = MainWindow(engine, agent, puzzle_path, demo)
    window.show()
    return app.exec()
