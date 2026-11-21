"""NeonTitle (tiêu đề neon) + TerminalMessage (khung thông báo kiểu terminal). (Scope F)
"""
import math
from typing import Optional

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, QSize, Qt)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainter,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QSizePolicy, QWidget)

from gui import theme
from gui.icons import NO_PEN, pen
from gui.anim import Tween, Typer, clock
from gui.draw_utils import (ALIGN_CENTER, draw_typed, make_font)


class NeonTitle(QWidget):
    """Tiêu đề phát sáng: chữ giãn cách, quầng cyan + đỏ nhịp thở, vệt laser quét qua chữ."""

    def __init__(self, text: str, parent: Optional[QWidget] = None, px: int = 26, spacing: float = 5.0,
                 gadget: bool = False, core: str = "#f5e7b8") -> None:
        super().__init__(parent)
        self._text, self._px, self._spacing, self._gadget, self._core = text, px, spacing, gadget, core
        self._glow_cache: Optional[QPixmap] = None
        self._glow_key: tuple = ()
        self._anim = Tween(self, self.update, QEasingCurve.Type.Linear)
        self._anim.loop(3600)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _font(self) -> QFont:
        family = theme.FONT_GADGET if self._gadget else theme.FONT_TITLE
        return make_font(family, self._px, True, spacing=self._spacing)

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self._font())
        return QSize(int(metrics.horizontalAdvance(self._text) + len(self._text) * self._spacing) + 30,
                     int(metrics.height()) + 16)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _glow_pixmap(self, font: QFont, rect: QRectF) -> QPixmap:
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, self._text, self._px)
        if self._glow_cache is None or self._glow_key != key:
            pix = QPixmap(int(rect.width() * dpr), int(rect.height() * dpr))
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.GlobalColor.transparent)
            g = QPainter(pix)
            g.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            g.setFont(font)
            for color, offset in ((theme.RED_NEON, QPointF(2, 1)), (theme.CYAN_LASER, QPointF(0, 0))):
                for radius, alpha in ((7, 12), (5, 22), (3, 40), (1.5, 70)):
                    tint = QColor(color)
                    tint.setAlpha(alpha)
                    g.setPen(tint)
                    for k in range(12):
                        angle = 2 * math.pi * k / 12
                        g.drawText(rect.translated(offset + QPointF(math.cos(angle) * radius,
                                                                    math.sin(angle) * radius)),
                                   ALIGN_CENTER, self._text)
            g.end()
            self._glow_cache, self._glow_key = pix, key
        return self._glow_cache

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect, font, t = QRectF(self.rect()), self._font(), self._anim.now
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)
        p.setOpacity(0.55 + 0.45 * pulse)
        p.drawPixmap(QPointF(0, 0), self._glow_pixmap(font, rect))
        p.setOpacity(1.0)
        p.setFont(font)
        stops = {0.0: QColor(self._core), 1.0: QColor(self._core)}
        centre = -0.15 + 1.3 * t                       # vệt laser quét từ trái sang phải
        for pos, color in ((centre - 0.1, self._core), (centre, "#ffffff"), (centre + 0.1, self._core)):
            if 0.0 <= pos <= 1.0:
                stops[pos] = QColor(color)
        sweep = QLinearGradient(rect.left(), 0, rect.right(), 0)
        for pos in sorted(stops):
            sweep.setColorAt(pos, stops[pos])
        p.setPen(QPen(QBrush(sweep), 1))
        p.drawText(rect, ALIGN_CENTER, self._text)


class TerminalMessage(QWidget):
    """Khung thông báo kiểu terminal: gõ chữ từng ký tự, viền đổi màu theo kind (info/ok/warn/bad)
    và một đèn LED ở góc trái (xanh nhịp tim = ok, vàng nhấp nháy = warn, đỏ chớp = bad)."""

    _TONES = {"info": ("#2c4170", "#dfe7fb"), "ok": ("#2fae6b", "#b9f5d2"),
              "warn": (theme.GOLD, "#ffe9a6"), "bad": (theme.RED_NEON, "#ffc2c8")}
    _LEDS = {"info": "#4aa8ff", "ok": "#39ff14", "warn": "#ffd166", "bad": "#ff3b4e"}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._kind = "info"
        self.typer = Typer(self)
        self.typer.changed.connect(self.update)
        self.setMinimumHeight(70)
        clock().tick.connect(self._on_tick)

    def set_message(self, text: str, kind: str = "info") -> None:
        self._kind = kind if kind in self._TONES else "info"
        self.typer.start(text)
        self.update()

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def _led_level(self) -> float:
        t = clock().t
        if self._kind == "bad":
            return 1.0 if int(t * 3) % 2 == 0 else 0.15                         # chớp liên tục
        if self._kind == "warn":
            return 0.4 + 0.6 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.6 * t))    # nhấp nháy
        if self._kind == "ok":
            return 0.35 + 0.65 * max(0.0, math.sin(2 * math.pi * 1.1 * t)) ** 3   # nhịp tim
        return 0.7

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        border, color = self._TONES[self._kind]
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(QColor(8, 14, 30, 220))
        p.setPen(pen(border, 1.5))
        p.drawRoundedRect(rect, 8, 8)
        level, led = self._led_level(), QColor(self._LEDS[self._kind])
        center = QPointF(rect.left() + 18, rect.top() + 18)
        p.setPen(NO_PEN)
        halo = QColor(led)
        halo.setAlpha(int(75 * level))
        p.setBrush(halo)
        p.drawEllipse(center, 9, 9)
        core = QColor(led)
        core.setAlpha(int(255 * level))
        p.setBrush(core)
        p.drawEllipse(center, 4.5, 4.5)
        draw_typed(p, rect.adjusted(34, 8, -14, -8), self.typer.text, self.typer.shown,
                   theme.FONT_DOSSIER, 15, 10, color, cursor=self.typer.cursor_visible)
