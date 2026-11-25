"""Mixin vẽ mặt úp của thẻ: bìa hồ sơ mật, dấu ? neon, niêm phong sáp. (Scope F)
"""
import math
from typing import Dict

from PySide6.QtCore import (QPointF, QRectF, Qt)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPixmap, QPolygonF)

from gui import icons, theme
from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.anim import clock
from gui.draw_utils import (A, ALIGN_CENTER, ALIGN_LEFT_MID, draw_fitted, flags, make_font)


class CardBackMixin:
    """Các hàm vẽ mặt úp; dùng thuộc tính của CardView (self._hover, self._phase, ...)."""

    def _paint_back(self, p: QPainter, r: QRectF, u: float, seal_progress: float) -> None:
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0, QColor("#1f3057"))
        grad.setColorAt(1, QColor("#090f1f"))
        p.fillPath(path, QBrush(grad))
        p.save()
        p.setClipPath(path)
        apex = QPointF(r.left() + 4, r.top() + 2)
        cone = QPolygonF([apex, QPointF(r.left() + r.width() * 0.1, r.bottom()),
                          QPointF(r.right(), r.bottom() - r.height() * 0.25)])
        light = QLinearGradient(apex, r.center())
        light.setColorAt(0, QColor(255, 255, 230, int(80 + 80 * self._hover.now)))
        light.setColorAt(1, QColor(255, 255, 230, 0))
        p.setPen(NO_PEN)
        p.setBrush(QBrush(light))
        p.drawPolygon(cone)
        cx, head_y = r.center().x(), r.top() + r.height() * 0.38
        p.setBrush(QColor("#04060d"))
        p.drawEllipse(QPointF(cx, head_y), u * 0.17, u * 0.2)
        p.drawEllipse(QPointF(cx, head_y + u * 0.42), u * 0.38, u * 0.26)
        self._neon_question(p, QPointF(cx, head_y), u)
        strip = QRectF(r.left(), r.top(), r.width(), u * 0.17)
        p.setBrush(QColor(255, 255, 255, 22))
        p.drawRect(strip)
        p.setPen(QColor(theme.CYAN_LASER))
        p.setFont(make_font(theme.FONT_GADGET, u * 0.085, True, spacing=1.5))
        p.drawText(strip.adjusted(u * 0.07, 0, 0, 0), ALIGN_LEFT_MID, "HỒ SƠ MẬT")
        p.setPen(QColor(theme.GOLD))
        p.setFont(make_font(theme.FONT_MONO, u * 0.125, True))
        p.drawText(strip.adjusted(0, 0, -u * 0.07, 0), flags(A.AlignRight, A.AlignVCenter), self.cell)
        plate = QRectF(r.left(), r.bottom() - u * 0.32, r.width(), u * 0.32)
        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 0, 0, 150))
        p.drawRect(plate)
        draw_fitted(p, QRectF(plate.left() + u * 0.05, plate.top() + u * 0.02, plate.width() - u * 0.1,
                              u * 0.18), self.name, theme.FONT_TITLE, int(u * 0.16), 10, theme.GOLD_SOFT,
                    bold=True, fl=ALIGN_CENTER)
        draw_fitted(p, QRectF(plate.left() + u * 0.05, plate.top() + u * 0.2, plate.width() - u * 0.1,
                              u * 0.11), self.profession, theme.FONT_DOSSIER, int(u * 0.11), 9, "#b9c6e6",
                    italic=True, fl=ALIGN_CENTER)
        p.restore()
        self._wax_seal(p, QPointF(cx, r.top() + r.height() * 0.66), u * 0.075, seal_progress)
        p.setBrush(NO_BRUSH)
        p.setPen(pen("#3d5486", 2))
        p.drawPath(path)

    _GLOW_CACHE: Dict[int, tuple] = {}

    def _neon_question(self, p: QPainter, center: QPointF, u: float) -> None:
        """Dấu ? neon đỏ phập phồng (phóng nhẹ, lắc nhẹ, sáng tối theo nhịp ~1.8 s)."""
        px, dpr = int(u * 0.38), self.devicePixelRatioF()
        entry = CardBackMixin._GLOW_CACHE.get(px)
        if entry is None or entry[2] != dpr:
            path = QPainterPath()
            path.addText(0.0, 0.0, make_font(theme.FONT_GADGET, px, True), "?")
            box = path.boundingRect()
            path.translate(-box.center().x(), -box.center().y())
            margin = 22
            w, h = int(box.width() + 2 * margin), int(box.height() + 2 * margin)
            pix = QPixmap(int(w * dpr) + 1, int(h * dpr) + 1)
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.GlobalColor.transparent)
            g = QPainter(pix)
            g.setRenderHint(QPainter.RenderHint.Antialiasing)
            g.translate(w / 2, h / 2)
            for i in range(7, 0, -1):
                g.strokePath(path, pen(QColor(255, 42, 61, 26), i * 2.4))
            g.end()
            entry = (pix, path, dpr, w, h)
            CardBackMixin._GLOW_CACHE[px] = entry
        pix, path, _dpr, w, h = entry
        t = clock().t
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (t / 1.8 + self._phase))
        p.save()
        p.translate(center)
        p.rotate(math.sin(2 * math.pi * (t / 2.6 + self._phase)) * 2.5)
        p.scale(1.0 + 0.045 * pulse, 1.0 + 0.045 * pulse)
        p.setOpacity(min(1.0, 0.35 + 0.55 * pulse + 0.25 * self._hover.now))
        p.drawPixmap(QPointF(-w / 2, -h / 2), pix)
        p.setOpacity(1.0)
        p.fillPath(path, QColor("#ff5a68").lighter(100 + int(25 * pulse)))
        p.restore()

    @staticmethod
    def _wax_seal(p: QPainter, c: QPointF, rad: float, progress: float) -> None:
        if progress >= 1.0:
            return
        for sign in (-1, 1):
            p.save()
            p.setOpacity(1.0 - progress)
            p.translate(sign * rad * 1.6 * progress, rad * 1.2 * progress * progress)
            p.translate(c)
            p.rotate(sign * 28 * progress)
            p.translate(-c.x(), -c.y())
            half = QRectF(c.x() - rad * 1.6 if sign < 0 else c.x(), c.y() - rad * 1.6, rad * 1.6, rad * 3.2)
            p.setClipRect(half)
            p.setPen(pen("#5d0c16", rad * 0.12))
            p.setBrush(QColor("#b3202f"))
            p.drawEllipse(c, rad, rad)
            p.setPen(pen("#d4505e", rad * 0.08))
            p.setBrush(NO_BRUSH)
            p.drawEllipse(c, rad * 0.65, rad * 0.65)
            p.setPen(NO_PEN)
            p.setBrush(QColor("#d4505e"))
            p.drawPolygon(icons.star_polygon(c.x(), c.y(), rad * 0.4, rad * 0.17))
            p.restore()
