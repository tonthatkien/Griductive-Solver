"""NightBackdrop: nền màn chơi, đổi cảnh theo địa điểm của vụ án (xem gui/scenes). (Scope F)

Ngoài việc vẽ cảnh còn có: lớp phủ tối (`veil`) để lưới thẻ dễ đọc nhưng có thể gỡ đi lúc mở màn / ngắm nền,
và các phản ứng với ván chơi: `react_good`, `react_bad`, `play_dawn`.
"""
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPointF, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui.anim import Tween, clock
from gui.scenes import Scene, scene_for


class NightBackdrop(QWidget):
    """Nền màn chơi: mỗi địa điểm một cảnh động riêng; không rõ địa điểm thì là thành phố ban đêm."""

    resized = Signal()
    clicked = Signal()          # bấm vào nền (khi giao diện đang ẩn thì cửa sổ chính dùng để hiện lại)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._place = ""
        self._scene: Scene = scene_for("")
        self._t, self._t0 = 0.0, clock().t
        self._veil = 1.0
        self._veil_tween = Tween(self, self._on_veil, QEasingCurve.Type.OutCubic)
        self._veil_tween.now = 1.0
        self._dawn = Tween(self, self._on_dawn, QEasingCurve.Type.InOutSine)
        clock().tick.connect(self._tick)

    # ---- cảnh --------------------------------------------------------------------------
    def set_place(self, place: str) -> None:
        """Đổi cảnh nền theo tên địa điểm (Level.place). Gọi trước khi hiện màn chơi."""
        self._place, self._scene = place, scene_for(place)
        self._dawn.jump(0.0)
        self.update()

    # ---- lớp phủ tối -------------------------------------------------------------------
    def set_veil(self, value: float, ms: int = 600) -> None:
        """1 = phủ tối bình thường (thẻ dễ đọc), 0 = nền sáng rõ. Chạy mượt trong `ms`."""
        self._veil_tween.go(value, ms)

    def set_veil_now(self, value: float) -> None:
        self._veil_tween.jump(value)

    def _on_veil(self) -> None:
        self._veil = self._veil_tween.now
        self.update()

    # ---- phản ứng với ván chơi ---------------------------------------------------------
    def react_good(self) -> None:
        """Phá án đúng: cảnh sáng lên một nhịp (mỗi cảnh có thể tự làm riêng)."""
        self._scene.on_good(self._t)

    def react_bad(self) -> None:
        """Kết luận sai: đèn chập chờn rồi tối đi."""
        self._scene.on_bad(self._t)

    def play_dawn(self, ms: int = 2800) -> None:
        """Thắng màn: đêm chuyển dần sang bình minh."""
        self._dawn.go(1.0, ms)

    def reset_mood(self) -> None:
        self._dawn.jump(0.0)
        self._scene.reset_mood()

    def _on_dawn(self) -> None:
        self._scene.set_dawn(self._dawn.now)

    # ---- vẽ ----------------------------------------------------------------------------
    def _tick(self) -> None:
        self._t = clock().t - self._t0
        if self.isVisible():
            self.update()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.resized.emit()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        self._scene.paint(p, w, h, self._t, self.devicePixelRatioF())
        # lớp phủ tối nhẹ ở giữa (cho lưới thẻ dễ đọc) + tối dần ra mép (vignette)
        v = self._veil
        veil = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.75)
        veil.setColorAt(0, QColor(0, 0, 0, int(85 * v)))
        veil.setColorAt(0.6, QColor(0, 0, 0, int(55 * v)))
        veil.setColorAt(1, QColor(0, 0, 0, int(90 + 60 * v)))
        p.fillRect(self.rect(), QBrush(veil))
