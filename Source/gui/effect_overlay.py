"""EffectOverlay: hiệu ứng toàn màn hình 'contradict' và 'victory'. (Scope F)
"""
import math
import random
from typing import List, Tuple

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, Qt)
from PySide6.QtGui import (QBrush, QColor, QPainter,
                           QRadialGradient)
from PySide6.QtWidgets import (QWidget)

from gui import icons, theme
from gui.icons import NO_PEN
from gui.anim import Tween
from gui.draw_utils import (ALIGN_CENTER, ALIGN_LEFT_MID, draw_neon_text, make_font)


class EffectOverlay(QWidget):
    """'contradict': chớp sét + bóng đen hung thủ. 'victory': "Sự thật chỉ có một!"."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._mode = ""
        self._tween = Tween(self, self.update, QEasingCurve.Type.Linear)
        self._tween.finished.connect(self._done)
        rng = random.Random(7)
        self._bolts: List[List[Tuple[float, float]]] = []
        for x0 in (0.16, 0.5, 0.84):
            pts, x = [], x0
            for i in range(9):
                pts.append((x, i * 0.07))
                x += rng.uniform(-0.05, 0.05)
            self._bolts.append(pts)
        self._sparks = [(rng.random(), rng.uniform(0.4, 1.0), rng.random(), rng.uniform(4, 11))
                        for _ in range(70)]
        self.hide()

    def play(self, mode: str) -> None:
        self._mode = mode
        self.setGeometry(self.parentWidget().rect())
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, mode == "contradict")
        self.show()
        self.raise_()
        self._tween.jump(0.0)
        self._tween.go(1.0, 1500 if mode == "contradict" else 4200)

    def dismiss(self) -> None:
        self._tween.stop()
        self.hide()

    def _done(self) -> None:
        if self._mode == "contradict":
            self.hide()

    def mousePressEvent(self, event) -> None:
        if self._mode == "victory":
            self.dismiss()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self._mode == "contradict":
            self._paint_contradict(p, self._tween.now)
        elif self._mode == "victory":
            self._paint_victory(p, self._tween.now)

    def _paint_contradict(self, p: QPainter, t: float) -> None:
        w, h = float(self.width()), float(self.height())
        p.fillRect(self.rect(), QColor(18, 0, 10, int(215 * (1 - t) ** 0.5)))
        if t < 0.15:
            p.fillRect(self.rect(), QColor(255, 255, 255, int(255 * (1 - t / 0.15))))
        if t < 0.75 and int(t * 24) % 3 != 2:
            for pts in self._bolts:
                icons.draw_lightning(p, [QPointF(x * w, y * h) for x, y in pts])
        alpha = int(255 * min(1.0, t * 6) * (1.0 if t < 0.75 else (1 - t) / 0.25))
        size = min(w, h) * 0.62 * (0.85 + 0.15 * min(1.0, t * 4))
        rect = QRectF(w / 2 - size / 2, h * 0.58 - size / 2, size, size)
        halo = QRadialGradient(rect.center(), size * 0.8)
        halo.setColorAt(0, QColor(255, 0, 40, alpha // 3))
        halo.setColorAt(1, QColor(255, 0, 40, 0))
        p.fillRect(self.rect(), QBrush(halo))
        icons.draw_villain(p, rect, alpha)
        title = QRectF(0, h * 0.1, w, h * 0.1)
        draw_neon_text(p, title, "SUY LUẬN NGƯỢC LOGIC!",
                       make_font(theme.FONT_CLUE_TITLE, h * 0.07, True, spacing=5),
                       "#ff6b78", theme.RED_NEON, 1.0, ALIGN_CENTER, alpha)
        p.setFont(make_font(theme.FONT_DOSSIER, h * 0.03, False, True))
        p.setPen(QColor(255, 255, 255, alpha))
        p.drawText(QRectF(0, h * 0.2, w, h * 0.05), ALIGN_CENTER, "Kết luận ngược lại mới là hệ quả bắt buộc.")

    def _paint_victory(self, p: QPainter, t: float) -> None:
        w, h = float(self.width()), float(self.height())
        p.fillRect(self.rect(), QColor(4, 10, 28, int(150 * min(1.0, t * 3))))
        spot = QRadialGradient(QPointF(w / 2, h * 0.45), h * 0.6)
        spot.setColorAt(0, QColor(255, 230, 150, 80))
        spot.setColorAt(1, QColor(255, 230, 150, 0))
        p.fillRect(self.rect(), QBrush(spot))
        p.setPen(NO_PEN)
        for x, speed, phase, size in self._sparks:
            y = ((t * speed * 1.6 + phase) % 1.0) * h
            p.setBrush(QColor(255, 214, 80, 200))
            p.drawPolygon(icons.star_polygon(x * w, y, size, size * 0.4))
        face = min(w, h) * 0.3
        bob = math.sin(t * 12) * 4
        icons.draw_conan(p, QRectF(w / 2 - face / 2, h * 0.12 + bob, face, face), "happy")
        text, px = "SỰ THẬT CHỈ CÓ MỘT!", h * 0.085
        font = make_font(theme.FONT_CLUE_TITLE, px, True, spacing=6)
        p.setFont(font)
        full = p.fontMetrics().horizontalAdvance(text)
        shown = text[: int(len(text) * min(1.0, t * 2.2)) + 1]
        box = QRectF((w - full) / 2, h * 0.58, full + 40, px * 1.5)
        draw_neon_text(p, box, shown, font, theme.GOLD_SOFT, theme.CYAN_LASER, 1.0, ALIGN_LEFT_MID)
        if t > 0.5:
            p.setFont(make_font(theme.FONT_DOSSIER, h * 0.035, False, True))
            p.setPen(QColor(235, 240, 255, int(255 * min(1.0, (t - 0.5) * 3))))
            p.drawText(QRectF(0, h * 0.7, w, h * 0.06), ALIGN_CENTER, "Vụ án đã được phá. Hung thủ không còn đường chối cãi.")
        if t > 0.9:
            p.setFont(make_font(theme.FONT_GADGET, h * 0.022, spacing=2))
            p.setPen(QColor(160, 176, 216))
            p.drawText(QRectF(0, h * 0.9, w, h * 0.05), ALIGN_CENTER, "Nhấn chuột để tiếp tục")