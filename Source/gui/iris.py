"""IrisTransition: hiệu ứng khép/mở vòng tròn kiểu đóng màn phim hoạt hình. (Scope F)

close_to(tâm, callback): vòng tròn thu nhỏ về `tâm` cho tới khi màn đen kín, rồi gọi callback
(lúc này mới đổi trang, nạp màn chơi...). open_from(tâm, callback): vòng tròn mở rộng từ `tâm`.
Trong lúc hiệu ứng chạy, widget này chặn chuột nên người chơi không bấm được gì phía sau.
"""
import math
from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from gui import theme
from gui.anim import Tween
from gui.icons import NO_BRUSH, pen

CLOSE_MS = 520
OPEN_MS = 640
CURTAIN = QColor(2, 5, 12)


class IrisTransition(QWidget):
    """Lớp phủ toàn khung, con của widget cần chuyển cảnh."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._center = QPointF()
        self._closing = True
        self._callback: Optional[Callable[[], None]] = None
        self._anim = Tween(self, self.update, QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._done)
        self.hide()

    def close_to(self, center: QPointF, callback: Optional[Callable[[], None]] = None) -> None:
        self._start(center, True, callback, CLOSE_MS)

    def open_from(self, center: QPointF, callback: Optional[Callable[[], None]] = None) -> None:
        self._start(center, False, callback, OPEN_MS)

    def _start(self, center: QPointF, closing: bool,
               callback: Optional[Callable[[], None]], ms: int) -> None:
        self._center, self._closing, self._callback = QPointF(center), closing, callback
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._anim.jump(0.0)
        self._anim.go(1.0, ms)

    def _done(self) -> None:
        callback, self._callback = self._callback, None
        if not self._closing:
            self.hide()
        if callback is not None:
            QTimer.singleShot(0, callback)       # màn vẫn đen kín cho tới khi open_from chạy

    def paintEvent(self, _event) -> None:
        t = self._anim.now
        w, h, c = float(self.width()), float(self.height()), self._center
        max_r = math.hypot(max(c.x(), w - c.x()), max(c.y(), h - c.y())) + 6.0
        r = max_r * (1.0 - t) if self._closing else max_r * t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        outer = QPainterPath()
        outer.addRect(QRectF(self.rect()))
        hole = QPainterPath()
        hole.addEllipse(c, r, r)
        p.fillPath(outer.subtracted(hole), CURTAIN)
        if 3.0 < r < max_r - 3.0:                # viền vàng quanh mép vòng tròn
            p.setBrush(NO_BRUSH)
            for width, alpha in ((12, 30), (4, 150)):
                ring = QColor(theme.GOLD)
                ring.setAlpha(alpha)
                p.setPen(pen(ring, width))
                p.drawEllipse(c, r, r)
