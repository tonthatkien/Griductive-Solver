"""Quán cà phê góc phố: cửa kính đêm mưa, bokeh phố xá, đèn thả vàng ấm, biển neon OPEN, hơi nước từ cốc."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter

from gui import theme
from gui.draw_utils import ALIGN_CENTER, draw_neon_text, make_font
from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.scenes.base import Scene, col, glow, make_drops, poly, rain, vgrad


class CafeScene(Scene):
    name = "cafe"
    seed = 21
    accent = "#ff8fc0"

    def setup(self) -> None:
        rng = random.Random(self.seed)
        self.bokeh = [(rng.uniform(0.07, 0.93), rng.uniform(0.14, 0.66), rng.uniform(0.012, 0.04),
                       rng.choice(("#ffb454", "#ff6b81", "#5ad8ff", "#ffe08a"))) for _ in range(34)]
        self.drops = make_drops(rng, 80)
        self.runs = [(rng.uniform(0.1, 0.9), rng.random(), rng.uniform(0.05, 0.1)) for _ in range(14)]
        self.steam = [(i / 3.0, rng.uniform(0, 6.28)) for i in range(3)]

    @staticmethod
    def _win(w: float, h: float) -> QRectF:
        return QRectF(w * 0.08, h * 0.09, w * 0.84, h * 0.62)

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#150d0e"), (1, "#24170f")])
        win, u = self._win(w, h), min(w, h)
        p.save()
        p.setClipRect(win)
        vgrad(p, w, h, [(0, "#0a1630"), (0.7, "#142a52"), (1, "#1c2a44")], 0.09, 0.71)
        for x, y, r, c in self.bokeh:                       # đèn phố nhoè sau lớp kính
            glow(p, x * w, y * h, r * u * 2.4, c, 90)
            p.setPen(NO_PEN)
            p.setBrush(col(c, 70))
            p.drawEllipse(QPointF(x * w, y * h), r * u, r * u)
        p.restore()
        p.setBrush(NO_BRUSH)                                # khung cửa sổ gỗ
        p.setPen(pen("#3b2418", 12))
        p.drawRect(win)
        p.setPen(pen("#3b2418", 8))
        for k in (1 / 3, 2 / 3):
            x = win.left() + win.width() * k
            p.drawLine(QPointF(x, win.top()), QPointF(x, win.bottom()))
        y = win.top() + win.height() * 0.55
        p.drawLine(QPointF(win.left(), y), QPointF(win.right(), y))
        vgrad(p, w, h, [(0, "#2d1b10"), (1, "#100905")], 0.74, 1.0)   # mặt bàn (đè lên phần dưới)
        for x in (0.3, 0.7):                                # đèn thả
            p.setPen(pen("#050505", 2))
            p.drawLine(QPointF(w * x, 0), QPointF(w * x, h * 0.15))
            poly(p, [(w * x - 28, h * 0.2), (w * x + 28, h * 0.2), (w * x + 12, h * 0.15),
                     (w * x - 12, h * 0.15)], "#1a1a1a", "#5a3a22")
        cx, cy = w * 0.22, h * 0.8                          # cốc cà phê
        p.setPen(pen("#6b4a30", 2))
        p.setBrush(col("#2a1a12"))
        p.drawRoundedRect(QRectF(cx - 26, cy - 30, 52, 36), 8, 8)
        p.setBrush(NO_BRUSH)
        p.setPen(pen("#6b4a30", 4))
        p.drawArc(QRectF(cx + 18, cy - 24, 24, 22), -90 * 16, 180 * 16)

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        for x in (0.3, 0.7):
            glow(p, w * x, h * 0.21, min(w, h) * 0.28, "#ffb454", 70 + 25 * math.sin(t * 1.3 + x * 9))
        win = self._win(w, h)
        p.save()
        p.setClipRect(win)
        rain(p, w, h, t, self.drops, "#a8d4ff", 70, 0.25)
        for x, ph, ln in self.runs:                         # giọt nước chảy trên kính
            y = win.top() + ((t * 0.04 + ph) % 1.0) * win.height()
            p.setPen(pen(col("#cfe8ff", 70), 1.6))
            p.drawLine(QPointF(w * x, y), QPointF(w * x, y + h * ln * 0.4))
            p.setPen(NO_PEN)
            p.setBrush(col("#e8f4ff", 110))
            p.drawEllipse(QPointF(w * x, y + h * ln * 0.4), 2.2, 3.0)
        p.restore()
        gk = self.good_k(t)                                  # phá đúng: neon bừng sáng
        on = 1.0 if gk > 0 else (0.35 if int(t * 6) % 13 == 0 else 1.0)   # biển neon chập chờn
        sign = QRectF(w * 0.74, h * 0.2, w * 0.14, h * 0.08)
        glow(p, sign.center().x(), sign.center().y(), sign.width() * (0.9 + 0.9 * gk), "#ff4f9a", 60 * on + 170 * gk)
        p.setBrush(NO_BRUSH)
        p.setPen(pen(col("#ff4f9a", 230 * on), 2.5))
        p.drawRoundedRect(sign, 8, 8)
        draw_neon_text(p, sign, "OPEN", make_font(theme.FONT_GADGET, max(12, int(sign.height() * 0.5)), True,
                                                  spacing=3), "#ffd0e6", "#ff4f9a", on, ALIGN_CENTER)
        cx, cy = w * 0.22, h * 0.8
        for off, ph in self.steam:                          # hơi nước bốc lên từ cốc
            u = (t * 0.2 + off) % 1.0
            glow(p, cx + 10 * math.sin(u * 6 + ph), cy - 36 - u * h * 0.2, 14 + u * 26, "#ffffff",
                 55 * math.sin(u * math.pi))
