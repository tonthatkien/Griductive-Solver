"""BuildMixin: dựng giao diện MainWindow (bản đồ, màn chơi, thanh trên, bảng bên cạnh, các lớp phủ). (Scope F)

Mixin của MainWindow: tạo các widget và gắn tín hiệu; logic xử lý nằm ở main_window / app_play / app_auto / app_view.
"""
from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QStackedWidget, QTabWidget, QVBoxLayout,
                               QWidget)

from gui.case_intro import CaseIntro
from gui.components import (ClueListView, ConanToast, ConanWidget, EffectOverlay, GadgetButton, GridView,
                            NeonTitle, NightBackdrop, NotebookPanel, RadialMenu, TerminalMessage)
from gui.eye_button import EyeButton
from gui.hud_fader import HudContainer
from gui.iris import IrisTransition
from gui.level_menu import LevelMenu


class _Stage(QStackedWidget):
    """QStackedWidget báo khi đổi kích thước để lớp chuyển cảnh phủ kín theo."""

    resized = Signal()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.resized.emit()


class BuildMixin:
    # ---- dựng giao diện -------------------------------------------------------------
    def _build_ui(self) -> None:
        self.stage = _Stage()
        self.setCentralWidget(self.stage)
        self.menu = LevelMenu()
        self.backdrop = NightBackdrop()
        self.stage.addWidget(self.menu)
        self.stage.addWidget(self.backdrop)
        self.iris = IrisTransition(self.stage)
        self.hud = HudContainer(self.backdrop)         # toàn bộ giao diện: làm mờ/ẩn được để ngắm nền
        root = QVBoxLayout(self.backdrop)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.hud)
        hud_box = QVBoxLayout(self.hud)
        hud_box.setContentsMargins(12, 8, 12, 10)
        hud_box.setSpacing(6)

        header = QHBoxLayout()
        title = NeonTitle("GRIDUCTIVE · CONAN CASE FILE", px=18, spacing=3.0)
        self.case_label = QLabel("")
        self.case_label.setObjectName("subtitle")
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("subtitle")
        header.addWidget(title)
        header.addSpacing(12)
        header.addWidget(self.case_label)
        header.addStretch(1)
        # nút thao tác gọn nằm ngay trên thanh tiêu đề (tiết kiệm cả dải nút phía dưới)
        self.btn_menu = GadgetButton("load", "Menu", "Bản đồ vụ án", "Quay về bản đồ chọn màn", compact=True)
        self.btn_restart = GadgetButton("restart", "Restart", "Giày tăng lực", "Đặt lại ván về trạng thái ban đầu", compact=True)
        self.btn_hint = GadgetButton("hint", "Hint", "Đồng hồ gây mê", "Chỉ ra ô có thể chứng minh tiếp theo", compact=True)
        self.btn_auto = GadgetButton("auto", "Auto Solve", "Bóng tăng kích thước", "Agent tự suy luận từng bước", compact=True)
        for button in (self.btn_menu, self.btn_restart, self.btn_hint, self.btn_auto):
            header.addWidget(button)
            button.clicked.connect(lambda: self.sound.play("click"))
        header.addSpacing(6)

        self.btn_eye = EyeButton(tooltip="Ẩn giao diện để ngắm nền (Space)")
        header.addWidget(self.btn_eye)
        self.btn_mute = QPushButton("🔊")
        self.btn_mute.setFixedWidth(44)
        self.btn_mute.setToolTip("Bật/tắt âm thanh (phím M)")
        self.btn_mute.clicked.connect(self._toggle_sound)
        header.addWidget(self.btn_mute)

        hud_box.addLayout(header)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        self.grid = GridView()
        middle.addWidget(self.grid, 1)
        middle.addWidget(self._build_sidebar())
        hud_box.addLayout(middle, 1)

        self.radial = RadialMenu(self.backdrop)
        self.toast = ConanToast(self.backdrop)
        self.effect = EffectOverlay(self.backdrop)
        self.intro = CaseIntro(self.backdrop)
        self.eye_float = EyeButton("HIỆN LẠI · SPACE", "Hiện lại giao diện (Space)", closed=True, parent=self.backdrop)
        self.eye_float.hide()
        self._space = QShortcut(QKeySequence("Space"), self)       # chỉ bật khi đang ở màn chơi
        self._space.setEnabled(False)
        self._space.activated.connect(self._on_space)
        self.backdrop.resized.connect(self._layout_overlays)
        self.backdrop.clicked.connect(self._on_backdrop_clicked)
        self.hud.faded_out.connect(self._on_hud_faded_out)
        self.intro.reveal.connect(self._on_intro_reveal)
        self.intro.done.connect(self._on_intro_done)
        self.btn_eye.clicked.connect(lambda: self._set_hud_hidden(True))
        self.eye_float.clicked.connect(lambda: self._set_hud_hidden(False))
        self.stage.resized.connect(self._layout_iris)
        self.menu.levelChosen.connect(self._on_level_chosen)
        self.menu.conan.typed.connect(lambda: self.sound.play("type"))
        self.grid.cardClicked.connect(self._on_card_clicked)
        self.radial.chosen.connect(self._on_verdict_chosen)
        self.clue_list.clueSelected.connect(self._select_clue)
        self.btn_menu.clicked.connect(self._on_menu)
        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_hint.clicked.connect(self._on_hint)
        self.btn_auto.clicked.connect(self._on_auto)
        self.btn_step.clicked.connect(self._step)
        self.btn_stop.clicked.connect(self._stop_auto)

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setFixedWidth(330)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.notebook = NotebookPanel()
        self.clue_list = ClueListView()
        tabs = QTabWidget()
        tabs.addTab(self.notebook, "Sổ tay")
        tabs.addTab(self.clue_list, "Manh mối")
        layout.addWidget(self.progress_label)
        layout.addWidget(tabs, 1)
        controls = QHBoxLayout()
        self.btn_step = QPushButton("Bước tiếp ▶")
        self.btn_stop = QPushButton("Dừng Auto")
        controls.addWidget(self.btn_step)
        controls.addWidget(self.btn_stop)
        layout.addLayout(controls)
        self.message_label = TerminalMessage()
        self.message_label.setMinimumHeight(64)
        layout.addWidget(self.message_label)
        self.conan = ConanWidget()
        self.conan.setFixedHeight(110)
        self.conan.typed.connect(lambda: self.sound.play("type"))      # tiếng gõ phím khi Conan nói
        layout.addWidget(self.conan)
        return side
