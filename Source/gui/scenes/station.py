"""Ga tàu điện: đường hầm nhìn xuyên sâu, đèn trần chập chờn, đèn pha tàu lao tới định kỳ, đèn tín hiệu."""
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.scenes.base import Scene, col, glow, poly, vgrad

_RINGS = 12


class StationScene(Scene):
    name = "station"
    seed = 51

    @staticmethod
    def _vp(w: float, h: float):
        return w * 0.5, h * 0.46

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vx, vy = self._vp(w, h)
        vgrad(p, w, h, [(0, "#05080e"), (1, "#0b121b")])
        poly(p, [(0, 0), (vx, vy), (0, h)], "#0b1219")           # tường trái / phải, trần, sàn
        poly(p, [(w, 0), (vx, vy), (w, h)], "#0b1219")
        poly(p, [(0, 0), (w, 0), (vx, vy)], "#070b12")
        poly(p, [(0, h), (w, h), (vx, vy)], "#10161e")
        p.setBrush(NO_BRUSH)
        for i in range(_RINGS):                                   # sườn hầm thu nhỏ dần về điểm tụ
            s = 0.8 ** i
            p.setPen(pen(col("#2b3a4e", 150 * s + 40), 2.4 * s + 0.6))
            p.drawRect(QRectF(vx - w * 0.5 * s, vy - h * 0.46 * s, w * s, h * 0.92 * s))
        p.setPen(pen("#5b6a7a", 3))                               # ray + tà vẹt
        for dx in (-0.14, 0.14):
            p.drawLine(QPointF(vx, vy), QPointF(vx + w * dx * 3.2, h))
        p.setPen(pen(col("#3a2f22", 170), 3))
        for i in range(1, 16):
            s = 0.78 ** i
            y = vy + (h - vy) * s * 1.0
            p.drawLine(QPointF(vx - w * 0.5 * s * 0.5, y), QPointF(vx + w * 0.5 * s * 0.5, y))
        p.setPen(pen(col("#ffd23c", 200), 4))                     # vạch vàng mép sân ga
        p.drawLine(QPointF(vx - w * 0.04, vy + h * 0.03), QPointF(w * 0.06, h))
        p.drawLine(QPointF(vx + w * 0.04, vy + h * 0.03), QPointF(w * 0.94, h))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        vx, vy = self._vp(w, h)
        for i in range(1, _RINGS, 2):                             # đèn trần, vài bóng chập chờn
            s = 0.8 ** i
            flick = 0.35 if (int(t * 8) + i) % 11 == 0 else 1.0
            glow(p, vx, vy - h * 0.46 * s * 0.9, 18 + 120 * s, "#cfe6ff", 85 * flick * (0.5 + 0.5 * s))
        k = (t % 11.0) / 11.0                                     # tàu lao tới: đèn pha lớn dần từ điểm tụ
        if k < 0.55:
            u = k / 0.55
            glow(p, vx, vy + h * 0.02, 8 + w * 0.55 * u ** 3, "#fff6d8", 40 + 190 * u ** 2)
            p.fillRect(QRectF(0, 0, w, h), col("#fff6d8", 25 * u ** 4))
        on = int(t * 1.2) % 2 == 0                                # đèn tín hiệu
        glow(p, vx + w * 0.06, vy - h * 0.05, 16, "#ff3b4e" if on else "#39ff14", 200)
        p.setPen(NO_PEN)
        p.setBrush(col("#ff3b4e" if on else "#39ff14"))
        p.drawEllipse(QPointF(vx + w * 0.06, vy - h * 0.05), 3.5, 3.5)
