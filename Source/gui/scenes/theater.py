"""Nhà hát thành phố: rèm nhung đỏ, sân khấu gỗ, dải bóng đèn chạy trên vòm, đèn rọi quét, bụi trong chùm sáng."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, beam, col, dust, egl, glow, make_motes, vgrad

_BULBS = 28


class TheaterScene(Scene):
    name = "theater"
    seed = 111

    def setup(self) -> None:
        self.motes = make_motes(random.Random(self.seed), 50)

    def _curtain(self, p: QPainter, x0: float, x1: float, h: float, base: str, light: str) -> None:
        stripes = 9
        sw = (x1 - x0) / stripes
        for i in range(stripes):
            c = light if i % 2 == 0 else base
            p.setPen(NO_PEN)
            p.setBrush(col(c))
            p.drawRect(QRectF(x0 + i * sw, 0, sw + 1, h * 0.84))
            p.setBrush(col("#000000", 40))                             # nếp gấp tối ở mép mỗi sọc
            p.drawRect(QRectF(x0 + i * sw, 0, sw * 0.25, h * 0.84))

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#0a0306"), (1, "#1a070c")])
        for i in range(14):                                              # rèm hậu cảnh
            p.fillRect(QRectF(w * (0.28 + i * 0.3 / 14), h * 0.12, w * 0.3 / 14 + 1, h * 0.7),
                       col("#2a0a12" if i % 2 else "#350d17"))
        vgrad(p, w, h, [(0, "#3a2414"), (1, "#0c0704")], 0.8, 1.0)        # sàn sân khấu
        p.setPen(pen(col("#5a3a22", 120), 1))
        for i in range(-8, 9):
            p.drawLine(QPointF(w * 0.5 + i * 10, h * 0.8), QPointF(w * 0.5 + i * w * 0.13, h))
        self._curtain(p, 0, w * 0.27, h, "#5a0c19", "#7e1424")           # rèm trái / phải
        self._curtain(p, w * 0.73, w, h, "#5a0c19", "#7e1424")
        for x0, x1 in ((0, w * 0.27), (w * 0.73, w)):                     # dây buộc rèm
            p.setPen(pen("#c9a24b", 5))
            p.drawLine(QPointF(x0, h * 0.62), QPointF(x1, h * 0.58))
        p.setPen(NO_PEN)                                                  # diềm rèm + viền vàng
        p.setBrush(col("#6e0f1e"))
        p.drawRect(QRectF(0, 0, w, h * 0.11))
        p.setBrush(col("#7e1424"))
        n = 14
        for i in range(n):
            p.drawEllipse(QPointF(w * (i + 0.5) / n, h * 0.11), w / n / 2, h * 0.035)
        p.setBrush(col("#c9a24b"))
        p.drawRect(QRectF(0, h * 0.085, w, 3))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        head = int(t * 7)
        p.setPen(NO_PEN)
        for i in range(_BULBS):                                           # dải bóng đèn chạy
            on = (i - head) % 4 == 0
            x, y = w * (i + 0.5) / _BULBS, h * 0.095
            if on:
                glow(p, x, y, 16, "#ffd98a", 190)
            p.setBrush(col("#fff1c8" if on else "#4a3a22"))
            p.drawEllipse(QPointF(x, y), 3, 3)
        for k, ox in enumerate((0.38, 0.62)):                             # hai đèn rọi quét ngược chiều nhau
            ang = math.pi / 2 + (0.28 if k == 0 else -0.28) * math.sin(t * 0.7 + k * 2.2)
            beam(p, w * ox, h * 0.12, ang, 0.1, h * 0.8, "#fff1c8", 80)
            tx = w * ox + math.tan(ang - math.pi / 2) * h * 0.68
            egl(p, tx, h * 0.82, w * 0.07, h * 0.02, "#fff1c8", 110)
        dust(p, w, h, t, self.motes, "#fff1c8", 120, 0.008)
