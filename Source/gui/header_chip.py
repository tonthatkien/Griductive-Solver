"""HeaderChip: các ô thông tin neon ở hàng đầu bản đồ (lời nhắc, số vụ đã phá, tổng sao). (Scope F)
"""
import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from gui import icons, theme
from gui.anim import clock
from gui.draw_utils import ALIGN_LEFT_MID, draw_brackets, draw_neon_text, make_font
from gui.icons import NO_BRUSH, NO_PEN, pen

ACCENT_DONE = "#4aa8ff"


class HeaderChip(QWidget):
    """Ô thông tin ở hàng đầu bản đồ, cùng phong cách neon với ghim và bảng khu phố.

    kind: 'hint'  = lời nhắc (chấm cyan nhấp nháy + chữ mono giãn cách)
          'cases' = số vụ đã phá (huy hiệu + nhãn + số lớn)
          'stars' = tổng số sao (ngôi sao + nhãn + số lớn)
    """

    def __init__(self, kind: str, label: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind, self.label = kind, label
        self.done, self.total = 0, 0
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        clock().tick.connect(self._on_tick)

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def set_value(self, done: int, total: int) -> None:
        self.done, self.total = done, total
        self.updateGeometry()
        self.update()

    def _accent(self) -> QColor:
        if self.kind == "hint":
            return QColor(theme.CYAN_LASER)
        if self.total and self.done >= self.total:
            return QColor(theme.GOLD_SOFT)
        return QColor(ACCENT_DONE if self.kind == "cases" else theme.GOLD)

    def sizeHint(self) -> QSize:
        if self.kind == "hint":
            fm = QFontMetricsF(make_font(theme.FONT_MONO, 12, True, spacing=1.6))
            return QSize(int(fm.horizontalAdvance(self.label.upper())) + 58, 36)
        lab = QFontMetricsF(make_font(theme.FONT_MONO, 10, True, spacing=1.4))
        val = QFontMetricsF(make_font(theme.FONT_GADGET, 20, True))
        return QSize(int(lab.horizontalAdvance(self.label) + val.horizontalAdvance(f"{self.done}/{self.total}")) + 82,
                     36)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        t = clock().t
        accent = self._accent()
        breath = 0.5 + 0.5 * math.sin(t * 2.0 + (0.0 if self.kind != "stars" else 1.3))
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        plate = QPainterPath()
        plate.addRoundedRect(r, 9, 9)
        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0, QColor(14, 28, 62, 225))
        bg.setColorAt(1, QColor(5, 10, 24, 235))
        p.fillPath(plate, QBrush(bg))
        p.setBrush(NO_BRUSH)
        halo = QColor(accent)
        halo.setAlpha(int(22 + 22 * breath))
        p.setPen(pen(halo, 5))
        p.drawPath(plate)
        edge = QColor(accent)
        edge.setAlpha(190)
        p.setPen(pen(edge, 1.5))
        p.drawPath(plate)
        draw_brackets(p, r.adjusted(-2, -2, 2, 2), accent.lighter(135), 7, 1.4)

        if self.kind == "hint":
            c = QPointF(r.left() + 17, r.center().y())
            ring = QColor(accent)
            ring.setAlpha(int(140 * (1 - (t * 0.8) % 1.0)))
            p.setPen(pen(ring, 1.5))
            p.drawEllipse(c, 4 + 6 * ((t * 0.8) % 1.0), 4 + 6 * ((t * 0.8) % 1.0))   # sóng lan như ghim chưa phá
            p.setPen(NO_PEN)
            p.setBrush(accent)
            p.drawEllipse(c, 3.6, 3.6)
            p.setFont(make_font(theme.FONT_MONO, 12, True, spacing=1.6))
            p.setPen(QColor("#bff6ff"))
            p.drawText(QRectF(r.left() + 32, r.top(), r.width() - 38, r.height()), ALIGN_LEFT_MID,
                       self.label.upper())
            p.end()
            return

        icon = QRectF(r.left() + 10, r.center().y() - 11, 22, 22)
        if self.kind == "cases":
            icons.draw_badge(p, icon)
        else:
            glow = QRadialGradient(icon.center(), 15)
            glow.setColorAt(0, QColor(255, 214, 80, int(80 + 60 * breath)))
            glow.setColorAt(1, QColor(255, 214, 80, 0))
            p.setPen(NO_PEN)
            p.setBrush(QBrush(glow))
            p.drawEllipse(icon.center(), 15, 15)
            p.setBrush(QColor(theme.GOLD_SOFT))
            p.drawPolygon(icons.star_polygon(icon.center().x(), icon.center().y(), 10.5, 4.4))
        p.setFont(make_font(theme.FONT_MONO, 10, True, spacing=1.4))
        p.setPen(QColor("#7fdcff"))
        lab_w = QFontMetricsF(p.font()).horizontalAdvance(self.label) + 4
        p.drawText(QRectF(icon.right() + 8, r.top(), lab_w, r.height()), ALIGN_LEFT_MID, self.label)
        val_x = icon.right() + 8 + lab_w + 6
        draw_neon_text(p, QRectF(val_x, r.top(), r.right() - val_x - 10, r.height()),
                       f"{self.done}/{self.total}", make_font(theme.FONT_GADGET, 20, True),
                       accent.lighter(125), accent, 0.7 + 0.3 * breath, ALIGN_LEFT_MID)
        p.end()
