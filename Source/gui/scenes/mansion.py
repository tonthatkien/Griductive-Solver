"""Biệt thự bỏ hoang: bầu trời bão tím, trăng sau mây, nhà ma, cây trơ cành, sương, sét, dơi, cửa sổ chập chờn."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, col, egl, fog, glow, lightning, poly, vgrad

_WINDOWS = ((0.41, 0.58), (0.50, 0.58), (0.58, 0.58), (0.45, 0.70), (0.55, 0.70), (0.325, 0.50))


class MansionScene(Scene):
    name = "mansion"
    seed = 31
    accent = "#cfd8ff"

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.45) for _ in range(60)]
        self.clouds = [(rng.random(), rng.uniform(0.08, 0.3), rng.uniform(0.18, 0.34), rng.uniform(0.006, 0.014))
                       for _ in range(5)]
        self.bats = [(rng.random(), rng.uniform(0.1, 0.4), rng.uniform(0.04, 0.07), rng.uniform(0.7, 1.4))
                     for _ in range(4)]

    def _branch(self, p: QPainter, rng: random.Random, x: float, y: float, ang: float, ln: float,
                depth: int) -> None:
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        p.setPen(pen("#05030a", max(1.0, depth * 1.6)))
        p.drawLine(QPointF(x, y), QPointF(x2, y2))
        if depth > 0:
            for da in (-0.55, 0.5):
                self._branch(p, rng, x2, y2, ang + da + rng.uniform(-0.2, 0.2), ln * rng.uniform(0.62, 0.78),
                             depth - 1)

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#0a0614"), (0.55, "#25132f"), (0.8, "#3b1f3b"), (1, "#1a0e1f")])
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 120))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        mx, my, mr = w * 0.8, h * 0.2, min(w, h) * 0.045
        glow(p, mx, my, mr * 6.5, "#d9c8ff", 70)
        p.setBrush(col("#efe6ff"))
        p.drawEllipse(QPointF(mx, my), mr, mr)
        p.fillRect(QRectF(0, h * 0.84, w, h * 0.16), col("#07040b"))
        body = "#060309"                                      # nhà chính, tháp, mái, ống khói
        p.setBrush(col(body))
        p.drawRect(QRectF(w * 0.38, h * 0.5, w * 0.26, h * 0.34))
        poly(p, [(w * 0.36, h * 0.5), (w * 0.51, h * 0.34), (w * 0.66, h * 0.5)], body)
        p.drawRect(QRectF(w * 0.30, h * 0.4, w * 0.07, h * 0.44))
        poly(p, [(w * 0.29, h * 0.4), (w * 0.335, h * 0.27), (w * 0.38, h * 0.4)], body)
        p.drawRect(QRectF(w * 0.58, h * 0.3, w * 0.02, h * 0.1))
        for x, y in _WINDOWS:
            p.setBrush(col("#12091a"))
            p.drawRect(QRectF(w * x, h * y, w * 0.025, h * 0.06))
        p.setPen(pen("#05030a", 2))                           # hàng rào
        x = 0.03
        while x < 0.97:
            p.drawLine(QPointF(w * x, h * 0.9), QPointF(w * x, h * 0.84))
            x += 0.022
        p.drawLine(QPointF(0, h * 0.875), QPointF(w, h * 0.875))
        for x, s in ((0.10, 1.0), (0.90, 0.85), (0.19, 0.6), (0.82, 0.55)):    # cây trơ cành
            self._branch(p, rng, w * x, h * 0.88, -math.pi / 2 + rng.uniform(-0.1, 0.1), h * 0.2 * s, 5)

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        for x, y, sz, sp in self.clouds:                      # mây trôi qua trăng
            egl(p, ((x + t * sp) % 1.3 - 0.15) * w, y * h, w * sz, h * 0.05, "#0d0716", 150)
        for i in (0, 3, 5):                                   # ánh nến chập chờn trong cửa sổ
            x, y = _WINDOWS[i]
            a = 150 + 90 * math.sin(t * 9 + i * 2.1) * math.sin(t * 3.3 + i)
            p.setPen(NO_PEN)
            p.setBrush(col("#ffb347", a))
            p.drawRect(QRectF(w * x, h * y, w * 0.025, h * 0.06))
            glow(p, w * x + w * 0.0125, h * y + h * 0.03, w * 0.05, "#ff9b2f", a * 0.35)
        for x, y, s, sp in self.bats:                         # dơi
            bx = ((x + t * 0.05 * sp) % 1.2 - 0.1) * w
            by = (y + 0.03 * math.sin(t * 1.7 * sp + x * 9)) * h
            sz, flap = s * w * 0.5, math.sin(t * 14 * sp + x * 20)
            poly(p, [(bx, by), (bx - sz, by - sz * 0.5 * flap), (bx - sz * 0.55, by + sz * 0.25)], "#05030a")
            poly(p, [(bx, by), (bx + sz, by - sz * 0.5 * flap), (bx + sz * 0.55, by + sz * 0.25)], "#05030a")
        fog(p, w, h, t, "#8a7aa8", 5, 22, 0.82)
        lt, gk = lightning(t, 11.0), self.good_k(t, 0.7)      # phá đúng: một tia sét
        k = max(lt, gk)
        if k > 0:
            p.fillRect(QRectF(0, 0, w, h), col("#cfd8ff", 70 * k))
            if k > 0.35:                                      # tia sét ziczac
                rng = random.Random(int(self._good_at) if gk > lt else int(t // 11.0))
                x, y, pts = rng.uniform(0.1, 0.9) * w, 0.0, []
                for _ in range(7):
                    pts.append((x, y))
                    x += rng.uniform(-0.04, 0.04) * w
                    y += h * 0.085
                for width, alpha in ((7, 50), (2.4, 255)):
                    p.setPen(pen(col("#f4f0ff", alpha * k), width))
                    for a, b in zip(pts, pts[1:]):
                        p.drawLine(QPointF(*a), QPointF(*b))
