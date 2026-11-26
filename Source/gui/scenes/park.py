"""Công viên ven sông: trăng soi mặt nước, cầu vòm, liễu rủ, đèn đường, đom đóm và sương."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, col, dust, fog, glow, make_motes, strokes, vgrad

_MOON = (0.7, 0.2)
_LAMPS = (0.22, 0.5, 0.78)


class ParkScene(Scene):
    name = "park"
    seed = 81

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.4) for _ in range(80)]
        self.fireflies = make_motes(rng, 22)
        self.skyline = []
        x = 0.0
        while x < 1.0:
            bw = rng.uniform(0.03, 0.07)
            self.skyline.append((x, bw, rng.uniform(0.05, 0.16)))
            x += bw

    def _willow(self, p: QPainter, rng: random.Random, x: float, h: float, s: float) -> None:
        top = QPointF(x, h * (0.86 - 0.3 * s))
        p.setPen(pen("#05100c", 8 * s))
        p.drawLine(QPointF(x, h * 0.88), top)
        for _ in range(26):                                             # cành liễu rủ
            a = rng.uniform(-1.0, 1.0)
            sx, sy = top.x() + a * h * 0.12 * s, top.y() + abs(a) * h * 0.03
            p.setPen(pen(col("#0c2a1e", 200), 1.6))
            p.drawLine(QPointF(sx, sy), QPointF(sx + a * h * 0.05 * s, sy + h * rng.uniform(0.12, 0.26) * s))

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#050a18"), (0.5, "#14264a"), (0.6, "#1f3560")], 0.0, 0.6)
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 110))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        mx, my, mr = w * _MOON[0], h * _MOON[1], min(w, h) * 0.04
        glow(p, mx, my, mr * 7, "#cfe0ff", 70)
        p.setBrush(col("#f4f8ff"))
        p.drawEllipse(QPointF(mx, my), mr, mr)
        for x, bw, bh in self.skyline:                                  # đường chân trời xa
            p.setBrush(col("#0a1226"))
            p.drawRect(QRectF(x * w, h * (0.58 - bh), bw * w, h * bh))
            for _ in range(2):
                p.setBrush(col("#ffd98a", 120))
                p.drawRect(QRectF(x * w + rng.uniform(0.1, 0.8) * bw * w, h * (0.58 - rng.uniform(0.02, bh)), 3, 3))
        vgrad(p, w, h, [(0, "#0b2a4a"), (1, "#050e1c")], 0.58, 0.87)    # mặt sông
        vgrad(p, w, h, [(0, "#06130d"), (1, "#020805")], 0.87, 1.0)     # bờ cỏ
        p.setPen(pen("#06090f", 3))                                     # cầu vòm
        p.setBrush(col("#06090f"))
        p.drawRect(QRectF(w * 0.28, h * 0.555, w * 0.34, h * 0.03))
        for k in range(3):
            cx = w * (0.34 + k * 0.11)
            strokes(p, "#06090f", 5)
            p.drawArc(QRectF(cx - w * 0.045, h * 0.575, w * 0.09, h * 0.09), 0, 180 * 16)
        self._willow(p, rng, w * 0.10, h, 1.0)
        self._willow(p, rng, w * 0.92, h, 0.85)
        for lx in _LAMPS:                                               # cột đèn
            p.setPen(pen("#04070c", 3))
            p.drawLine(QPointF(w * lx, h * 0.88), QPointF(w * lx, h * 0.72))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        mx = w * _MOON[0]
        for i in range(16):                                             # bóng trăng gợn trên sông
            y = h * (0.6 + i * 0.016)
            half = (14 + i * 5) * (1 + 0.25 * math.sin(t * 1.3 + i))
            strokes(p, col("#d8e8ff", 120 * (1 - i / 17)), 2.2)
            p.drawLine(QPointF(mx - half + 6 * math.sin(t * 0.9 + i), y), QPointF(mx + half + 6 * math.sin(t * 0.9 + i), y))
        for lx in _LAMPS:
            flick = 0.85 + 0.15 * math.sin(t * 6 + lx * 20)
            glow(p, w * lx, h * 0.72, 60, "#ffd98a", 150 * flick)
            p.setPen(NO_PEN)
            p.setBrush(col("#fff1c8"))
            p.drawEllipse(QPointF(w * lx, h * 0.72), 4, 4)
            strokes(p, col("#ffd98a", 50 * flick), 3)                   # vệt đèn dưới nước
            p.drawLine(QPointF(w * lx, h * 0.74), QPointF(w * lx, h * 0.86))
        fog(p, w, h, t, "#9fc0d8", 4, 20, 0.62)
        dust(p, w, h, t, self.fireflies, "#c8ff7a", 210, 0.004)
