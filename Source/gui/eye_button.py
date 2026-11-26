"""EyeButton: nút "con mắt" ẩn/hiện giao diện để ngắm nền. (Scope F)

closed=False: mắt mở (đang hiện giao diện, bấm để ẩn). closed=True: mắt gạch chéo (đang ẩn, bấm để hiện lại).
Bản nổi (có nhãn) hiện ở góc màn hình khi giao diện đã ẩn, thở nhẹ để người chơi biết đường quay lại.
"""
import math
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractButton, QWidget

from gui import theme
from gui.anim import Tween, clock
from gui.draw_utils import ALIGN_LEFT_MID, make_font
from gui.icons import NO_BRUSH, NO_PEN, pen

_H = 40


class EyeButton(QAbstractButton):
    def __init__(self, label: str = "", tooltip: str = "", closed: bool = False,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label, self._closed = label, closed
        self._hover = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)        # để phím Space không "bấm" nút này lần nữa
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        text_w = QFontMetricsF(self._font()).horizontalAdvance(label) + 14 if label else 0
        self._size = QSize(int(46 + text_w), _H)
        self.setFixedSize(self._size)
        clock().tick.connect(self._on_tick)

    @staticmethod
    def _font():
        return make_font(theme.FONT_MONO, 10, True, spacing=1.2)

    def sizeHint(self) -> QSize:
        return self._size

    def set_closed(self, closed: bool) -> None:
        self._closed = closed
        self.update()

    def _on_tick(self) -> None:
        if self._label and self.isVisible():
            self.update()

    def enterEvent(self, event) -> None:
        self._hover.go(1.0, 140)

    def leaveEvent(self, event) -> None:
        self._hover.go(0.0, 200)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        hov = self._hover.now
        breath = 0.5 + 0.5 * math.sin(clock().t * 2.4) if self._label else 0.0
        accent = QColor(theme.GOLD_SOFT if self._closed else theme.CYAN_LASER)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        plate = QPainterPath()
        plate.addRoundedRect(r, 12, 12)
        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0, QColor(18, 34, 70, 235))
        bg.setColorAt(1, QColor(6, 12, 28, 240))
        p.fillPath(plate, QBrush(bg))
        p.setBrush(NO_BRUSH)
        halo = QColor(accent)
        halo.setAlpha(int(24 + 30 * hov + 40 * breath))
        p.setPen(pen(halo, 6))
        p.drawPath(plate)
        edge = QColor(accent)
        edge.setAlpha(int(170 + 80 * hov))
        p.setPen(pen(edge, 1.6))
        p.drawPath(plate)
        # con mắt: hình hạnh nhân + mống mắt + đồng tử
        cx, cy, half_w, half_h = r.left() + 22, r.center().y(), 13.0, 8.5
        eye = QPainterPath()
        eye.moveTo(cx - half_w, cy)
        eye.quadTo(cx, cy - half_h * 2.1, cx + half_w, cy)
        eye.quadTo(cx, cy + half_h * 2.1, cx - half_w, cy)
        p.setBrush(QColor(4, 10, 24, 220))
        p.setPen(pen(accent, 2.0))
        p.drawPath(eye)
        p.setPen(NO_PEN)
        iris = QColor(accent)
        iris.setAlpha(210)
        p.setBrush(iris)
        p.drawEllipse(QPointF(cx, cy), 5.6, 5.6)
        p.setBrush(QColor(4, 10, 24))
        p.drawEllipse(QPointF(cx, cy), 2.6, 2.6)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawEllipse(QPointF(cx - 1.8, cy - 1.8), 1.1, 1.1)
        if self._closed:                                     # gạch chéo: giao diện đang ẩn
            a, b = QPointF(cx - half_w + 2, cy + half_h + 3), QPointF(cx + half_w - 2, cy - half_h - 3)
            p.setBrush(NO_BRUSH)
            p.setPen(pen(QColor(4, 10, 24), 5.5))
            p.drawLine(a, b)
            p.setPen(pen(accent, 2.4))
            p.drawLine(a, b)
        if self._label:
            p.setFont(self._font())
            p.setPen(QColor("#fff1c8" if self._closed else "#bff6ff"))
            p.drawText(QRectF(r.left() + 42, r.top(), r.width() - 46, r.height()), ALIGN_LEFT_MID, self._label)
