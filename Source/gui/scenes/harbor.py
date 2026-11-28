"""Bến cảng về đêm: cần cẩu, container, tàu hàng, hải đăng quét chùm sáng, sóng nước và phao nhấp nháy."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, beam, col, glow, poly, strokes, vgrad

_HORIZON = 0.6
_LIGHT = (0.9, 0.34)
_BOXES = ("#3a1f1f", "#1f2f3a", "#2f3a1f", "#3a331f", "#2a1f3a")


class HarborScene(Scene):
    name = "harbor"
    seed = 101

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.5) for _ in range(80)]
        self.far = [(rng.uniform(0.02, 0.98), rng.choice(("#ffd98a", "#cfe6ff", "#ff9b6a"))) for _ in range(30)]

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#050a18"), (0.6, "#14284a"), (1, "#2a4f7a")], 0.0, _HORIZON)
        vgrad(p, w, h, [(0, "#0b2038"), (1, "#03070f")], _HORIZON, 1.0)
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 110))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        for x, c in self.far:                                             # đèn thành phố xa
            p.setBrush(col(c, 170))
            p.drawEllipse(QPointF(x * w, h * (_HORIZON - 0.012)), 1.6, 1.6)
        p.setPen(pen("#05090f", 1))
        x = 0.02                                                          # bãi container
        for row in range(2):
            x = 0.02
            while x < 0.40:
                bw = 0.045
                p.setBrush(col(rng.choice(_BOXES)))
                p.drawRect(QRectF(w * x, h * (0.585 - 0.04 * (row + 1)) + 6, w * bw, h * 0.04))
                x += bw + 0.004
        for cx in (0.12, 0.3):                                            # cần cẩu giàn
            p.setPen(pen("#05090f", 6))
            for dx in (-0.025, 0.025):
                p.drawLine(QPointF(w * (cx + dx), h * 0.6), QPointF(w * (cx + dx), h * 0.3))
            p.setPen(pen("#05090f", 5))
            p.drawLine(QPointF(w * (cx - 0.07), h * 0.3), QPointF(w * (cx + 0.16), h * 0.3))
            p.drawLine(QPointF(w * (cx + 0.16), h * 0.3), QPointF(w * (cx + 0.16), h * 0.4))
        hull = [(w * 0.5, h * 0.6), (w * 0.84, h * 0.6), (w * 0.8, h * 0.655), (w * 0.54, h * 0.655)]   # tàu hàng
        poly(p, hull, "#060a14")
        p.setBrush(col("#060a14"))
        p.drawRect(QRectF(w * 0.74, h * 0.53, w * 0.06, h * 0.07))
        p.drawRect(QRectF(w * 0.77, h * 0.5, w * 0.025, h * 0.03))
        lx, ly = w * _LIGHT[0], h * _LIGHT[1]                             # hải đăng
        poly(p, [(lx - 14, h * _HORIZON), (lx + 14, h * _HORIZON), (lx + 7, ly + 14), (lx - 7, ly + 14)], "#0a0f1c", "#2a3550")
        p.setBrush(col("#0a0f1c"))
        p.setPen(pen("#2a3550", 1.5))
        p.drawRect(QRectF(lx - 10, ly, 20, 14))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        lx, ly = w * _LIGHT[0], h * _LIGHT[1] + 7
        ang = math.pi - 0.1 + 0.42 * math.sin(t * 0.5)                    # chùm sáng quét qua lại
        beam(p, lx, ly, ang, 0.07, w * 0.95, "#fff6d8", 85)
        glow(p, lx, ly, 34, "#fff6d8", 190)
        for k in range(9):                                                # sóng
            y = h * (_HORIZON + 0.025 + k * 0.045)
            path = QPainterPath()
            for i in range(41):
                x = w * i / 40
                yy = y + (2 + k * 0.5) * math.sin(i * 0.8 + t * (0.8 + k * 0.07) + k)
                path.moveTo(QPointF(x, yy)) if i == 0 else path.lineTo(QPointF(x, yy))
            strokes(p, col("#7fb8e8", 26 + k * 3), 1.2)
            p.drawPath(path)
        for x, c in self.far[::2]:                                        # ánh đèn xa lung linh dưới nước
            strokes(p, col(c, 70), 1.6)
            y = h * (_HORIZON + 0.03)
            sh = 4 * math.sin(t * 1.5 + x * 30)
            p.drawLine(QPointF(x * w + sh, y), QPointF(x * w + sh, y + h * 0.05))
        on = int(t * 1.4) % 2 == 0                                        # phao đỏ nhấp nháy
        bx, by = w * 0.46, h * 0.74 + 2 * math.sin(t * 1.2)
        p.setPen(NO_PEN)
        p.setBrush(col("#ff3b4e" if on else "#5a1a22"))
        p.drawEllipse(QPointF(bx, by), 4, 4)
        if on:
            glow(p, bx, by, 26, "#ff3b4e", 180)
        for k in range(5):                                                # đèn cabin tàu
            p.setBrush(col("#ffd98a", 150 + 60 * math.sin(t * 2 + k * 1.7)))
            p.drawRect(QRectF(w * (0.745 + k * 0.01), h * 0.545, 3, 4))
