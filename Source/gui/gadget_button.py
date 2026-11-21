"""GadgetButton: nút bảo bối (Load / Restart / Hint / Auto Solve). (Scope F)
"""
import math
from typing import Optional

from PySide6.QtCore import (QEasingCurve, QRectF, QSize, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QLinearGradient, QPainter,
                           QPen)
from PySide6.QtWidgets import (QAbstractButton, QSizePolicy, QWidget)

from gui import icons, theme
from gui.icons import NO_BRUSH, pen
from gui.anim import Tween, clock
from gui.draw_utils import (ALIGN_CENTER, make_font)


class GadgetButton(QAbstractButton):
    """Nút bảo bối: kind = load | restart | hint | auto | pause.

    Icon chuyển động khi rê chuột (nơ rung cánh, giày nhún, bóng nảy), kim giây đồng hồ nhích mỗi giây,
    và vòng năng lượng cyan xoay quanh nút khi set_working(True) (Auto Solve đang chạy)."""

    _ICONS = {"load": icons.draw_bowtie, "restart": icons.draw_shoe, "hint": icons.draw_watch,
              "auto": icons.draw_ball, "pause": icons.draw_pause}

    def __init__(self, kind: str, caption: str, subtitle: str, tooltip: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.kind, self.caption, self.subtitle = kind, caption, subtitle
        self._working, self._last_second = False, -1
        self._glow = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        clock().tick.connect(self._on_tick)

    def sizeHint(self) -> QSize:
        return QSize(128, 112)

    def set_look(self, kind: str, caption: str, subtitle: str) -> None:
        self.kind, self.caption, self.subtitle = kind, caption, subtitle
        self.update()

    def set_working(self, working: bool) -> None:
        """True khi Agent đang tự suy luận: vòng năng lượng xoay quanh nút + bóng nảy liên tục."""
        self._working = working
        self.update()

    def _on_tick(self) -> None:
        if not self.isVisible():
            return
        second = int(clock().t)
        if self._working or self._glow.now > 0.02 or (self.kind == "hint" and second != self._last_second):
            self._last_second = second
            self.update()

    def enterEvent(self, event) -> None:
        self._glow.go(1.0, 180)

    def leaveEvent(self, event) -> None:
        self._glow.go(0.0, 240)

    def _paint_icon(self, p: QPainter, icon: QRectF, g: float) -> None:
        t = clock().t
        p.save()
        p.translate(icon.center())
        if self.kind == "load":                       # nơ: hai cánh rung khi hover
            flutter = g * math.sin(t * 26)
            p.scale(1.0 + 0.07 * flutter, 1.0)
            p.rotate(3.0 * flutter)
        elif self.kind == "restart":                  # giày: nhún và đá nhẹ khi hover
            p.rotate(-12.0 * g * abs(math.sin(t * 6)))
            p.translate(3.0 * g * math.sin(t * 6), 0)
        elif self.kind == "auto":                     # bóng: nảy lên, phồng xẹp nhịp nhàng
            energy = max(g, 1.0 if self._working else 0.0)
            p.translate(0, -icon.height() * 0.14 * abs(math.sin(t * 5.5)) * energy)
            squash = 1.0 + 0.06 * math.sin(t * 11) * energy
            p.scale(squash, 2.0 - squash)
        elif self.kind == "hint":                     # đồng hồ: rung nhẹ khi hover
            p.rotate(2.0 * g * math.sin(t * 22))
        p.translate(-icon.center())
        if self.kind == "hint":                       # kim giây nhích từng nốt mỗi giây
            icons.draw_watch(p, icon, second=int(t) % 60)
        else:
            self._ICONS[self.kind](p, icon)
        p.restore()

    def _paint_energy_ring(self, p: QPainter, r: QRectF) -> None:
        t = clock().t
        pulse = 0.65 + 0.35 * math.sin(t * 8)
        for width, peak in ((10, 70), (3.5, 255)):
            cone = QConicalGradient(r.center(), -((t * 170) % 360))
            cone.setColorAt(0.0, QColor(56, 242, 255, 0))
            cone.setColorAt(0.55, QColor(56, 242, 255, 0))
            cone.setColorAt(1.0, QColor(56, 242, 255, int(peak * pulse)))
            ring = QPen(QBrush(cone), width)
            ring.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(ring)
            p.setBrush(NO_BRUSH)
            p.drawRoundedRect(r.adjusted(-2, -2, 2, 2), 16, 16)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if not self.isEnabled():
            p.setOpacity(0.38)
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        if self.isDown():
            r.translate(0, 2)
        g = self._glow.now
        for width, alpha in ((12, 22), (8, 40)):
            p.setPen(pen(QColor(226, 185, 71, int(alpha * g)), width))
            p.setBrush(NO_BRUSH)
            p.drawRoundedRect(r, 14, 14)
        plate = QLinearGradient(r.topLeft(), r.bottomLeft())
        plate.setColorAt(0, QColor("#23365e"))
        plate.setColorAt(1, QColor("#0d172e"))
        p.setBrush(QBrush(plate))
        p.setPen(pen(QColor(226, 185, 71, int(130 + 125 * g)), 2))
        p.drawRoundedRect(r, 14, 14)
        if self._working:
            self._paint_energy_ring(p, r)
        icon_size = r.height() * 0.5
        icon = QRectF(r.center().x() - icon_size / 2, r.top() + 8 - 3 * g, icon_size, icon_size)
        self._paint_icon(p, icon, g)
        p.setPen(QColor(theme.CYAN_LASER if g > 0.5 else theme.GOLD_SOFT))
        p.setFont(make_font(theme.FONT_GADGET, 12, True, spacing=0.5))
        p.drawText(QRectF(r.left(), icon.bottom() + 2, r.width(), 20), ALIGN_CENTER, self.caption)
        p.setPen(QColor("#9fb0d8"))
        p.setFont(make_font(theme.FONT_DOSSIER, 10, False, True))
        p.drawText(QRectF(r.left(), icon.bottom() + 20, r.width(), 16), ALIGN_CENTER, self.subtitle)
