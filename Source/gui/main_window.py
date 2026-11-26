"""MainWindow: bản đồ chọn màn + màn chơi, nạp/làm lại ván, cập nhật hiển thị từ PublicKB. (Scope F)

Hai trang trong một QStackedWidget: LevelMenu (bản đồ thành phố về đêm) và màn chơi (NightBackdrop).
Chuyển trang bằng hiệu ứng khép/mở vòng tròn (IrisTransition). Không còn nút Load: màn chơi được
chọn trên bản đồ (gui/levels.py quét data/), hoặc truyền thẳng `python main.py --puzzle <file>`.

GUI KHÔNG chứa luật chơi hay suy luận: mọi verdict đi qua engine.submit_verdict(..., agent.classify),
Hint qua agent.hint(public_kb), Auto Solve qua gui.solver_driver.run_step. Việc nặng chạy ở QThread.
Dựng giao diện ở app_build.py, cảnh mở đầu + ẩn/hiện giao diện ở app_view.py,
phần chơi tay ở app_play.py, phần Auto Solve ở app_auto.py.

Engine thật (engine/game_state.py): `engine.characters` là tuple[Character] công khai,
`engine.n`, `engine.get_public_kb()`, `engine.load_puzzle(path)`, `engine.restart()`.
"""
from pathlib import Path
from typing import Callable, Dict, Optional

import traceback
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QMessageBox

from engine.game_state import PublicKB
from gui.clue_text import format_clue_text
from gui.levels import discover_levels
from gui.progress import DEFAULT_PATH, Progress, compute_stars
from gui.solver_driver import agent_counters
from gui.sound import SoundManager
from gui.task import Task
from gui.app_auto import AutoMixin
from gui.app_build import BuildMixin
from gui.app_play import PlayMixin
from gui.app_view import ViewMixin

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TITLE_MENU = "Griductive · Bản đồ vụ án"
TITLE_GAME = "Griductive · Conan Case File"


