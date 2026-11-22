"""Thẻ hồ sơ CardView: trạng thái, animation lật, sự kiện, paintEvent. (Scope F)

Phần vẽ mặt úp / mặt ngửa / highlight nằm ở card_back.py, card_front.py, card_highlight.py (mixin).
"""
import math
import random
from typing import List, Optional, Tuple

from PySide6.QtCore import (QEasingCurve, QPointF, QRectF, Qt,
                            QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QPainter,
                           QPixmap)
from PySide6.QtWidgets import (QSizePolicy, QWidget)

from gui import icons
from gui.icons import NO_PEN
from gui.anim import Tween, clock
from gui.card_back import CardBackMixin
from gui.card_front import CardFrontMixin
from gui.card_highlight import CardHighlightMixin


class CardView(CardBackMixin, CardFrontMixin, CardHighlightMixin, QWidget):
    """Một thẻ nhân vật: úp = bìa hồ sơ mật, ngửa = hồ sơ giấy ố vàng + dấu CRIMINAL/INNOCENT."""

    clicked = Signal(str)

    def __init__(self, cell: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.cell = cell
        self.name = ""
        self.profession = ""
        self.status: Optional[str] = None
        self.clue_text = ""
        self._mode = ""
        self._hint = False
        self._input = True
        self._flip = Tween(self, self.update, QEasingCurve.Type.InOutSine)
        self._hover = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        self._shake = Tween(self, self.update, QEasingCurve.Type.Linear)
        self._scan = Tween(self, self.update, QEasingCurve.Type.Linear)
        self._type = Tween(self, self.update, QEasingCurve.Type.Linear)   # gõ chữ clue sau khi lật
        self._type.finished.connect(self._on_type_done)
        self._type_busy, self._type_token = False, 0
        self._phase = (sum(map(ord, cell)) * 37 % 100) / 100.0    # lệch pha animation giữa các thẻ
        self._sparks: List[Tuple[float, float, float]] = []
        self._spark = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        self._front_cache: Optional[QPixmap] = None
        self._front_key: tuple = ()
        clock().tick.connect(self._on_tick)
        self.setMouseTracking(True)
        self.setMinimumSize(128, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ---- API cho GUI -------------------------------------------------------------
    def set_identity(self, name: str, profession: str) -> None:
        self.name, self.profession = name, profession
        self.update()

    def set_face_down(self) -> None:
        self.status, self.clue_text = None, ""
        self._spark.jump(0.0)
        self._sparks = []
        self._type_token += 1
        self._type_busy = False
        self._type.jump(0.0)
        self._flip.jump(0.0)

    def set_face_up(self, status: str, clue_text: str, animate: bool) -> None:
        self.status, self.clue_text = status, clue_text
        if animate:
            self._flip.jump(0.0)
            self._flip.go(1.0, 1100)
            self._type.jump(0.0)
            self._type_token += 1
            self._type_busy = True
            token = self._type_token
            QTimer.singleShot(720, lambda: self._start_typing(token))   # sau khi mặt ngửa hiện ra
            QTimer.singleShot(150, lambda: self._burst(token))          # niêm phong nứt thì bắn hạt sáng
        else:
            if self._flip.now < 1.0 and self._flip.state() != QVariantAnimation.State.Running:
                self._flip.jump(1.0)
            if not self._type_busy:
                self._type.jump(1.0)

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def _burst(self, token: int) -> None:
        """Bắn 8 hạt sáng bung ra quanh con dấu sáp khi thẻ vừa lật."""
        if token != self._type_token or self.status is None:
            return
        self._sparks = [(random.uniform(0, 2 * math.pi), random.uniform(0.22, 0.6), random.uniform(2.5, 5.0))
                        for _ in range(8)]
        self._spark.jump(0.0)
        self._spark.go(1.0, 900)

    def _paint_sparks(self, p: QPainter, r: QRectF, u: float) -> None:
        k = self._spark.now
        origin = QPointF(r.center().x(), r.top() + r.height() * 0.66)
        fade = max(0.0, 1.0 - k)
        p.save()
        p.setPen(NO_PEN)
        for angle, dist, size in self._sparks:
            pos = origin + QPointF(math.cos(angle), math.sin(angle) * 0.85 - 0.2 * k) * (dist * u * k)
            s = size * (1.0 - 0.5 * k) * max(1.0, u / 150.0)
            p.setBrush(QColor(255, 214, 80, int(70 * fade)))
            p.drawEllipse(pos, s * 1.9, s * 1.9)
            p.setBrush(QColor(255, 236, 150, int(255 * fade)))
            p.drawPolygon(icons.star_polygon(pos.x(), pos.y(), s, s * 0.4, 4))
        p.restore()

    def _start_typing(self, token: int) -> None:
        if token == self._type_token and self.status is not None:
            self._type.go(1.0, max(500, min(2000, len(self.clue_text) * 24)))

    def _on_type_done(self) -> None:
        self._type_busy = False
        self.update()

    def set_highlight(self, mode: str) -> None:
        """mode: '' | 'target' (laser + kính định vị) | 'source' (chủ của clue)."""
        self._mode = mode
        self._sync_scan()

    def set_hint(self, on: bool) -> None:
        self._hint = on
        self._sync_scan()

    def set_input_enabled(self, enabled: bool) -> None:
        self._input = enabled
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        if not enabled:
            self._hover.go(0.0, 120)

    def shake(self) -> None:
        self._shake.jump(0.0)
        self._shake.go(1.0, 480)

    def _sync_scan(self) -> None:
        if self._mode or self._hint:
            self._scan.loop(1600)
        else:
            self._scan.stop_loop()
        self.update()

    # ---- sự kiện -----------------------------------------------------------------
    def enterEvent(self, event) -> None:
        if self._input:
            self._hover.go(1.0, 160)

    def leaveEvent(self, event) -> None:
        self._hover.go(0.0, 200)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cell)

    # ---- vẽ ----------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        margin = 7.0
        base = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)
        unit = min(base.width(), base.height() * 0.78)
        lift = -5.0 * self._hover.now
        dx = math.sin(self._shake.now * math.pi * 7) * 8 * (1 - self._shake.now)
        card = base.translated(dx, lift)
        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawRoundedRect(card.translated(3, 6 - lift * 0.4), 12, 12)

        t = self._flip.now
        face_up = self.status is not None
        seal = min(1.0, t / 0.25) if face_up else 0.0
        phase = max(0.0, (t - 0.25) / 0.75) if face_up else 0.0
        front = face_up and phase >= 0.5
        scale_x = abs(math.cos(math.pi * phase)) if face_up else 1.0
        scale_x = max(scale_x, 0.02)
        p.save()
        center = card.center()
        p.translate(center)
        p.scale(scale_x, 1.0)
        p.translate(-center.x(), -center.y())
        if front:
            self._paint_front(p, card, unit)
        else:
            self._paint_back(p, card, unit, seal)
        p.restore()
        if self._sparks and self._spark.state() == QVariantAnimation.State.Running:
            self._paint_sparks(p, card, unit)
        self._paint_highlight(p, card, unit)
