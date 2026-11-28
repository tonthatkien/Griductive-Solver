"""Sân thượng cao ốc: nhìn xuống biển đèn thành phố, ăng-ten đèn đỏ nhấp nháy, trực thăng rọi đèn pha, mây gió."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, beam, col, egl, glow, poly, strokes, vgrad

_ANTENNA = 0.14


class RooftopScene(Scene):
    name = "rooftop"
    seed = 131
    accent = "#fff6d8"

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.4) for _ in range(70)]
        self.clouds = [(rng.random(), rng.uniform(0.05, 0.4), rng.uniform(0.2, 0.36), rng.uniform(0.01, 0.025))
                       for _ in range(5)]
        self.layers = []                                                  # (độ cao nền, danh sách toà nhà) xa -> gần
        for base, lo, hi in ((0.66, 0.04, 0.12), (0.74, 0.06, 0.2)):
            x, row = 0.0, []
            while x < 1.0:
                bw = rng.uniform(0.03, 0.07)
                row.append((x, bw, rng.uniform(lo, hi)))
                x += bw + rng.uniform(0, 0.006)
            self.layers.append((base, row))

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#050816"), (0.55, "#161a3a"), (0.8, "#3a2a50"), (1, "#5a3a58")])
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 110))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        for k, (base, row) in enumerate(self.layers):                     # hai lớp nhà, lớp gần sáng đèn hơn
            for x, bw, bh in row:
                r = QRectF(x * w, h * (base - bh), bw * w, h * (1 - base + bh))
                p.setBrush(col("#0a0d1e" if k == 0 else "#060814"))
                p.drawRect(r)
                for _ in range(int(bw * 70) if k else int(bw * 30)):
                    p.setBrush(col(rng.choice(("#ffd98a", "#ffe9b0", "#cfe6ff")), 100 + 90 * k))
                    p.drawRect(QRectF(r.left() + rng.uniform(2, max(3.0, r.width() - 4)),
                                      r.top() + rng.uniform(3, h * (bh + 0.12)), 2, 2.5))
        vgrad(p, w, h, [(0, "#0b0d17"), (1, "#05060c")], 0.88, 1.0)       # mặt sân thượng
        p.fillRect(QRectF(0, h * 0.88, w, 4), col("#2a3040"))
        strokes(p, "#1a1f2e", 3)                                          # lan can
        p.drawLine(QPointF(0, h * 0.8), QPointF(w, h * 0.8))
        p.drawLine(QPointF(0, h * 0.84), QPointF(w, h * 0.84))
        x = 0.0
        while x < w:
            p.drawLine(QPointF(x, h * 0.8), QPointF(x, h * 0.88))
            x += 34
        ax = w * _ANTENNA                                                  # ăng-ten
        strokes(p, "#05060c", 4)
        p.drawLine(QPointF(ax, h * 0.88), QPointF(ax, h * 0.14))
        for yy, half in ((0.3, 0.04), (0.42, 0.03)):
            p.drawLine(QPointF(ax - w * half, h * yy), QPointF(ax + w * half, h * yy))
        p.setPen(pen("#1a1f2e", 2))                                       # bồn nước
        p.setBrush(col("#080a14"))
        p.drawRect(QRectF(w * 0.78, h * 0.6, w * 0.1, h * 0.2))
        poly(p, [(w * 0.77, h * 0.6), (w * 0.83, h * 0.55), (w * 0.89, h * 0.6)], "#080a14", "#1a1f2e")
        p.drawLine(QPointF(w * 0.79, h * 0.8), QPointF(w * 0.78, h * 0.88))
        p.drawLine(QPointF(w * 0.87, h * 0.8), QPointF(w * 0.88, h * 0.88))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        for x, y, sz, sp in self.clouds:                                  # mây gió thổi nhanh
            egl(p, ((x + t * sp) % 1.4 - 0.2) * w, y * h, w * sz, h * 0.04, "#8a7aa8", 40)
        hx = ((t * 0.035) % 1.4 - 0.2) * w                                # trực thăng + đèn pha
        hy = h * (0.2 + 0.015 * math.sin(t * 1.3))
        gk = self.good_k(t, 1.6)                                          # phá đúng: đèn pha quét về phía thẻ
        ang = math.pi / 2 + 0.35 * math.sin(t * 1.1)
        ang += (math.atan2(h * 0.5 - hy, w * 0.5 - hx) - ang) * gk
        beam(p, hx, hy, ang, 0.07 + 0.05 * gk, h * 0.75, "#fff6d8", 90 + 110 * gk)
        p.setPen(NO_PEN)
        p.setBrush(col("#04060c"))
        p.drawEllipse(QPointF(hx, hy), 14, 6)
        strokes(p, "#04060c", 2)
        p.drawLine(QPointF(hx - 20, hy - 7), QPointF(hx + 20, hy - 7))
        if (t % 1.0) < 0.2:
            glow(p, hx, hy + 6, 12, "#ff3b4e", 230)
        blink = (t % 1.6) < 0.25                                          # đèn cảnh báo đỏ trên ăng-ten
        ax, ay = w * _ANTENNA, h * 0.14
        glow(p, ax, ay, 22 if blink else 8, "#ff3b4e", 230 if blink else 60)
        p.setPen(NO_PEN)
        p.setBrush(col("#ff3b4e" if blink else "#5a1a22"))
        p.drawEllipse(QPointF(ax, ay), 3.5, 3.5)
