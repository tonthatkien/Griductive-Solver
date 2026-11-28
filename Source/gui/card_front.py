"""Mixin vẽ mặt ngửa của thẻ: nền lab, chân dung, dấu CRIMINAL/INNOCENT, manh mối. (Scope F)
"""

import math

from PySide6.QtCore import (QPointF, QRectF, Qt)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                           QPainterPath, QPixmap, QRadialGradient)

from gui import icons, theme
from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.anim import character_pixmap, clock
from gui.draw_utils import (A, ALIGN_CENTER, ALIGN_LEFT_MID, WRAP_TOP, draw_brackets,
                            draw_fitted, draw_typed, flags, make_font)


# Màu nhấn của thẻ đã lật: đỏ neon = CRIMINAL, xanh dương sáng = INNOCENT (dễ phân biệt trên nền tối).
_ACCENTS = {"CRIMINAL": "#ff3b4e", "INNOCENT": "#4aa8ff"}


class CardFrontMixin:
    """Các hàm vẽ mặt ngửa; dùng thuộc tính của CardView (self.status, self._type, ...)."""

    @staticmethod
    def _compact(u: float) -> bool:
        """Thẻ nhỏ (lưới 4x4, 5x5...): dồn chân dung + tên + kết luận vào một hàng để dành chỗ cho manh mối."""
        return u < 215

    def _front_rects(self, r: QRectF, u: float):
        """Trả về pad, header, portrait, plate, clue_box, name_rect, job_rect."""
        if self._compact(u):
            pad = u * 0.06
            header = QRectF(r.left(), r.top(), r.width(), u * 0.14)
            ph = u * 0.40
            portrait = QRectF(r.left() + pad, header.bottom() + pad * 0.6, ph / 1.08, ph)
            tx = portrait.right() + pad
            tw = r.right() - pad - tx
            name_rect = QRectF(tx, portrait.top() - 1, tw, u * 0.14)
            job_rect = QRectF(tx, name_rect.bottom(), tw, u * 0.11)
            plate_h = u * 0.14
            plate = QRectF(tx, portrait.bottom() - plate_h, tw, plate_h)
            top = portrait.bottom() + pad * 0.6
            clue_box = QRectF(r.left() + pad, top, r.width() - 2 * pad, r.bottom() - pad * 0.8 - top)
            return pad, header, portrait, plate, clue_box, name_rect, job_rect
        pad = u * 0.07
        header = QRectF(r.left(), r.top(), r.width(), u * 0.15)
        pw = u * 0.36
        portrait = QRectF(r.left() + pad, header.bottom() + pad * 0.9, pw, pw * 1.08)
        plate = QRectF(r.left() + pad, portrait.bottom() + pad * 0.9, r.width() - 2 * pad, u * 0.19)
        top = plate.bottom() + pad * 0.7
        clue_box = QRectF(r.left() + pad, top, r.width() - 2 * pad, r.bottom() - pad - top)
        tx = portrait.right() + pad
        tw = r.right() - pad - tx
        name_rect = QRectF(tx, portrait.top() - 2, tw, u * 0.17)
        job_rect = QRectF(tx, portrait.top() + u * 0.18, tw, u * 0.22)
        return pad, header, portrait, plate, clue_box, name_rect, job_rect

    def _front_base(self, r: QRectF, u: float) -> QPixmap:
        """Lớp tĩnh của mặt ngửa vẽ MỘT lần rồi dùng lại (có thêm lề 8px cho quầng sáng viền)."""
        dpr = self.devicePixelRatioF()
        key = (round(r.width(), 1), round(r.height(), 1), dpr, self.status, self.name, self.profession, self.cell)
        if self._front_key != key:
            margin = 8
            pix = QPixmap(int((r.width() + 2 * margin) * dpr) + 1, int((r.height() + 2 * margin) * dpr) + 1)
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.GlobalColor.transparent)
            g = QPainter(pix)
            g.setRenderHint(QPainter.RenderHint.Antialiasing)
            g.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            self._paint_front_static(g, QRectF(margin, margin, r.width(), r.height()), u)
            g.end()
            self._front_cache, self._front_key = pix, key
        return self._front_cache

    def _paint_front(self, p: QPainter, r: QRectF, u: float) -> None:
        """Mặt ngửa: lớp tĩnh (cache) + góc ngắm nhấp nháy + chữ manh mối đang gõ."""
        p.drawPixmap(QPointF(r.left() - 8, r.top() - 8), self._front_base(r, u))
        portrait, clue_box = self._front_rects(r, u)[2], self._front_rects(r, u)[4]
        self._paint_reticle(p, portrait, u)
        self._paint_card_blink(p, r, u)
        compact = self._compact(u)
        pad = u * (0.06 if compact else 0.07)
        count = int(self._type.now * len(self.clue_text) + 0.5)
        text_rect = clue_box.adjusted(pad * 0.9, u * (0.075 if compact else 0.085), -pad * 0.6,
                                      -pad * (0.2 if compact else 0.25))
        p.save()
        p.setClipRect(clue_box)                  # chữ không bao giờ tràn ra ngoài khung / đè thẻ dưới
        draw_typed(p, text_rect, self.clue_text, count, theme.FONT_CLUE_BODY, int(u * 0.135),
                   8 if compact else 10, "#d6f3ff",
                   cursor=self._type_busy and 0 < count < len(self.clue_text))
        p.restore()

    def _paint_reticle(self, p: QPainter, portrait: QRectF, u: float) -> None:
        """Góc ngắm quanh chân dung: 4 góc thở sáng/tối."""
        accent = QColor(_ACCENTS.get(self.status or "", theme.CYAN_LASER))
        t = clock().t + self._phase * 10
        pulse = 0.5 + 0.5 * math.sin(t * 2.6)                 # 0..1, nhịp thở của góc ngắm
        frame = portrait.adjusted(-3, -3, 3, 3)
        size = u * 0.07
        p.save()
        glow = QColor(accent)
        glow.setAlpha(int(30 + 70 * pulse))
        draw_brackets(p, frame, glow, size * (1.0 + 0.25 * pulse), max(4.0, u * 0.03))      # quầng sáng
        bright = QColor(accent.lighter(150))
        bright.setAlpha(int(110 + 145 * pulse))
        draw_brackets(p, frame, bright, size * (1.0 + 0.25 * pulse), 2.0)                   # nét chính
        p.restore()

    def _paint_card_blink(self, p: QPainter, r: QRectF, u: float) -> None:
        """Nhấp nháy cả thẻ: nền phủ màu kết luận + viền neon cùng sáng/tối theo nhịp thở
        (đỏ = CRIMINAL, xanh dương = INNOCENT). Mỗi thẻ lệch pha để không nháy đồng loạt."""
        accent = QColor(_ACCENTS.get(self.status or "", theme.CYAN_LASER))
        t = clock().t + self._phase * 10
        wave = 0.5 + 0.5 * math.sin(t * 2.4)        # 0..1, ~2.6 s / nhịp
        pulse = wave * wave                          # nhọn hơn: sáng gắt rồi dịu lâu
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.save()
        tint = QColor(accent)
        tint.setAlpha(int(8 + 52 * pulse))
        p.fillPath(path, tint)                       # nền thẻ nháy
        p.setBrush(NO_BRUSH)
        for width, alpha in ((12, 60), (7, 110)):    # quầng viền nở ra khi sáng
            glow = QColor(accent)
            glow.setAlpha(int(alpha * pulse))
            p.setPen(pen(glow, width))
            p.drawPath(path)
        edge = QColor(accent.lighter(100 + int(60 * pulse)))
        edge.setAlpha(int(150 + 105 * pulse))
        p.setPen(pen(edge, 2.5))
        p.drawPath(path)
        p.restore()

    def _paint_front_static(self, p: QPainter, r: QRectF, u: float) -> None:
        """Nền lab Agasa: lưới, scanline mờ, header, chân dung trong góc ngắm, tên, khung kết luận,
        khung manh mối (chưa có chữ), viền neon theo kết luận."""
        accent = QColor(_ACCENTS.get(self.status or "", theme.CYAN_LASER))
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        bg = QLinearGradient(r.topLeft(), r.bottomRight())
        bg.setColorAt(0, QColor("#11243d"))
        bg.setColorAt(1, QColor("#050d1b"))
        p.fillPath(path, QBrush(bg))
        p.save()
        p.setClipPath(path)
        step = max(10.0, u * 0.09)
        p.setPen(pen(QColor(56, 242, 255, 16), 1))
        x = r.left()
        while x < r.right():
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            x += step
        y = r.top()
        while y < r.bottom():
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            y += step
        p.setPen(pen(QColor(0, 0, 0, 24), 1))
        y = r.top()
        while y < r.bottom():
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            y += 3
        halo = QRadialGradient(QPointF(r.center().x(), r.top()), r.width() * 0.95)
        halo.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 60))
        halo.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 0))
        p.fillRect(r, QBrush(halo))

        pad, header, portrait, plate, clue_box, name_rect, job_rect = self._front_rects(r, u)
        compact = self._compact(u)
        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRect(header)
        p.setPen(pen(accent, 1.5))
        p.drawLine(QPointF(r.left(), header.bottom()), QPointF(r.right(), header.bottom()))
        p.setPen(accent)
        p.setFont(make_font(theme.FONT_DISPLAY, u * 0.075, True, spacing=1))
        p.drawText(header.adjusted(pad, 0, 0, 0), ALIGN_LEFT_MID, f"SUBJECT // {self.cell}")
        p.setPen(NO_PEN)
        p.setBrush(accent)
        p.drawEllipse(QPointF(header.right() - pad - u * 0.03, header.center().y()), u * 0.025, u * 0.025)

        pixmap = character_pixmap(self.name)
        if pixmap is not None and not pixmap.isNull():
            p.drawPixmap(portrait.toRect(), pixmap)
        else:
            icons.draw_avatar(p, portrait, self.name)
        p.fillRect(portrait, QColor(56, 242, 255, 26))
        p.setPen(pen(QColor(0, 0, 0, 45), 1))
        y = portrait.top()
        while y < portrait.bottom():
            p.drawLine(QPointF(portrait.left(), y), QPointF(portrait.right(), y))
            y += 3
        draw_brackets(p, portrait.adjusted(-3, -3, 3, 3), accent, u * 0.07)

        draw_fitted(p, name_rect, self.name, theme.display(self.name), int(u * 0.17), 9 if compact else 11,
                    "#eaf6ff", bold=True, fl=ALIGN_LEFT_MID)
        draw_fitted(p, job_rect, self.profession.upper(), theme.FONT_MONO, int(u * 0.105),
                    8 if compact else 9, "#7fdcff", fl=ALIGN_LEFT_MID if compact else WRAP_TOP)
        self._paint_stamp(p, plate, u)

        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 12, 26, 175))
        p.drawRoundedRect(clue_box, 6, 6)
        p.setBrush(accent)
        p.drawRect(QRectF(clue_box.left(), clue_box.top() + 5, 3, clue_box.height() - 10))
        p.setPen(accent)
        p.setFont(make_font(theme.FONT_CLUE_TITLE, u * 0.07, True, spacing=1.2))
        p.drawText(clue_box.adjusted(pad * 0.9, u * 0.01, 0, 0), flags(A.AlignLeft, A.AlignTop), "MANH MỐI")
        p.restore()

        p.setBrush(NO_BRUSH)
        for width, alpha in ((8, 22), (4, 55)):
            glow = QColor(accent)
            glow.setAlpha(alpha)
            p.setPen(pen(glow, width))
            p.drawPath(path)
        p.setPen(pen(accent, 2))
        p.drawPath(path)
        draw_brackets(p, r.adjusted(5, 5, -5, -5), QColor(255, 255, 255, 150), u * 0.09, 1.5)

    def _paint_stamp(self, p: QPainter, area: QRectF, u: float) -> None:
        """Module kết luận kiểu hologram: viền đôi neon + icon + CRIMINAL / INNOCENT."""
        criminal = self.status == "CRIMINAL"
        accent = QColor(_ACCENTS.get(self.status or "", theme.CYAN_LASER))
        p.save()
        fill = QColor(accent)
        fill.setAlpha(40)
        p.setBrush(fill)
        p.setPen(pen(accent, max(1.5, u * 0.014)))
        p.drawRoundedRect(area, 6, 6)
        inner = QColor(accent)
        inner.setAlpha(110)
        p.setBrush(NO_BRUSH)
        p.setPen(pen(inner, 1))
        p.drawRoundedRect(area.adjusted(4, 4, -4, -4), 4, 4)
        icon = QRectF(area.left() + u * 0.03, area.top() + u * 0.025, area.height() - u * 0.05,
                      area.height() - u * 0.05)
        (icons.draw_handcuffs if criminal else icons.draw_badge)(p, icon, accent.name())
        draw_fitted(p, QRectF(icon.right() + u * 0.02, area.top(), area.right() - icon.right() - u * 0.04,
                              area.height()),
                    "CRIMINAL" if criminal else "INNOCENT", theme.FONT_DISPLAY, int(u * 0.1), 6,
                    accent.lighter(135), bold=True, fl=ALIGN_CENTER)
        p.restore()