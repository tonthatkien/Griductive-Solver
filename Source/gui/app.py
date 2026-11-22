"""Điểm vào GUI: tạo engine + agent thật, mở MainWindow. (Scope F)

GUI KHÔNG chứa luật chơi hay suy luận. Code cửa sổ nằm ở main_window.py (+ app_play.py, app_auto.py).
"""
import sys
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from engine.game_state import GameEngine
from gui import theme
from gui.app_auto import AUTO_DELAY_MS  # noqa: F401  (re-export)
from gui.app_play import HINT_SHOW_MS  # noqa: F401  (re-export)
from gui.main_window import DATA_DIR, MainWindow  # noqa: F401  (re-export)
from gui.task import Task  # noqa: F401  (re-export)
from logic.agent import LogicAgent


def run(puzzle_path: Optional[str] = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    theme.init_fonts()                      # nạp font trong gui/assets/fonts rồi chọn font có sẵn
    app.setStyleSheet(theme.build_qss())
    app.setFont(QFont(theme.FONT_GADGET, 10))
    window = MainWindow(GameEngine(), LogicAgent(), puzzle_path)
    window.show()
    return app.exec()
