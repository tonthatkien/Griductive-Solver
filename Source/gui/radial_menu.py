"""RadialMenu: vòng chọn verdict quanh thẻ (còng tay / huy hiệu). (Scope F)
"""
import math
from typing import List, Tuple

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, Qt,
                            Signal)
from PySide6.QtGui import (QBrush, QColor, QPainter,
                           QRadialGradient)
from PySide6.QtWidgets import (QWidget)

from gui import icons, theme
from gui.icons import NO_BRUSH, pen
from gui.anim import Tween
from gui.draw_utils import (ALIGN_CENTER, make_font)


class RadialMenu(QWidget):
    """Vòng chọn verdict hiện quanh thẻ: còng tay (CRIMINAL) / huy hiệu (INNOCENT)."""

    chosen = Signal(str, str)      # cell, verdict
    closed = Signal()
    BTN_RADIUS = 42.0

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._cell, self._name, self._anchor = "", "", QPointF()
        self._hover = -1
        self._open = Tween(self, self.update, QEasingCurve.Type.OutBack)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

    def open_at(self, cell: str, name: str, anchor: QPointF) -> None:
        self._cell, self._name, self._anchor, self._hover = cell, name, anchor, -1
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus()
        self._open.jump(0.0)
        self._open.go(1.0, 320)

    def close_menu(self) -> None:
        if self.isVisible():
            self.hide()
            self.closed.emit()

    def _layout(self) -> Tuple[QPointF, float, List[Tuple[str, QPointF]]]:
        k = self._open.now
        reach = 96.0 * k
        margin = 96.0 + self.BTN_RADIUS + 24
        x = min(max(self._anchor.x(), margin), max(margin, self.width() - margin))
        y = min(max(self._anchor.y(), self.BTN_RADIUS + 50), max(self.BTN_RADIUS + 50, self.height() - 90))
        center = QPointF(x, y)
        return center, reach, [("CRIMINAL", QPointF(x - reach, y)), ("INNOCENT", QPointF(x + reach, y))]

    def _hit(self, pos: QPointF) -> int:
        _, _, buttons = self._layout()
        for i, (_, c) in enumerate(buttons):
            if math.hypot(pos.x() - c.x(), pos.y() - c.y()) <= self.BTN_RADIUS * 1.1:
                return i
        return -1

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        k = min(1.0, self._open.now)
        p.fillRect(self.rect(), QColor(2, 6, 16, int(165 * k)))
        center, reach, buttons = self._layout()
        p.setOpacity(min(1.0, k * 1.5))
        p.setBrush(NO_BRUSH)
        for width, alpha in ((10, 25), (3, 150)):
            p.setPen(pen(QColor(226, 185, 71, alpha), width))
            p.drawEllipse(center, reach, reach)
        p.setBrush(QColor(8, 14, 30, 235))
        p.setPen(pen(theme.GOLD, 2))
        p.drawEllipse(center, 36, 36)
        p.setPen(QColor(theme.GOLD_SOFT))
        p.setFont(make_font(theme.FONT_MONO, 18, True))
        p.drawText(QRectF(center.x() - 36, center.y() - 20, 72, 24), ALIGN_CENTER, self._cell)
        p.setFont(make_font(theme.FONT_DOSSIER, 11, False, True))
        p.setPen(QColor("#cdd7f0"))
        p.drawText(QRectF(center.x() - 36, center.y() + 2, 72, 18), ALIGN_CENTER, self._name)
        specs = {"CRIMINAL": ("#ff3b4e", "#7a0f1d", icons.draw_handcuffs, "CRIMINAL", "Còng tay"),
                 "INNOCENT": ("#3b8bff", "#123a7a", icons.draw_badge, "INNOCENT", "Huy hiệu")}
        for i, (verdict, c) in enumerate(buttons):
            rim, fill, painter_fn, title, sub = specs[verdict]
            rad = self.BTN_RADIUS * (1.14 if i == self._hover else 1.0)
            if i == self._hover:
                glow = QColor(rim)
                for width, alpha in ((18, 40), (10, 80)):
                    glow.setAlpha(alpha)
                    p.setPen(pen(glow, width))
                    p.setBrush(NO_BRUSH)
                    p.drawEllipse(c, rad, rad)
            body = QRadialGradient(QPointF(c.x(), c.y() - rad * 0.4), rad * 1.6)
            body.setColorAt(0, QColor(fill).lighter(160))
            body.setColorAt(1, QColor(fill).darker(220))
            p.setBrush(QBrush(body))
            p.setPen(pen(rim, 3))
            p.drawEllipse(c, rad, rad)
            painter_fn(p, QRectF(c.x() - rad * 0.62, c.y() - rad * 0.62, rad * 1.24, rad * 1.24))
            p.setPen(QColor(rim).lighter(135))
            p.setFont(make_font(theme.FONT_GADGET, 12, True, spacing=1))
            p.drawText(QRectF(c.x() - 70, c.y() + rad + 4, 140, 18), ALIGN_CENTER, title)
            p.setPen(QColor("#9fb0d8"))
            p.setFont(make_font(theme.FONT_DOSSIER, 11, False, True))
            p.drawText(QRectF(c.x() - 70, c.y() + rad + 22, 140, 16), ALIGN_CENTER, sub)

    def mouseMoveEvent(self, event) -> None:
        hover = self._hit(event.position())
        if hover != self._hover:
            self._hover = hover
            self.setCursor(Qt.CursorShape.PointingHandCursor if hover >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, event) -> None:
        index = self._hit(event.position())
        if index >= 0 and event.button() == Qt.MouseButton.LeftButton:
            verdict = self._layout()[2][index][0]
            self.hide()
            self.chosen.emit(self._cell, verdict)
        else:
            self.close_menu()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()
