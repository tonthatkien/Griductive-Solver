"""Bảo tàng nghệ thuật: hành lang tranh khung vàng, đèn rọi từ trần, tượng bán thân, tia laser báo động quét ngang."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, beam, col, dust, glow, make_motes, poly, strokes, vgrad

# (x, y, rộng, cao) theo phân số + hai màu của bức tranh
_FRAMES = ((0.08, 0.16, 0.14, 0.30, "#7a2b3a", "#1d2a55"), (0.27, 0.22, 0.10, 0.22, "#2b5a4a", "#c9a24b"),
           (0.42, 0.14, 0.16, 0.34, "#3b2a6a", "#e07a5f"), (0.64, 0.22, 0.10, 0.22, "#a0522d", "#1f3a5a"),
           (0.79, 0.16, 0.13, 0.30, "#1f4a6a", "#d9c27a"))


class MuseumScene(Scene):
    name = "museum"
    seed = 61

    def setup(self) -> None:
        self.motes = make_motes(random.Random(self.seed), 40)

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#0d0a0b"), (0.7, "#1b1412")])
        vgrad(p, w, h, [(0, "#201612"), (1, "#070504")], 0.72, 1.0)     # sàn gỗ bóng
        p.setPen(pen(col("#4a3526", 120), 1))
        for i in range(-6, 7):                                          # đường ván sàn toả về điểm tụ
            p.drawLine(QPointF(w * 0.5 + i * 12, h * 0.72), QPointF(w * 0.5 + i * w * 0.16, h))
        p.setPen(pen("#3a2a20", 4))
        p.drawLine(QPointF(0, h * 0.72), QPointF(w, h * 0.72))          # chân tường
        for x, y, fw, fh, c1, c2 in _FRAMES:
            r = QRectF(w * x, h * y, w * fw, h * fh)
            p.setPen(pen("#c9a24b", 5))
            p.setBrush(col("#0a0807"))
            p.drawRect(r.adjusted(-6, -6, 6, 6))
            p.setPen(NO_PEN)
            p.setBrush(col(c1, 190))
            p.drawRect(r)
            p.setBrush(col(c2, 170))                                     # nét trừu tượng bên trong tranh
            for _ in range(3):
                cx, cy = r.left() + rng.uniform(0.2, 0.8) * r.width(), r.top() + rng.uniform(0.2, 0.8) * r.height()
                p.drawEllipse(QPointF(cx, cy), r.width() * rng.uniform(0.1, 0.25), r.width() * rng.uniform(0.08, 0.2))
        px = w * 0.9                                                     # bệ + tượng bán thân
        p.setPen(pen("#6b5a48", 2))
        p.setBrush(col("#2a2420"))
        p.drawRect(QRectF(px - 26, h * 0.62, 52, h * 0.16))
        p.setBrush(col("#8a8070"))
        p.drawEllipse(QPointF(px, h * 0.55), 17, 21)
        poly(p, [(px - 30, h * 0.62), (px - 14, h * 0.58), (px + 14, h * 0.58), (px + 30, h * 0.62)], "#8a8070")

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        for i, (x, y, fw, fh, *_c) in enumerate(_FRAMES):               # đèn rọi từng tranh
            breath = 0.7 + 0.3 * math.sin(t * 0.9 + i * 1.7)
            beam(p, w * (x + fw / 2), 0, math.pi / 2, 0.16 + fw * 0.4, h * (y + fh + 0.08), "#fff1c8", 70 * breath)
            glow(p, w * (x + fw / 2), h * y, w * fw * 0.9, "#fff1c8", 30 * breath)
        for k in range(4):                                              # laser báo động: các tia ngang trượt lên xuống
            y = h * (0.80 + 0.07 * math.sin(t * 0.8 + k * 1.4)) + k * h * 0.035
            on = 0.55 + 0.45 * math.sin(t * 5 + k)
            strokes(p, col("#ff2b3d", 40 * on), 6)
            p.drawLine(QPointF(0, y), QPointF(w, y))
            strokes(p, col("#ff5a66", 200 * on), 1.4)
            p.drawLine(QPointF(0, y), QPointF(w, y))
        p.setPen(NO_PEN)
        p.setBrush(col("#ff2b3d", 230))                                  # đầu phát laser bên trái
        for k in range(4):
            p.drawEllipse(QPointF(6, h * (0.80 + 0.07 * math.sin(t * 0.8 + k * 1.4)) + k * h * 0.035), 4, 4)
        dust(p, w, h, t, self.motes, "#fff1c8", 120)
