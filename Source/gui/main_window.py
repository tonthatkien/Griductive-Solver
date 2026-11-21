"""MainWindow: dựng giao diện, nạp/làm lại ván, cập nhật hiển thị từ PublicKB. (Scope F)

GUI KHÔNG chứa luật chơi hay suy luận: mọi verdict đi qua engine.submit_verdict(..., agent.classify),
Hint qua agent.hint(public_kb), Auto Solve qua gui.solver_driver.run_step. Việc nặng chạy ở QThread.
Phần chơi tay ở app_play.py, phần Auto Solve ở app_auto.py.
"""
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QTabWidget, QVBoxLayout, QWidget)

from engine.game_state import PublicKB
from gui.clue_text import format_clue_text
from gui.components import (ClueListView, ConanToast, ConanWidget, EffectOverlay, GadgetButton,
                            GridView, NeonTitle, NightBackdrop, NotebookPanel, RadialMenu,
                            TerminalMessage)
from gui.solver_driver import agent_counters
from gui.sound import SoundManager
from gui.task import Task
from gui.app_auto import AutoMixin
from gui.app_play import PlayMixin

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class MainWindow(PlayMixin, AutoMixin, QMainWindow):
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

    def _layout_overlays(self) -> None:
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
