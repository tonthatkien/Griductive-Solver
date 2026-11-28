"""Phòng thí nghiệm: tường lưới xanh, kệ bình thí nghiệm sủi bọt, radar quét, màn hình điện tâm đồ."""
import math
import random

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPolygonF

from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.scenes.base import Scene, col, glow, make_motes, dust, strokes, vgrad

# (x, y kệ, màu, mức chất lỏng 0..1)
_FLASKS = ((0.07, 0.40, "#39ff14", 0.6), (0.14, 0.40, "#38f2ff", 0.45), (0.21, 0.40, "#ff4fd8", 0.7),
           (0.28, 0.40, "#ffd23c", 0.5), (0.72, 0.40, "#38f2ff", 0.65), (0.79, 0.40, "#39ff14", 0.4),
           (0.86, 0.40, "#ff4fd8", 0.55), (0.93, 0.40, "#ffd23c", 0.7),
           (0.07, 0.68, "#38f2ff", 0.5), (0.17, 0.68, "#39ff14", 0.65), (0.27, 0.68, "#ff4fd8", 0.4),
           (0.73, 0.68, "#ffd23c", 0.6), (0.83, 0.68, "#38f2ff", 0.5), (0.93, 0.68, "#39ff14", 0.7))
_BLIPS = ((0.55, 1.1), (0.8, 3.4), (0.35, 5.0))


class LabScene(Scene):
    name = "lab"
    seed = 41

    def setup(self) -> None:
        self.motes = make_motes(random.Random(self.seed), 26)

    @staticmethod
    def _flask(w: float, h: float, x: float, sy: float):
        fw, fh = w * 0.026, h * 0.1
        cx, base = x * w, sy * h
        return [(cx - fw * 0.28, base - fh), (cx + fw * 0.28, base - fh), (cx + fw * 0.28, base - fh * 0.62),
                (cx + fw, base), (cx - fw, base), (cx - fw * 0.28, base - fh * 0.62)], cx, base, fw, fh

    @staticmethod
    def _radar(w: float, h: float):
        return w * 0.5, h * 0.46, min(w, h) * 0.24

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#05131a"), (1, "#0a2229")])
        p.setPen(pen(col("#38f2ff", 16), 1))
        for i in range(int(w // 48) + 1):
            p.drawLine(QPointF(i * 48, 0), QPointF(i * 48, h))
        for j in range(int(h // 48) + 1):
            p.drawLine(QPointF(0, j * 48), QPointF(w, j * 48))
        p.setPen(pen("#1b3b46", 5))                              # ván kệ
        for sy in (0.40, 0.68):
            p.drawLine(QPointF(w * 0.03, h * sy + 3), QPointF(w * 0.33, h * sy + 3))
            p.drawLine(QPointF(w * 0.67, h * sy + 3), QPointF(w * 0.97, h * sy + 3))
        for x, sy, c, lv in _FLASKS:                             # viền bình
            pts, *_ = self._flask(w, h, x, sy)
            p.setBrush(col("#0a1c24"))
            p.setPen(pen(col("#8fe9ff", 150), 1.4))
            p.drawPolygon(QPolygonF([QPointF(a, b) for a, b in pts]))
        cx, cy, r = self._radar(w, h)                            # khung radar
        strokes(p, col("#38f2ff", 80), 1.5)
        for k in (1.0, 0.7, 0.4):
            p.drawEllipse(QPointF(cx, cy), r * k, r * k)
        p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
        p.setPen(pen("#1b3b46", 3))                              # khung màn hình ECG
        p.setBrush(col("#04100f", 220))
        p.drawRoundedRect(QRectF(w * 0.34, h * 0.8, w * 0.32, h * 0.12), 8, 8)

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        for i, (x, sy, c, lv) in enumerate(_FLASKS):             # chất lỏng + bọt khí
            pts, cx, base, fw, fh = self._flask(w, h, x, sy)
            path = QPainterPath()
            path.addPolygon(QPolygonF([QPointF(a, b) for a, b in pts]))
            path.closeSubpath()
            level = fh * 0.62 * lv + 2 * math.sin(t * 1.5 + i)
            p.save()
            p.setClipPath(path)
            p.fillRect(QRectF(cx - fw, base - level, fw * 2, level), col(c, 120 + 40 * math.sin(t * 2 + i)))
            p.setPen(NO_PEN)
            for b in range(3):
                u = (t * 0.45 + b / 3.0 + i * 0.13) % 1.0
                p.setBrush(col("#ffffff", 150 * (1 - u)))
                p.drawEllipse(QPointF(cx + fw * 0.4 * math.sin(u * 9 + b), base - u * level), 2.0, 2.0)
            p.restore()
            glow(p, cx, base - level * 0.5, fw * 2.2, c, 30 + 12 * math.sin(t * 2 + i))
        cx, cy, r = self._radar(w, h)                            # radar quét
        a = t * 1.1
        sweep = [(cx, cy)] + [(cx + math.cos(a - 0.55 * k / 8) * r, cy + math.sin(a - 0.55 * k / 8) * r)
                              for k in range(9)]
        p.setPen(NO_PEN)
        p.setBrush(col("#39ff14", 46))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in sweep]))
        strokes(p, col("#7dff6a", 200), 2)
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * r, cy + math.sin(a) * r))
        for rr, ang in _BLIPS:                                   # chấm mục tiêu sáng khi tia quét qua
            lag = (a - ang) % (2 * math.pi)
            alpha = 230 * max(0.0, 1 - lag / 3.0)
            p.setPen(NO_PEN)
            p.setBrush(col("#caffb8", alpha))
            p.drawEllipse(QPointF(cx + math.cos(ang) * r * rr, cy + math.sin(ang) * r * rr), 4, 4)
        mon = QRectF(w * 0.35, h * 0.81, w * 0.30, h * 0.10)     # điện tâm đồ
        path, n = QPainterPath(), 90
        for i in range(n + 1):
            ph = ((i / n) * 2.4 - t * 0.5) % 1.0
            v = (-0.35 if 0.40 < ph < 0.43 else 1.0 - abs(ph - 0.45) / 0.02 if 0.43 <= ph < 0.47
                 else -0.5 if 0.47 <= ph < 0.5 else 0.0)
            pt = QPointF(mon.left() + mon.width() * i / n, mon.center().y() - v * mon.height() * 0.4)
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        p.setBrush(NO_BRUSH)
        p.setPen(pen(col("#39ff14", 220), 2))
        p.drawPath(path)
        for k, c in enumerate(("#ff3b4e", "#ffd23c", "#39ff14")):   # đèn LED
            p.setPen(NO_PEN)
            p.setBrush(col(c, 230 if int(t * 2 + k) % 3 == k else 60))
            p.drawEllipse(QPointF(w * 0.36 + k * 14, h * 0.775), 3.5, 3.5)
        dust(p, w, h, t, self.motes, "#8fe9ff", 90)
