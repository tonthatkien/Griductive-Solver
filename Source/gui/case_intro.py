"""CaseIntro: cảnh mở đầu kiểu phim trinh thám khi vào màn: hai dải đen điện ảnh trượt vào, tên địa điểm + giờ
hiện lên giữa nền, rồi mờ đi. Bấm chuột để bỏ qua. (Scope F)

Phát hai tín hiệu: `reveal` (chữ bắt đầu mờ đi: lúc này cửa sổ chính cho giao diện + thẻ hiện dần) và
`done` (cảnh mở đầu kết thúc hẳn).
"""
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui import theme
from gui.anim import Tween
from gui.draw_utils import ALIGN_CENTER, ALIGN_LEFT_MID, draw_neon_text, make_font

TOTAL_MS = 2700          # tổng thời lượng
BARS_IN_MS = 350         # dải đen trượt vào
TEXT_IN_MS = 300         # chữ bắt đầu hiện
HOLD_END_MS = 2000       # hết giữ chữ: chữ mờ đi, dải đen trượt ra, phát `reveal`
OUT_MS = 520


def case_time(seed: str) -> str:
    """Giờ 'ghi nhận' cố định theo vụ án, rơi vào ban đêm (21:00 - 03:59)."""
    n = sum(ord(c) * (i + 3) for i, c in enumerate(seed))
    return f"{(21 + n % 7) % 24:02d}:{(n * 7) % 60:02d}"


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class CaseIntro(QWidget):
    reveal = Signal()
    done = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._tween = Tween(self, self._on_frame, QEasingCurve.Type.Linear)
        self._tween.finished.connect(self._finish)
        self._revealed = False
        self._kicker = self._place = self._time = self._sub = ""
        self.hide()

    def play(self, kicker: str, place: str, time_text: str, sub: str) -> None:
        self._kicker, self._place, self._time, self._sub = kicker, place, time_text, sub
        self._revealed = False
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._tween.jump(0.0)
        self._tween.go(1.0, TOTAL_MS)

    def skip(self) -> None:
        if self.isVisible():
            self._tween.stop()
            self._finish()

    def mousePressEvent(self, event) -> None:
        self.skip()

    def _on_frame(self) -> None:
        if not self._revealed and self._tween.now * TOTAL_MS >= HOLD_END_MS:
            self._revealed = True
            self.reveal.emit()
        self.update()

    def _finish(self) -> None:
        if not self._revealed:
            self._revealed = True
            self.reveal.emit()
        self.hide()
        self.done.emit()

    def paintEvent(self, _event) -> None:
        ms = self._tween.now * TOTAL_MS
        w, h = float(self.width()), float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        bar = _ease(ms / BARS_IN_MS) * (1.0 - _ease((ms - HOLD_END_MS) / OUT_MS))
        bh = h * 0.13 * bar
        gold = QColor(theme.GOLD)
        gold.setAlpha(int(170 * bar))
        for y in (0.0, h - bh):
            p.fillRect(QRectF(0, y, w, bh), QColor(0, 0, 0, 240))
        p.fillRect(QRectF(0, bh - 1.5, w, 1.5), gold)
        p.fillRect(QRectF(0, h - bh, w, 1.5), gold)
        if bh > 22 and int(ms / 420) % 2 == 0:               # "● GHI HÌNH" nhấp nháy trong dải đen
            p.setFont(make_font(theme.FONT_MONO, 12, True, spacing=2))
            p.setPen(QColor(255, 70, 80, 230))
            p.drawText(QRectF(24, 0, 240, bh), ALIGN_LEFT_MID, "●  GHI HÌNH")

        a = _ease((ms - TEXT_IN_MS) / 450) * (1.0 - _ease((ms - HOLD_END_MS) / 380))
        if a <= 0.01:
            return
        alpha = int(255 * a)
        shade = QRadialGradient(QPointF(w / 2, h / 2), w * 0.5)
        shade.setColorAt(0, QColor(0, 0, 0, int(130 * a)))
        shade.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(shade))

        spread = 1.0 - _ease((ms - TEXT_IN_MS) / 900)        # chữ co khít dần lại
        title = f"{self._place}  ·  {self._time}"
        family = theme.display(title)                          # Tektur cho chữ Việt (Cinzel thiếu glyph)
        px = min(h * 0.085, 66.0)
        while px > 16 and QFontMetricsF(make_font(family, px, True, spacing=6)).horizontalAdvance(title) > w * 0.86:
            px -= 1
        title_box = QRectF(0, h * 0.5 - px * 0.75, w, px * 1.5)
        draw_neon_text(p, title_box, title, make_font(family, px, True, spacing=6 + 18 * spread),
                       theme.GOLD_SOFT, theme.CYAN_LASER, 1.0, ALIGN_CENTER, alpha)
        kpx = max(12.0, h * 0.022)
        p.setFont(make_font(theme.FONT_MONO, kpx, True, spacing=5 + 10 * spread))
        p.setPen(QColor(127, 220, 255, alpha))
        p.drawText(QRectF(0, title_box.top() - kpx * 2.6, w, kpx * 2), ALIGN_CENTER, self._kicker)
        full = QFontMetricsF(make_font(family, px, True, spacing=6)).horizontalAdvance(title)
        line = full * _ease((ms - TEXT_IN_MS - 150) / 700)    # vạch vàng nở ra từ giữa
        gold.setAlpha(int(200 * a))
        p.fillRect(QRectF((w - line) / 2, title_box.bottom() + 6, line, 2), gold)
        spx = max(13.0, h * 0.03)
        p.setFont(make_font(theme.FONT_DOSSIER, spx, False, True))
        p.setPen(QColor(225, 233, 255, int(alpha * 0.9)))
        p.drawText(QRectF(0, title_box.bottom() + 16, w, spx * 2), ALIGN_CENTER, self._sub)