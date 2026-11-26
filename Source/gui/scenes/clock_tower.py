"""Tháp đồng hồ: mặt đồng hồ lớn phát sáng với kim chạy, bánh răng cơ khí xoay trên nền trời, mây che trăng."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, col, egl, gear, glow, poly, strokes, vgrad

_FACE = (0.5, 0.40)
_MOON = (0.85, 0.15)
# (x, y, bán kính theo min(w, h), số răng, tốc độ quay)
_GEARS = ((0.20, 0.30, 0.10, 14, 0.35), (0.30, 0.46, 0.06, 9, -0.55), (0.80, 0.34, 0.09, 12, -0.4),
          (0.70, 0.50, 0.055, 8, 0.6))


class ClockTowerScene(Scene):
    name = "clock_tower"
    seed = 121

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.55) for _ in range(90)]
        self.clouds = [(rng.random(), rng.uniform(0.08, 0.5), rng.uniform(0.15, 0.3), rng.uniform(0.006, 0.016))
                       for _ in range(6)]

    @staticmethod
    def _geo(w: float, h: float):
        return w * _FACE[0], h * _FACE[1], min(w, h) * 0.17

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#04081a"), (0.6, "#101c3c"), (1, "#1c2c52")])
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 120))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        mx, my, mr = w * _MOON[0], h * _MOON[1], min(w, h) * 0.035
        glow(p, mx, my, mr * 6, "#fff4cf", 80)
        p.setBrush(col("#fff4cf"))
        p.drawEllipse(QPointF(mx, my), mr, mr)
        cx, cy, r = self._geo(w, h)
        body = "#070b14"                                                 # thân tháp + mái chóp
        p.setPen(pen("#1a2438", 2))
        p.setBrush(col(body))
        p.drawRect(QRectF(cx - r * 1.3, cy - r * 1.3, r * 2.6, h - cy + r * 1.3))
        poly(p, [(cx - r * 1.5, cy - r * 1.3), (cx, cy - r * 3.0), (cx + r * 1.5, cy - r * 1.3)], body, "#1a2438")
        p.setPen(pen(col("#1a2438", 170), 1))                            # gạch tháp
        y = cy + r * 1.3
        while y < h:
            p.drawLine(QPointF(cx - r * 1.3, y), QPointF(cx + r * 1.3, y))
            y += 22
        p.setBrush(col("#d9cfa4", 235))                                  # mặt đồng hồ
        p.setPen(pen("#c9a24b", 6))
        p.drawEllipse(QPointF(cx, cy), r, r)
        for i in range(12):
            a = i * math.pi / 6
            big = i % 3 == 0
            strokes(p, "#2b1d0e", 4 if big else 2)
            p.drawLine(QPointF(cx + math.cos(a) * r * (0.78 if big else 0.86), cy + math.sin(a) * r * (0.78 if big else 0.86)),
                       QPointF(cx + math.cos(a) * r * 0.94, cy + math.sin(a) * r * 0.94))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        cx, cy, r = self._geo(w, h)
        glow(p, cx, cy, r * 2.4, "#ffe9a8", 55 + 20 * math.sin(t * 1.1))
        for gx, gy, gr, teeth, sp in _GEARS:                             # bánh răng cơ khí
            gear(p, w * gx, h * gy, min(w, h) * gr, teeth, t * sp, col("#2a3550", 150), "#4a5a7a")
        for x, y, sz, sp in self.clouds:                                 # mây trôi
            egl(p, ((x + t * sp) % 1.3 - 0.15) * w, y * h, w * sz, h * 0.045, "#101a33", 150)
        for ang, ln, wd in ((t * 0.05, 0.5, 6), (t * 0.6, 0.78, 4)):     # kim giờ, kim phút
            a = ang - math.pi / 2
            strokes(p, "#1a1208", wd)
            p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * r * ln, cy + math.sin(a) * r * ln))
        a = t * 3.0 - math.pi / 2                                        # kim giây
        strokes(p, "#c0182b", 2)
        p.drawLine(QPointF(cx - math.cos(a) * r * 0.15, cy - math.sin(a) * r * 0.15),
                   QPointF(cx + math.cos(a) * r * 0.88, cy + math.sin(a) * r * 0.88))
        p.setPen(NO_PEN)
        p.setBrush(col("#c0182b"))
        p.drawEllipse(QPointF(cx, cy), 5, 5)
