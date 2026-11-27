"""Mixin vẽ lớp highlight của thẻ: laser quét (target), viền đứt (source), tâm ngắm Hint. (Scope F)
"""
import math

from PySide6.QtCore import (QPointF, QRectF, Qt)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath)

from gui import theme
from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.anim import clock
from gui.draw_utils import (ALIGN_CENTER, make_font)


class CardHighlightMixin:
    """Các hàm vẽ highlight; dùng self._mode, self._hint, self._scan của CardView."""

    def _paint_highlight(self, p: QPainter, r: QRectF, u: float) -> None:
        if not (self._mode or self._hint):
            return
        t = self._scan.now
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.setBrush(NO_BRUSH)
        if self._mode == "target":
            p.save()
            p.setClipPath(path)
            band = r.height() * 0.22
            y = r.top() - band + (r.height() + band) * t
            sweep = QLinearGradient(0, y, 0, y + band)
            sweep.setColorAt(0, QColor(57, 255, 20, 0))
            sweep.setColorAt(0.8, QColor(57, 255, 20, 110))
            sweep.setColorAt(1, QColor(170, 255, 140, 220))
            p.fillRect(QRectF(r.left(), y, r.width(), band), QBrush(sweep))
            p.setPen(pen(QColor(190, 255, 170, 240), 2))
            p.drawLine(QPointF(r.left(), y + band), QPointF(r.right(), y + band))
            p.restore()
            for width, alpha in ((10, 30), (6, 65), (3, 255)):
                p.setPen(pen(QColor(57, 255, 20, alpha), width))     # laser xanh lá, nổi trên nền xanh đen và viền đỏ/xanh dương
                p.drawPath(path)
            p.setPen(pen("#e6ffe0", 3))
            size = u * 0.12
            for cx, cy, sx, sy in ((r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
                                   (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1)):
                p.drawLine(QPointF(cx + 5 * sx, cy + 5 * sy), QPointF(cx + (5 + size) * sx, cy + 5 * sy))
                p.drawLine(QPointF(cx + 5 * sx, cy + 5 * sy), QPointF(cx + 5 * sx, cy + (5 + size) * sy))
        elif self._mode == "source":
            dashed = pen(theme.GOLD_SOFT, 3)
            dashed.setStyle(Qt.PenStyle.DashLine)
            p.setPen(dashed)
            p.drawPath(path)
        elif self._mode == "basis":
            self._paint_basis(p, r, u, t, path)
        elif self._mode == "infer":
            self._paint_infer(p, r, u, t, path)
        if self._hint:
            self._paint_hint(p, r, u, t)

    def _badge(self, p: QPainter, rect: QRectF, text: str, fill: QColor, edge: QColor, ink: str,
               px: int = 10) -> None:
        p.setBrush(fill)
        p.setPen(pen(edge, 1.8))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        p.setPen(QColor(ink))
        p.setFont(make_font(theme.FONT_GADGET, px, True, spacing=1.0))
        p.drawText(rect, ALIGN_CENTER, text)

    def _paint_basis(self, p: QPainter, r: QRectF, u: float, t: float, path: QPainterPath) -> None:
        """Thẻ căn cứ: nhấp nháy mạnh (2 lần/giây, dưới ngưỡng gây khó chịu) vàng sáng <-> tối,
        viền dày, vòng sáng loang ra ngoài và số thứ tự to ở giữa thẻ khớp với sổ tay."""
        wave = math.sin(clock().t * 2 * math.pi * 2.0)
        on = max(0.0, min(1.0, 0.5 + 1.6 * wave))          # sóng gần vuông: sáng gắt / tắt hẳn
        p.save()
        p.setClipPath(path)
        p.fillRect(r, QColor(255, 210, 40, int(30 + 150 * on)))
        p.restore()
        p.setBrush(NO_BRUSH)
        halo = r.adjusted(-4 - 4 * on, -4 - 4 * on, 4 + 4 * on, 4 + 4 * on)
        halo_path = QPainterPath()
        halo_path.addRoundedRect(halo, 15, 15)
        p.setPen(pen(QColor(255, 220, 60, int(40 + 150 * on)), 10))
        p.drawPath(halo_path)
        p.setPen(pen(QColor(255, 200, 40, 255), 6))
        p.drawPath(path)
        p.setPen(pen(QColor(255, 255, 255, int(80 + 175 * on)), 3))
        p.drawPath(path)
        # số thứ tự to ở giữa thẻ (dễ ghép với sổ tay)
        if self._label:
            p.setPen(NO_PEN)
            p.setBrush(QColor(20, 12, 0, int(120 + 100 * on)))
            rad = max(17.0, u * 0.16)
            c = r.center()
            p.drawEllipse(c, rad, rad)
            p.setBrush(NO_BRUSH)
            p.setPen(pen(QColor(255, 225, 80, 255), 3))
            p.drawEllipse(c, rad, rad)
            p.setPen(QColor(255, 244, 190) if on > 0.5 else QColor(255, 205, 60))
            p.setFont(make_font(theme.FONT_GADGET, int(rad * (1.15 if len(self._label) < 3 else 0.8)), True))
            p.drawText(QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad), ALIGN_CENTER, self._label)
        text = "CĂN CỨ"
        self._badge(p, QRectF(r.center().x() - 38, r.top() - 6.0, 76.0, 18.0), text,
                    QColor(36, 26, 4, 245), QColor(255, 220, 90), "#fff0b8", 9)

    def _paint_infer(self, p: QPainter, r: QRectF, u: float, t: float, path: QPainterPath) -> None:
        """Thẻ sắp được lật: khung xanh lơ đứt chạy vòng + bốn góc ngắm + huy hiệu SUY RA."""
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 2)
        cyan = QColor(56, 242, 255)
        p.setBrush(NO_BRUSH)
        for width, alpha in ((11, int(30 + 45 * pulse)), (6, int(90 + 60 * pulse))):
            p.setPen(pen(QColor(56, 242, 255, alpha), width))
            p.drawPath(path)
        rim = pen(QColor(210, 252, 255, 245), 2.6)
        rim.setDashPattern([6.0, 4.0])
        rim.setDashOffset(-clock().t * 30)
        p.setPen(rim)
        p.drawPath(path)
        p.setPen(pen(cyan, 3))
        size = u * 0.14
        for cx, cy, sx, sy in ((r.left(), r.top(), 1, 1), (r.right(), r.top(), -1, 1),
                               (r.left(), r.bottom(), 1, -1), (r.right(), r.bottom(), -1, -1)):
            p.drawLine(QPointF(cx + 5 * sx, cy + 5 * sy), QPointF(cx + (5 + size) * sx, cy + 5 * sy))
            p.drawLine(QPointF(cx + 5 * sx, cy + 5 * sy), QPointF(cx + 5 * sx, cy + (5 + size) * sy))
        w = max(66.0, u * 0.5)
        self._badge(p, QRectF(r.center().x() - w / 2, r.top() - 6.0, w, 18.0), "SUY RA",
                    QColor(4, 28, 34, 240), QColor(120, 245, 255), "#d8fcff", 9)

    def _paint_hint(self, p: QPainter, r: QRectF, u: float, t: float) -> None:
        """Hiệu ứng Hint dạng tâm ngắm Đồng hồ gây mê (Hồng Magenta Neon, tách lớp khỏi laser)."""
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
        magenta = QColor(255, 43, 214)

        p.save()
        # 1. Viền ngoài tách lớp (nằm ngoài viền laser xanh lá để không bị đè nét)
        outer = r.adjusted(-3.5, -3.5, 3.5, 3.5)
        outer_path = QPainterPath()
        outer_path.addRoundedRect(outer, 15, 15)
        p.setBrush(NO_BRUSH)
        for width, alpha in ((10, int(35 + 45 * pulse)), (5, int(90 + 70 * pulse))):
            p.setPen(pen(QColor(255, 43, 214, alpha), width))
            p.drawPath(outer_path)

        rim = pen(QColor(255, 150, 238, int(190 + 65 * pulse)), 2.5)
        rim.setDashPattern([6.0, 4.0])
        rim.setDashOffset(-clock().t * 24)
        p.setPen(rim)
        p.drawPath(outer_path)

        # 2. Tâm ngắm Đồng hồ gây mê ở giữa thẻ
        center = r.center()
        rad = u * (0.20 + 0.025 * pulse)
        p.setBrush(QColor(255, 43, 214, int(24 + 26 * pulse)))
        p.setPen(pen(QColor(255, 43, 214, 90), 6))
        p.drawEllipse(center, rad, rad)
        p.setBrush(NO_BRUSH)
        p.setPen(pen(QColor(255, 210, 248, 235), 2))
        p.drawEllipse(center, rad, rad)
        p.setPen(pen(magenta, 1.5))
        p.drawEllipse(center, rad * 0.52, rad * 0.52)

        # 4 vạch chữ thập tâm ngắm xoay nhẹ
        p.save()
        p.translate(center)
        p.rotate((clock().t * 45) % 360)
        p.setPen(pen(QColor(255, 230, 250, 240), 2.2))
        inner_tick, outer_tick = rad * 0.35, rad * 1.32
        for deg in (0, 90, 180, 270):
            p.save()
            p.rotate(deg)
            p.drawLine(QPointF(inner_tick, 0), QPointF(outer_tick, 0))
            p.restore()
        p.restore()

        # Chấm khóa mục tiêu ở tâm
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 43, 214, 140))
        p.drawEllipse(center, 6.0, 6.0)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(center, 2.5, 2.5)

        # 3. Nhãn badge "HINT" nổi bật ở mép trên thẻ
        badge_w, badge_h = max(48.0, u * 0.36), 17.0
        badge = QRectF(r.center().x() - badge_w / 2, r.top() - 5.0, badge_w, badge_h)
        p.setBrush(QColor(28, 6, 26, 235))
        p.setPen(pen(QColor(255, 110, 230), 1.8))
        p.drawRoundedRect(badge, 6, 6)
        p.setPen(QColor("#ffe6fa"))
        p.setFont(make_font(theme.FONT_GADGET, 9, True, spacing=1.2))
        p.drawText(badge, ALIGN_CENTER, "HINT")
        p.restore()
