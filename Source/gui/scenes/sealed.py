"""Hiện trường bị phong tỏa: đèn hú đỏ/xanh luân phiên, băng vàng phong toả chéo màn hình, vạch phấn trên đường."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui import theme
from gui.draw_utils import ALIGN_LEFT_MID, make_font
from gui.icons import pen
from gui.scenes.base import Scene, beam, col, dust, glow, make_motes, strokes, vgrad

_TAPE_TEXT = "HIỆN TRƯỜNG PHONG TỎA  ·  KHÔNG ĐƯỢC VƯỢT QUA  ·  " * 6


class SealedScene(Scene):
    name = "sealed"
    seed = 141

    def setup(self) -> None:
        self.motes = make_motes(random.Random(self.seed), 40)

    @staticmethod
    def _tape(p: QPainter, x0: float, y0: float, x1: float, y1: float, width: float) -> None:
        length = math.hypot(x1 - x0, y1 - y0)
        p.save()
        p.translate(x0, y0)
        p.rotate(math.degrees(math.atan2(y1 - y0, x1 - x0)))
        band = QRectF(0, -width / 2, length, width)
        p.setPen(pen("#1a1405", 1.5))
        p.setBrush(col("#e8c02a", 235))
        p.drawRect(band)
        p.setClipRect(band)
        p.setFont(make_font(theme.FONT_GADGET, int(width * 0.5), True, spacing=2))
        p.setPen(col("#1a1405"))
        p.drawText(band.adjusted(8, 0, 0, 0), ALIGN_LEFT_MID, _TAPE_TEXT)
        p.restore()

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#04050c"), (0.7, "#0b0e1a"), (1, "#131826")])
        p.setPen(pen(col("#1f2638", 150), 1))                            # tường gạch
        y = 0.0
        while y < h * 0.7:
            p.drawLine(QPointF(0, y), QPointF(w, y))
            y += 26
        vgrad(p, w, h, [(0, "#0d101a"), (1, "#05060b")], 0.72, 1.0)       # mặt đường
        p.setPen(pen("#2a3040", 3))
        p.drawLine(QPointF(0, h * 0.72), QPointF(w, h * 0.72))
        cx, cy = w * 0.5, h * 0.86                                        # vạch phấn hình người nằm
        strokes(p, col("#f4f0ff", 110), 2.2)
        p.drawEllipse(QPointF(cx - 46, cy), 11, 11)
        p.drawLine(QPointF(cx - 34, cy), QPointF(cx + 26, cy))
        p.drawLine(QPointF(cx - 20, cy), QPointF(cx - 30, cy - 22))
        p.drawLine(QPointF(cx - 14, cy), QPointF(cx - 6, cy + 24))
        p.drawLine(QPointF(cx + 26, cy), QPointF(cx + 58, cy - 14))
        p.drawLine(QPointF(cx + 26, cy), QPointF(cx + 56, cy + 16))
        self._tape(p, -20, h * 0.30, w + 20, h * 0.55, 34)
        self._tape(p, -20, h * 0.62, w + 20, h * 0.28, 34)

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        r = 0.5 + 0.5 * math.sin(t * 5.0)                                 # đỏ và xanh luân phiên
        b = 1.0 - r
        glow(p, 0, h * 0.15, w * 0.55, "#ff2b3d", 110 * r)
        glow(p, w, h * 0.15, w * 0.55, "#2b7bff", 110 * b)
        beam(p, 0, 0, 0.8 + 0.5 * math.sin(t * 2.5), 0.22, w, "#ff2b3d", 60 * r)
        beam(p, w, 0, math.pi - 0.8 - 0.5 * math.sin(t * 2.5 + 1.0), 0.22, w, "#2b7bff", 60 * b)
        p.fillRect(QRectF(0, 0, w, h), col("#ff2b3d", 14 * r))
        p.fillRect(QRectF(0, 0, w, h), col("#2b7bff", 14 * b))
        dust(p, w, h, t, self.motes, "#c8d8ff", 100)
