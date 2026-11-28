"""HudContainer: khung chứa toàn bộ giao diện màn chơi (thanh trên, lưới thẻ, bảng bên cạnh), làm mờ/ẩn được
để người chơi ngắm nền. (Scope F)

Hiệu ứng mờ dùng QGraphicsOpacityEffect nhưng CHỈ gắn trong lúc đang chuyển: khi đã hiện rõ hoặc đã ẩn
hẳn thì gỡ ra, vì effect buộc cả cây widget con vẽ qua một pixmap trung gian (tốn khi thẻ animation liên tục).
"""
from typing import Optional

from PySide6.QtCore import QEasingCurve, Signal
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from gui.anim import Tween


class HudContainer(QWidget):
    faded_in = Signal()      # đã hiện rõ hoàn toàn
    faded_out = Signal()     # đã ẩn hẳn

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._fx: Optional[QGraphicsOpacityEffect] = None
        self._target = 1.0
        self._shown = True
        self._tween = Tween(self, self._apply, QEasingCurve.Type.InOutSine)
        self._tween.now = 1.0
        self._tween.finished.connect(self._done)

    @property
    def is_shown(self) -> bool:
        """True nếu đang hiện hoặc đang hiện dần (False khi đã ẩn hoặc đang mờ đi để ẩn)."""
        return self._shown and self._target > 0.0

    def fade_to(self, target: float, ms: int = 400) -> None:
        """target 1.0 = hiện rõ, 0.0 = ẩn hẳn. Gọi giữa chừng thì chạy tiếp từ độ mờ hiện tại."""
        self._tween.stop()
        self._target = float(target)
        if target > 0.0 and not self._shown:
            self._tween.now = 0.0
            self._shown = True
            self.show()
        fx = QGraphicsOpacityEffect(self)
        fx.setOpacity(self._tween.now)
        self.setGraphicsEffect(fx)               # Qt tự huỷ effect cũ (nếu có)
        self._fx = fx
        self._tween.go(target, ms)

    def show_now(self) -> None:
        self._tween.stop()
        self._target, self._tween.now = 1.0, 1.0
        self._clear_fx()
        self._shown = True
        self.show()

    def hide_now(self) -> None:
        self._tween.stop()
        self._target, self._tween.now = 0.0, 0.0
        self._clear_fx()
        self._shown = False
        self.hide()

    def _apply(self) -> None:
        if self._fx is not None:
            self._fx.setOpacity(self._tween.now)

    def _clear_fx(self) -> None:
        self.setGraphicsEffect(None)
        self._fx = None

    def _done(self) -> None:
        self._clear_fx()
        if self._target >= 1.0:
            self.faded_in.emit()
        else:
            self._shown = False
            self.hide()
            self.faded_out.emit()
