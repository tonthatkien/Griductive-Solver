"""NightBackdrop: nền thành phố ban đêm (trăng, sao, nhà cao tầng, đèn pin). (Scope F)
"""
import math
import random
from typing import Optional

from PySide6.QtCore import (QPointF, QRectF, Signal)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import (QWidget)

from gui import theme
from gui.icons import NO_PEN
from gui.anim import clock


class NightBackdrop(QWidget):
    """Nền thành phố ban đêm: trăng, sao nhấp nháy, nhà cao tầng, vệt đèn pin quét chậm."""

    resized = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        rng = random.Random(11)
        self._stars = [(rng.random(), rng.random() * 0.6, rng.uniform(0, 6.28), rng.uniform(0.6, 2.2))
                       for _ in range(110)]
        self._buildings, x = [], 0.0
        while x < 1.0:
            bw, bh = rng.uniform(0.04, 0.09), rng.uniform(0.07, 0.2)
            lit = [rng.random() < 0.35 for _ in range(30)]
            self._buildings.append((x, bw, bh, lit))
            x += bw + rng.uniform(0.0, 0.01)
        self._t, self._t0 = 0.0, clock().t
        clock().tick.connect(self._tick)

    def _tick(self) -> None:
        self._t = clock().t - self._t0
        if self.isVisible():
            self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.resized.emit()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor(theme.NIGHT_TOP))
        sky.setColorAt(0.65, QColor(theme.NIGHT_MID))
        sky.setColorAt(1, QColor(theme.NIGHT_BOTTOM))
        p.fillRect(self.rect(), QBrush(sky))
        moon = QPointF(w * 0.9, h * 0.13)
        glow = QRadialGradient(moon, min(w, h) * 0.16)
        glow.setColorAt(0, QColor(255, 244, 200, 120))
        glow.setColorAt(1, QColor(255, 244, 200, 0))
        p.fillRect(self.rect(), QBrush(glow))
        p.setPen(NO_PEN)
        p.setBrush(QColor("#fff4cf"))
        p.drawEllipse(moon, min(w, h) * 0.035, min(w, h) * 0.035)
        for sx, sy, phase, speed in self._stars:
            alpha = int(60 + 150 * (0.5 + 0.5 * math.sin(self._t * speed + phase)))
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(QPointF(sx * w, sy * h), 1.2, 1.2)
        angle = math.radians(-62 + 10 * math.sin(self._t * 0.45))
        origin, length, spread = QPointF(w * 0.04, h), h * 1.1, math.radians(9)
        tip1 = origin + QPointF(math.cos(angle - spread), math.sin(angle - spread)) * length
        tip2 = origin + QPointF(math.cos(angle + spread), math.sin(angle + spread)) * length
        beam = QLinearGradient(origin, (tip1 + tip2) / 2)
        beam.setColorAt(0, QColor(255, 255, 235, 46))
        beam.setColorAt(1, QColor(255, 255, 235, 0))
        p.setBrush(QBrush(beam))
        p.drawPolygon(QPolygonF([origin, tip1, tip2]))
        for bx, bw, bh, lit in self._buildings:
            rect = QRectF(bx * w, h - bh * h, bw * w, bh * h)
            p.setBrush(QColor("#060b19"))
            p.drawRect(rect)
            cols, rows = 3, 6
            for i in range(cols * rows):
                if lit[i % len(lit)]:
                    wx = rect.left() + rect.width() * (0.15 + 0.28 * (i % cols))
                    wy = rect.top() + rect.height() * (0.1 + 0.14 * (i // cols))
                    p.setBrush(QColor(242, 193, 78, 150))
                    p.drawRect(QRectF(wx, wy, rect.width() * 0.14, rect.height() * 0.07))
