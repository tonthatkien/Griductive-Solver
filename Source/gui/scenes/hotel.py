"""Khách sạn trung tâm: mặt tiền cao tầng, cửa sổ bật/tắt đèn, biển neon HOTEL, xe chạy ngang đường."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui import theme
from gui.draw_utils import ALIGN_CENTER, draw_neon_text, make_font
from gui.icons import NO_PEN, pen
from gui.scenes.base import Scene, col, glow, poly, vgrad

_COLS, _ROWS = 7, 13


class HotelScene(Scene):
    name = "hotel"
    seed = 71

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.stars = [(rng.random(), rng.random() * 0.5) for _ in range(70)]
        self.sides = [(rng.uniform(0.0, 0.26), rng.uniform(0.3, 0.6), rng.uniform(0.07, 0.12)) for _ in range(4)] + \
                     [(rng.uniform(0.72, 0.9), rng.uniform(0.35, 0.65), rng.uniform(0.07, 0.12)) for _ in range(4)]

    @staticmethod
    def _tower(w: float, h: float) -> QRectF:
        return QRectF(w * 0.30, h * 0.14, w * 0.40, h * 0.72)

    def _win(self, w: float, h: float, i: int, j: int) -> QRectF:
        r = self._tower(w, h)
        cw, ch = r.width() / _COLS, (r.height() - h * 0.06) / _ROWS
        return QRectF(r.left() + i * cw + cw * 0.22, r.top() + h * 0.03 + j * ch + ch * 0.2, cw * 0.56, ch * 0.6)

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#060a1a"), (0.7, "#14213f"), (1, "#24305a")])
        p.setPen(NO_PEN)
        for x, y in self.stars:
            p.setBrush(col("#ffffff", 110))
            p.drawEllipse(QPointF(x * w, y * h), 1.1, 1.1)
        for x, top, bw in self.sides:                                  # toà nhà hai bên
            p.setBrush(col("#080d1a"))
            p.drawRect(QRectF(x * w, top * h, bw * w, h))
        r = self._tower(w, h)
        p.setPen(pen("#1c2a4a", 2))
        p.setBrush(col("#0a1020"))
        p.drawRect(r)
        p.setPen(NO_PEN)
        for i in range(_COLS):
            for j in range(_ROWS):
                p.setBrush(col("#121a2e"))
                p.drawRect(self._win(w, h, i, j))
        p.setBrush(col("#1b1410"))                                     # mái đón sảnh
        poly(p, [(w * 0.40, h * 0.86), (w * 0.60, h * 0.86), (w * 0.63, h * 0.9), (w * 0.37, h * 0.9)],
             "#2a1d14", "#c9a24b")
        p.fillRect(QRectF(0, h * 0.92, w, h * 0.08), col("#06080f"))   # mặt đường
        p.fillRect(QRectF(0, h * 0.92, w, 2), col("#2a3550"))

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        step = int(t / 5.0)                                            # mỗi 5 giây một số cửa sổ đổi trạng thái
        p.setPen(NO_PEN)
        for i in range(_COLS):
            for j in range(_ROWS):
                seed = ((i * 73856093) ^ (j * 19349663) ^ ((step + (i + j) % 3) * 83492791)) % 100
                if seed < 38:
                    warm = seed % 3 != 0
                    p.setBrush(col("#ffd98a" if warm else "#cfe6ff", 170))
                    p.drawRect(self._win(w, h, i, j))
        r = self._tower(w, h)
        sign = QRectF(r.left() + r.width() * 0.2, r.top() - h * 0.075, r.width() * 0.6, h * 0.06)
        pulse = 0.75 + 0.25 * math.sin(t * 2.4)
        glow(p, sign.center().x(), sign.center().y(), sign.width() * 0.8, "#ff4f9a", 55 * pulse)
        draw_neon_text(p, sign, "H O T E L", make_font(theme.FONT_GADGET, max(14, int(sign.height() * 0.8)), True,
                                                       spacing=4), "#ffd0e6", "#ff4f9a", pulse, ALIGN_CENTER)
        for x in (0.40, 0.5, 0.60):                                    # đèn dưới mái đón
            glow(p, w * x, h * 0.895, 26, "#ffd98a", 110 + 30 * math.sin(t * 2 + x * 9))
        for k, (speed, y, c) in enumerate(((0.11, 0.95, "#fff4cf"), (-0.08, 0.975, "#ff6b6b"))):   # xe chạy qua
            x = ((t * speed + k * 0.5) % 1.4 - 0.2) * w
            if speed < 0:
                x = w - x
            glow(p, x, h * y, 34, c, 150)
            p.setPen(NO_PEN)
            p.setBrush(col(c, 230))
            p.drawEllipse(QPointF(x, h * y), 3.5, 3.5)
            p.setBrush(col(c, 60))
            p.drawRect(QRectF(x - (70 if speed > 0 else -4), h * y - 1.5, 74, 3))
