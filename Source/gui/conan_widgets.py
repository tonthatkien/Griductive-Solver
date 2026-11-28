"""ConanWidget + ConanToast: avatar Conan, bong bóng thoại gõ chữ, popup NOT_PROVABLE. (Scope F)
"""
import math
from typing import Optional

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF, QTimer, Signal)
from PySide6.QtGui import (QColor, QPainter,
                           QPainterPath)
from PySide6.QtWidgets import (QWidget)

from gui import icons, theme
from gui.icons import NO_PEN, pen
from gui.anim import Tween, Typer
from gui.draw_utils import (draw_typed)


class ConanWidget(QWidget):
    """Avatar Conan + bong bóng thoại gõ chữ. mood: neutral | think | shake | shock | happy."""

    typed = Signal()            # mỗi 2 ký tự đã gõ, nối vào SoundManager nếu muốn tiếng gõ

    def __init__(self, parent: Optional[QWidget] = None, plate: bool = False) -> None:
        super().__init__(parent)
        self._mood, self._plate = "neutral", plate
        self._wiggle = Tween(self, self.update, QEasingCurve.Type.Linear)
        self.typer = Typer(self)
        self.typer.changed.connect(self.update)
        self.typer.typed.connect(self.typed)

    def say(self, text: str, mood: str = "neutral") -> None:
        self._mood = mood
        self._wiggle.jump(0.0)
        if mood in ("shake", "shock"):
            self._wiggle.go(1.0, 650)
        self.typer.start(text)
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = float(self.width()), float(self.height())
        if self._plate:
            p.setBrush(QColor(8, 14, 30, 238))
            p.setPen(pen(theme.GOLD, 2))
            p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 14, 14)
        size = min(h - 18, w * 0.36)
        face = QRectF(10, h - size - 8, size, size)
        t = self._wiggle.now
        angle = math.sin(t * math.pi * 8) * 11 * (1 - t) if self._mood == "shake" else 0.0
        if self._mood == "shock":
            angle = math.sin(t * math.pi * 14) * 4 * (1 - t)
        icons.draw_conan(p, face, self._mood, angle)
        bubble = QRectF(face.right() + 16, 10, w - face.right() - 26, h - 20)
        path = QPainterPath()
        path.addRoundedRect(bubble, 14, 14)
        tail = QPainterPath()
        tail.moveTo(bubble.left() + 1, bubble.center().y() - 8)
        tail.lineTo(bubble.left() - 14, bubble.center().y() + 8)
        tail.lineTo(bubble.left() + 1, bubble.center().y() + 10)
        tail.closeSubpath()
        p.setPen(pen("#6b5232", 2))
        p.setBrush(QColor("#fffbe8"))
        p.drawPath(path.united(tail))
        p.setPen(NO_PEN)
        p.drawRect(QRectF(bubble.left() - 1, bubble.center().y() - 7, 4, 16))
        draw_typed(p, bubble.adjusted(10, 6, -10, -6), self.typer.text, self.typer.shown,
                   theme.FONT_DOSSIER, 15, 9, theme.INK, bold=True, italic=True, center=True,
                   cursor=self.typer.cursor_visible)


class ConanToast(ConanWidget):
    """Popup nhỏ ở góc dưới phải (NOT_PROVABLE): Conan lắc đầu, tự trượt vào rồi ra."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, plate=True)
        self.setFixedSize(380, 132)
        self._leaving = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._slide_out)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.finished.connect(self._slide_done)
        self.hide()

    def _target(self) -> QPoint:
        parent = self.parentWidget()
        return QPoint(parent.width() - self.width() - 24, parent.height() - self.height() - 24)

    def popup(self, text: str, mood: str = "shake", ms: int = 2800) -> None:
        self.say(text, mood)
        self._leaving = False
        target = self._target()
        start = QPoint(self.parentWidget().width() + 10, target.y())
        self._slide.stop()
        self.move(start)
        self.show()
        self.raise_()
        self._slide.setDuration(380)
        self._slide.setStartValue(start)
        self._slide.setEndValue(target)
        self._slide.start()
        self._timer.start(ms)

    def _slide_out(self) -> None:
        self._leaving = True
        self._slide.stop()
        self._slide.setDuration(300)
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(QPoint(self.parentWidget().width() + 10, self.y()))
        self._slide.start()

    def _slide_done(self) -> None:
        if self._leaving:
            self.hide()
            self._leaving = False
