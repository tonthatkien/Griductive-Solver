"""Thư viện cổ: giá sách cao hai bên, cửa sổ vòm ánh trăng, tia sáng đầy bụi, đèn bàn xanh, trang giấy bay."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath

from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.scenes.base import Scene, col, dust, glow, make_motes, poly, vgrad

_BOOKS = ("#5a2a22", "#2f4a3a", "#2a3a5a", "#6a4a2a", "#4a2a4a", "#7a6a3a", "#3a2a22", "#5a1f2a")
_SHAFTS = ((0.42, 0.46), (0.54, 0.62))                                   # (x trên cửa sổ, x dưới sàn)


class LibraryScene(Scene):
    name = "library"
    seed = 91

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.motes = make_motes(rng, 60)
        self.pages = [(rng.uniform(0.3, 0.7), rng.uniform(0, 6.28), rng.uniform(0.6, 1.2)) for _ in range(4)]

    @staticmethod
    def _window(w: float, h: float) -> QRectF:
        return QRectF(w * 0.38, h * 0.12, w * 0.24, h * 0.5)

    def _shelves(self, p: QPainter, rng: random.Random, x0: float, x1: float, h: float) -> None:
        p.fillRect(QRectF(x0, 0, x1 - x0, h * 0.82), col("#150d08"))
        rows = 7
        for r in range(rows):
            top, bottom = h * 0.82 * r / rows, h * 0.82 * (r + 1) / rows
            x = x0 + 4
            while x < x1 - 8:
                bw, bh = rng.uniform(6, 13), (bottom - top) * rng.uniform(0.62, 0.92)
                p.setPen(NO_PEN)
                p.setBrush(col(rng.choice(_BOOKS), 230))
                p.drawRect(QRectF(x, bottom - 5 - bh, bw, bh))
                p.setBrush(col("#c9a24b", 90))
                p.drawRect(QRectF(x, bottom - 5 - bh * 0.7, bw, 2))
                x += bw + 0.6
            p.fillRect(QRectF(x0, bottom - 5, x1 - x0, 5), col("#3a2616"))

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        rng = self.fresh_rng()
        vgrad(p, w, h, [(0, "#0e0905"), (1, "#1a110a")])
        self._shelves(p, rng, 0, w * 0.24, h)
        self._shelves(p, rng, w * 0.76, w, h)
        win = self._window(w, h)                                         # cửa sổ vòm
        arch = QPainterPath()
        arch.moveTo(win.left(), win.bottom())
        arch.lineTo(win.left(), win.top() + win.width() / 2)
        arch.arcTo(QRectF(win.left(), win.top(), win.width(), win.width()), 180, -180)
        arch.lineTo(win.right(), win.bottom())
        arch.closeSubpath()
        g_top = win.top()
        p.save()
        p.setClipPath(arch)
        vgrad(p, w, h, [(0, "#0a1630"), (1, "#26406e")], g_top / h, win.bottom() / h)
        glow(p, win.center().x(), win.top() + win.height() * 0.3, win.width() * 0.5, "#dfe9ff", 120)
        p.restore()
        strokes_color = col("#3a2616")
        p.setBrush(NO_BRUSH)
        p.setPen(pen(strokes_color, 10))
        p.drawPath(arch)
        p.setPen(pen(strokes_color, 6))
        p.drawLine(QPointF(win.center().x(), win.top()), QPointF(win.center().x(), win.bottom()))
        p.drawLine(QPointF(win.left(), win.top() + win.height() * 0.5), QPointF(win.right(), win.top() + win.height() * 0.5))
        vgrad(p, w, h, [(0, "#2a1a0e"), (1, "#0c0704")], 0.82, 1.0)       # sàn gỗ
        p.setPen(pen("#05030a", 2))                                       # bàn đọc sách
        p.setBrush(col("#1d120a"))
        p.drawRect(QRectF(w * 0.38, h * 0.76, w * 0.24, h * 0.04))
        p.drawRect(QRectF(w * 0.40, h * 0.8, w * 0.02, h * 0.1))
        p.drawRect(QRectF(w * 0.58, h * 0.8, w * 0.02, h * 0.1))
        poly(p, [(w * 0.52, h * 0.76), (w * 0.56, h * 0.76), (w * 0.55, h * 0.70), (w * 0.50, h * 0.70)], "#1f5a3a", "#0a2a1a")

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        win = self._window(w, h)
        for i, (tx, bx) in enumerate(_SHAFTS):                           # tia sáng trăng xiên xuống
            breath = 0.6 + 0.4 * math.sin(t * 0.6 + i * 2.0)
            poly(p, [(w * tx, win.top() + win.height() * 0.2), (w * (tx + 0.05), win.top() + win.height() * 0.2),
                     (w * (bx + 0.12), h * 0.88), (w * (bx - 0.1), h * 0.88)], col("#cfe0ff", 20 * breath))
        dust(p, w, h, t, self.motes, "#dfe9ff", 150, 0.01)
        flick = 0.85 + 0.15 * math.sin(t * 7.0) * math.sin(t * 2.3)       # đèn bàn
        glow(p, w * 0.525, h * 0.72, w * 0.1, "#ffe08a", 110 * flick)
        for x, ph, sp in self.pages:                                      # trang giấy lơ lửng
            px = (x + 0.05 * math.sin(t * 0.5 * sp + ph)) * w
            py = (0.32 + 0.12 * math.sin(t * 0.7 * sp + ph * 2.0)) * h + 0.02 * h * ((t * sp) % 2.0)
            p.save()
            p.translate(px, py)
            p.rotate(25 * math.sin(t * 0.9 * sp + ph))
            p.setPen(NO_PEN)
            p.setBrush(col("#efe2b6", 150))
            p.drawRect(QRectF(-8, -10, 16, 20))
            p.restore()