class MainWindow(BuildMixin, ViewMixin, PlayMixin, AutoMixin, QMainWindow):
    def __init__(self, engine, agent, puzzle_path: Optional[str] = None) -> None:
        super().__init__()
        self.engine, self.agent = engine, agent
        self.progress = Progress(DEFAULT_PATH)
        self.kb: Optional[PublicKB] = None
        self.names: Dict[str, str] = {}
        self._task: Optional[Task] = None
        self._pending: Optional[Callable] = None
        self._busy = False
        self._transitioning = False
        self._auto_active = self._auto_paused = False
        self._step_no, self._dpll_ms = 0, 0.0
        self._baseline = agent_counters(agent)
        self._hint_cell: Optional[str] = None
        self._level_key: Optional[str] = None
        self._hints_used = self._wrong_attempts = 0     # để tính sao (progress.compute_stars)
        self._auto_used = self._recorded = False
        self._intro_active = self._hud_hidden = False     # cảnh mở đầu đang chạy / giao diện đang ẩn để ngắm nền
        self.setWindowTitle(TITLE_MENU)
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)
        self.sound = SoundManager(self)
        self._build_ui()
        self.menu.set_levels(discover_levels(DATA_DIR), self.progress)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_step)
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._clear_hint)
        QTimer.singleShot(0, self.sound.start_music)
        if puzzle_path:
            QTimer.singleShot(0, lambda: self._open_directly(puzzle_path))
        else:
            self.stage.setCurrentWidget(self.menu)
            self.menu.setFocus()

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
        self.btn_menu.setEnabled(not busy)
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
                    "Kiểm tra nhánh main đã có E1/E2/E5 (logic/agent.py) chưa.")
        elif isinstance(exc, AssertionError):
            text = ("Agent hoặc engine vi phạm hợp đồng (AssertionError): "
                    f"{exc}\nĐây là lỗi logic của nhóm, không phải lỗi giao diện.")
        else:
            text = f"{type(exc).__name__}: {exc}"
        self._say(text, "bad")
        QMessageBox.critical(self, "Lỗi", text)

    # ---- chuyển trang: bản đồ <-> màn chơi -----------------------------------------------
    def _begin_transition(self, center: QPointF, at_black: Callable[[], None]) -> None:
        """Khép vòng tròn về `center`, làm `at_black()` khi màn đen kín, rồi mở vòng tròn ra."""
        if self._transitioning:
            return
        self._transitioning = True
        self.iris.close_to(center, lambda: self._at_black(at_black, center))

    def _at_black(self, work: Callable[[], None], center: QPointF) -> None:
        error: Optional[BaseException] = None
        try:
            work()
        except Exception as exc:                   # noqa: BLE001 - không để lỗi bị nuốt im lặng
            traceback.print_exc()
            error = exc
        finally:                                   # dù lỗi cũng phải mở lại, không kẹt màn đen
            self.iris.open_from(center, self._transition_done)
        if error is not None:
            QTimer.singleShot(0, lambda: self._show_error(error))

    def _transition_done(self) -> None:
        self._transitioning = False
        if self.stage.currentWidget() is self.menu:
            self.menu.setFocus()

    def _on_level_chosen(self, key: str, anchor) -> None:
        if self._transitioning or self._busy:
            return
        self.sound.play("radial")
        path = str(DATA_DIR / key)
        level = self.menu.level_by_key(key)
        place = level.place if level else ""
        self._begin_transition(QPointF(anchor), lambda: self._enter_game(path, place))

    def _enter_game(self, path: str, place: str = "") -> None:
        if self._load(path):                       # nạp lỗi thì ở lại bản đồ
            self.backdrop.set_place(place)         # cảnh nền theo địa điểm của vụ án
            self.stage.setCurrentWidget(self.backdrop)
            self._space.setEnabled(True)
            self.setWindowTitle(TITLE_GAME)
            self.sound.play("flip")
            self._start_intro(place)

    def _open_directly(self, path: str) -> None:
        """`--puzzle <file>`: vào thẳng màn chơi, không qua bản đồ."""
        if self._load(path):
            self.backdrop.set_place("")
            self.stage.setCurrentWidget(self.backdrop)
            self._space.setEnabled(True)
            self.setWindowTitle(TITLE_GAME)
            self._start_intro("", f"HỒ SƠ #{Path(path).stem.upper()}")
        else:
            self.stage.setCurrentWidget(self.menu)

    def _on_menu(self) -> None:
        if self._busy or self._transitioning or self._intro_active or self.stage.currentWidget() is self.menu:
            return
        self._stop_auto()
        self.radial.close_menu()
        self.effect.dismiss()
        self._clear_hint()
        self._select_clue(None)
        center = QPointF(self.stage.width() / 2, self.stage.height() / 2)
        self._begin_transition(center, self._swap_to_menu)

    def _swap_to_menu(self) -> None:
        self._space.setEnabled(False)
        self._reset_view()
        self.stage.setCurrentWidget(self.menu)
        self.setWindowTitle(TITLE_MENU)
        self.menu.refresh()

    # ---- nạp / làm lại ván -----------------------------------------------------------
    @staticmethod
    def _key_of(path: str) -> Optional[str]:
        """Key tiến độ của file puzzle nếu nó nằm trong data/, ngược lại None (không ghi sao)."""
        try:
            return Path(path).resolve().relative_to(DATA_DIR.resolve()).as_posix()
        except ValueError:
            return None

    def _load(self, path: str) -> bool:
        """Nạp puzzle. Trả False (và báo lỗi) nếu puzzle sai; engine giữ nguyên ván cũ."""
        self._stop_auto()
        try:
            self.engine.load_puzzle(path)
        except Exception as exc:        # noqa: BLE001
            self._show_error(exc)
            return False
        self._level_key = self._key_of(path)
        level = self.menu.level_by_key(self._level_key) if self._level_key else None
        n = self.engine.n
        self.case_label.setText(f"{level.title} · {level.place} · {n}×{n}" if level
                                else f"Hồ sơ #{Path(path).stem.upper()} · {n}×{n}")
        self._after_reset()
        return True

    def _on_restart(self) -> None:
        self._stop_auto()
        try:
            self.engine.restart()
        except Exception as exc:        # noqa: BLE001
            self._show_error(exc)
            return
        self._after_reset()

    def _after_reset(self) -> None:
        n = self.engine.n
        chars = self.engine.characters                      # tuple[Character], row-major
        self.names = {ch.cell: ch.name for ch in chars}
        self.grid.set_board(n, {ch.cell: (ch.name, ch.profession) for ch in chars})
        self.notebook.reset()
        self._baseline = agent_counters(self.agent)
        self._step_no, self._dpll_ms, self._hint_cell = 0, 0.0, None
        self._hints_used = self._wrong_attempts = 0
        self._auto_used = self._recorded = False
        self.radial.close_menu()
        self.backdrop.reset_mood()                          # xoá bình minh/hiệu ứng cũ khi làm lại
        self._refresh()
        self.conan.say("Sự thật chỉ có một! Chọn một hồ sơ úp rồi kết luận, nhưng đừng đoán mò nhé.", "think")
        self._say("Bấm vào hồ sơ úp để kết luận. Bấm hồ sơ đã mở để soi manh mối của nó.")
        self.sound.start_music()
        self._update_controls()

    def _record_clear(self) -> int:
        """Tính sao cho lần phá án này và lưu vào tiến độ (một lần mỗi ván). Trả về số sao."""
        stars = compute_stars(self._hints_used, self._wrong_attempts, self._auto_used)
        if not self._recorded:
            self._recorded = True
            if self._level_key is not None:
                self.progress.record(self._level_key, stars)
        return stars

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
            if self._intro_active:
                self.intro.skip()
            elif self._hud_hidden:
                self._set_hud_hidden(False)
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
