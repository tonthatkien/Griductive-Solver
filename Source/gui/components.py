"""UI components tái sử dụng. (Scope F)

CardView, GridView, GadgetButton, RadialMenu, ConanWidget/ConanToast, EffectOverlay,
NotebookPanel, ClueListView, NightBackdrop. Không chứa luật chơi hay suy luận.
Enum viết đầy đủ (Qt.AlignmentFlag.X) để đổi sang PyQt6 chỉ cần sửa dòng import.
"""
import html
import math
import random
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import (QEasingCurve, QObject, QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt,
                            QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap, QPolygonF, QRadialGradient, QTextLayout, QTextOption)
from PySide6.QtWidgets import (QAbstractButton, QFrame, QGridLayout, QLabel, QListWidget,
                               QListWidgetItem, QSizePolicy, QStyledItemDelegate, QTextBrowser, QVBoxLayout,
                               QWidget)

from engine import board
from gui import icons, theme
from gui.clue_text import STATUS_VN
from gui.icons import NO_BRUSH, NO_PEN, pen

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "characters"


def flags(*items) -> int:
    value = 0
    for item in items:
        value |= int(item.value)
    return value


A = Qt.AlignmentFlag
ALIGN_CENTER = flags(A.AlignCenter)
ALIGN_LEFT_MID = flags(A.AlignLeft, A.AlignVCenter)
WRAP_TOP = flags(A.AlignLeft, A.AlignTop, Qt.TextFlag.TextWordWrap)
WRAP_CENTER = flags(A.AlignCenter, Qt.TextFlag.TextWordWrap)


# Màu nhấn của thẻ đã lật: đỏ neon = CRIMINAL, xanh dương sáng = INNOCENT (dễ phân biệt trên nền tối).
_ACCENTS = {"CRIMINAL": "#ff3b4e", "INNOCENT": "#4aa8ff"}


def draw_brackets(p: QPainter, rect: QRectF, color, size: float, width: float = 2.0) -> None:
    """Bốn góc ngắm hình chữ L quanh một khung (kiểu kính định vị / màn hình quét)."""
    p.save()
    p.setBrush(NO_BRUSH)
    p.setPen(pen(color, width))
    for cx, cy, sx, sy in ((rect.left(), rect.top(), 1, 1), (rect.right(), rect.top(), -1, 1),
                           (rect.left(), rect.bottom(), 1, -1), (rect.right(), rect.bottom(), -1, -1)):
        p.drawLine(QPointF(cx, cy), QPointF(cx + size * sx, cy))
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy + size * sy))
    p.restore()


def make_font(family: str, px: int, bold: bool = False, italic: bool = False,
              spacing: float = 0.0) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(6, int(px)))
    font.setBold(bold)
    font.setItalic(italic)
    if spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


_FIT_PX: Dict[tuple, int] = {}
_FIT_LINES: Dict[tuple, tuple] = {}


def draw_fitted(p: QPainter, rect: QRectF, text: str, family: str, max_px: int, min_px: int,
                color, bold: bool = False, italic: bool = False, fl: int = WRAP_TOP) -> None:
    """Vẽ text, tự giảm cỡ chữ đến khi vừa khung (kết quả được nhớ để khỏi tính lại mỗi khung hình)."""
    key = (text, family, int(max_px), min_px, bold, italic, fl, int(rect.width()), int(rect.height()))
    px = _FIT_PX.get(key)
    if px is None:
        px = max(int(max_px), min_px)
        while True:
            p.setFont(make_font(family, px, bold, italic))
            box = p.boundingRect(rect, fl, text)
            if px <= min_px or (box.height() <= rect.height() + 0.5 and box.width() <= rect.width() + 0.5):
                break
            px -= 1
        if len(_FIT_PX) > 800:
            _FIT_PX.clear()
        _FIT_PX[key] = px
    p.setFont(make_font(family, px, bold, italic))
    p.setPen(QColor(color))
    p.drawText(rect, fl, text)


def _span(style: str, text: str) -> str:
    return f'<span style="{style}">{text}</span>'


def _layout_lines(font: QFont, text: str, width: float):
    """Xếp chữ theo chiều rộng: [(vị trí đầu, độ dài, y, bề rộng, ascent)], tổng chiều cao."""
    layout = QTextLayout(text, font)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(option)
    lines, y = [], 0.0
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max(1.0, width))
        line.setPosition(QPointF(0.0, y))
        lines.append((line.textStart(), line.textLength(), y, line.naturalTextWidth(), line.ascent()))
        y += line.height()
    layout.endLayout()
    return lines, y


def draw_typed(p: QPainter, rect: QRectF, text: str, shown: int, family: str, max_px: int,
               min_px: int, color, bold: bool = False, italic: bool = False,
               center: bool = False, cursor: bool = False) -> None:
    """Vẽ `shown` ký tự đầu của text. Cỡ chữ và chỗ xuống dòng tính trên TOÀN BỘ text nên chữ
    không nhảy dòng hay đổi cỡ khi đang gõ. cursor=True vẽ con trỏ gạch dưới kiểu terminal."""
    text = text.replace("\n", "\u2028")
    key = (text, family, int(max_px), min_px, bold, italic, int(rect.width()), int(rect.height()))
    cached = _FIT_LINES.get(key)
    if cached is None:
        px = max(int(max_px), min_px)
        while True:
            lines, height = _layout_lines(make_font(family, px, bold, italic), text, rect.width()) \
                if text else ([], 0.0)
            if px <= min_px or height <= rect.height() + 0.5:
                break
            px -= 1
        if len(_FIT_LINES) > 400:
            _FIT_LINES.clear()
        cached = _FIT_LINES[key] = (px, lines, height)
    px, lines, height = cached
    font = make_font(family, px, bold, italic)
    p.save()
    p.setFont(font)
    p.setPen(QColor(color))
    metrics = QFontMetricsF(font)
    top = rect.top() + ((rect.height() - height) / 2 if center else 0.0)
    cursor_at = QPointF(rect.left(), top + metrics.ascent())
    for start, length, y, line_width, ascent in lines:
        visible = min(length, max(0, shown - start))
        if visible <= 0:
            continue
        chunk = text[start:start + visible]
        x = rect.left() + ((rect.width() - line_width) / 2 if center else 0.0)
        base = top + y + ascent
        p.drawText(QPointF(x, base), chunk)
        cursor_at = QPointF(x + metrics.horizontalAdvance(chunk), base)
    if cursor:
        p.fillRect(QRectF(cursor_at.x() + px * 0.1, cursor_at.y() + 1, px * 0.55, max(2.0, px * 0.11)),
                   QColor(color))
    p.restore()


def draw_neon_text(p: QPainter, rect: QRectF, text: str, font: QFont, color, glow, strength: float = 1.0,
                   fl: int = ALIGN_CENTER, alpha: int = 255) -> None:
    """Chữ neon: vài vòng bóng mờ quanh chữ (màu glow) rồi lõi sáng (màu color)."""
    p.save()
    p.setFont(font)
    for radius, base_alpha in ((6, 10), (4, 20), (2, 40)):
        tint = QColor(glow)
        tint.setAlpha(int(base_alpha * strength * alpha / 255))
        p.setPen(tint)
        for k in range(12):
            angle = 2 * math.pi * k / 12
            p.drawText(rect.translated(math.cos(angle) * radius, math.sin(angle) * radius), fl, text)
    core = QColor(color)
    core.setAlpha(alpha)
    p.setPen(core)
    p.drawText(rect, fl, text)
    p.restore()


class Tween(QVariantAnimation):
    """Giá trị 0..1 chạy mượt, gọi callback mỗi khung hình (dùng cho hover, lật thẻ, quét...)."""

    def __init__(self, owner, on_change: Callable[[], None],
                 easing: QEasingCurve.Type = QEasingCurve.Type.InOutSine) -> None:
        super().__init__(owner)
        self.now = 0.0
        self._on_change = on_change
        self.setEasingCurve(easing)
        self.valueChanged.connect(self._changed)

    def _changed(self, value) -> None:
        self.now = float(value)
        self._on_change()

    def go(self, target: float, ms: int = 160) -> None:
        self.stop()
        self.setLoopCount(1)
        self.setStartValue(self.now)
        self.setEndValue(float(target))
        self.setDuration(ms)
        self.start()

    def jump(self, value: float) -> None:
        self.stop()
        self.now = float(value)
        self._on_change()

    def loop(self, ms: int) -> None:
        if self.state() == QVariantAnimation.State.Running and self.loopCount() == -1:
            return
        self.stop()
        self.setStartValue(0.0)
        self.setEndValue(1.0)
        self.setDuration(ms)
        self.setLoopCount(-1)
        self.start()

    def stop_loop(self) -> None:
        self.stop()
        self.setLoopCount(1)
        self.jump(0.0)


class Typer(QObject):
    """Gõ chữ từng ký tự (~25 ms/ký tự, tối đa ~1.6 s mỗi câu) + con trỏ nhấp nháy kiểu terminal."""

    changed = Signal()
    typed = Signal()            # phát mỗi 2 ký tự để phát tiếng gõ

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.text, self.shown, self._blink_on = "", 0, True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        blink = QTimer(self)
        blink.timeout.connect(self._toggle)
        blink.start(450)

    def start(self, text: str) -> None:
        self.text, self.shown = text, 0
        if text:
            self._timer.start(max(8, min(28, 1600 // len(text))))
        else:
            self._timer.stop()
        self.changed.emit()

    @property
    def typing(self) -> bool:
        return self._timer.isActive()

    @property
    def cursor_visible(self) -> bool:
        return self.typing or self._blink_on

    def _step(self) -> None:
        self.shown += 1
        if self.shown % 2 == 0:
            self.typed.emit()
        if self.shown >= len(self.text):
            self._timer.stop()
        self.changed.emit()

    def _toggle(self) -> None:
        self._blink_on = not self._blink_on
        if not self.typing:
            self.changed.emit()


IDLE_FPS = 20                 # tốc độ khung hình của animation nền; giảm nếu máy yếu


class Clock(QObject):
    """Đồng hồ chung: MỘT QTimer cho mọi animation nền (nhịp thở, scanline, LED, tia laser...)."""

    tick = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.t = time.perf_counter()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(1000 // IDLE_FPS)

    def _on_timeout(self) -> None:
        self.t = time.perf_counter()
        self.tick.emit()


_CLOCK: Optional[Clock] = None


def clock() -> Clock:
    global _CLOCK
    if _CLOCK is None:
        _CLOCK = Clock()
    return _CLOCK


_PIXMAPS: Dict[str, Optional[QPixmap]] = {}


def character_pixmap(name: str) -> Optional[QPixmap]:
    """Ảnh thật của nhân vật nếu có gui/assets/characters/<tên-thường>.png."""
    if name not in _PIXMAPS:
        path = ASSET_DIR / f"{name.lower().replace(' ', '_')}.png"
        _PIXMAPS[name] = QPixmap(str(path)) if path.exists() else None
    return _PIXMAPS[name]


# --------------------------------------------------------------------------------------
# Thẻ hồ sơ
# --------------------------------------------------------------------------------------
class CardView(QWidget):
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
        p.setFont(make_font(theme.FONT_GADGET, u * 0.068, True, spacing=1.5))
        p.drawText(strip.adjusted(u * 0.07, 0, 0, 0), ALIGN_LEFT_MID, "HỒ SƠ MẬT")
        p.setPen(QColor(theme.GOLD))
        p.setFont(make_font(theme.FONT_MONO, u * 0.1, True))
        p.drawText(strip.adjusted(0, 0, -u * 0.07, 0), flags(A.AlignRight, A.AlignVCenter), self.cell)
        plate = QRectF(r.left(), r.bottom() - u * 0.32, r.width(), u * 0.32)
        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 0, 0, 150))
        p.drawRect(plate)
        draw_fitted(p, QRectF(plate.left() + u * 0.05, plate.top() + u * 0.02, plate.width() - u * 0.1,
                              u * 0.18), self.name, theme.FONT_TITLE, int(u * 0.13), 9, theme.GOLD_SOFT,
                    bold=True, fl=ALIGN_CENTER)
        draw_fitted(p, QRectF(plate.left() + u * 0.05, plate.top() + u * 0.2, plate.width() - u * 0.1,
                              u * 0.11), self.profession, theme.FONT_DOSSIER, int(u * 0.088), 8, "#b9c6e6",
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
        entry = CardView._GLOW_CACHE.get(px)
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
            CardView._GLOW_CACHE[px] = entry
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

    def _front_rects(self, r: QRectF, u: float):
        pad = u * 0.07
        header = QRectF(r.left(), r.top(), r.width(), u * 0.15)
        pw = u * 0.36
        portrait = QRectF(r.left() + pad, header.bottom() + pad * 0.9, pw, pw * 1.08)
        plate = QRectF(r.left() + pad, portrait.bottom() + pad * 0.9, r.width() - 2 * pad, u * 0.19)
        top = plate.bottom() + pad * 0.7
        clue_box = QRectF(r.left() + pad, top, r.width() - 2 * pad, r.bottom() - pad - top)
        return pad, header, portrait, plate, clue_box

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
        """Mặt ngửa: lớp tĩnh (cache) + vệt quét CRT chạy từ trên xuống + chữ manh mối đang gõ."""
        p.drawPixmap(QPointF(r.left() - 8, r.top() - 8), self._front_base(r, u))
        _pad, _header, _portrait, _plate, clue_box = self._front_rects(r, u)
        path = QPainterPath()
        path.addRoundedRect(r, 12, 12)
        p.save()
        p.setClipPath(path)
        band = u * 0.2
        y = r.top() - band + (r.height() + band) * ((clock().t * 0.22 + self._phase) % 1.0)
        sweep = QLinearGradient(0, y, 0, y + band)
        sweep.setColorAt(0, QColor(56, 242, 255, 0))
        sweep.setColorAt(0.7, QColor(56, 242, 255, 34))
        sweep.setColorAt(1, QColor(160, 250, 255, 80))
        p.fillRect(QRectF(r.left(), y, r.width(), band), QBrush(sweep))
        p.restore()
        pad = u * 0.07
        count = int(self._type.now * len(self.clue_text) + 0.5)
        draw_typed(p, clue_box.adjusted(pad * 0.9, u * 0.085, -pad * 0.6, -pad * 0.25), self.clue_text,
                   count, theme.FONT_MONO, int(u * 0.1), 8, "#d6f3ff",
                   cursor=self._type_busy and 0 < count < len(self.clue_text))

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

        pad, header, portrait, plate, clue_box = self._front_rects(r, u)
        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRect(header)
        p.setPen(pen(accent, 1.5))
        p.drawLine(QPointF(r.left(), header.bottom()), QPointF(r.right(), header.bottom()))
        p.setPen(accent)
        p.setFont(make_font(theme.FONT_MONO, u * 0.07, True, spacing=1))
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

        tx = portrait.right() + pad
        tw = r.right() - pad - tx
        draw_fitted(p, QRectF(tx, portrait.top() - 2, tw, u * 0.17), self.name, theme.FONT_MONO,
                    int(u * 0.13), 9, "#eaf6ff", bold=True, fl=ALIGN_LEFT_MID)
        draw_fitted(p, QRectF(tx, portrait.top() + u * 0.18, tw, u * 0.22), self.profession.upper(),
                    theme.FONT_MONO, int(u * 0.082), 8, "#7fdcff", fl=WRAP_TOP)
        self._paint_stamp(p, plate, u)

        p.setPen(NO_PEN)
        p.setBrush(QColor(0, 12, 26, 175))
        p.drawRoundedRect(clue_box, 6, 6)
        p.setBrush(accent)
        p.drawRect(QRectF(clue_box.left(), clue_box.top() + 5, 3, clue_box.height() - 10))
        p.setPen(accent)
        p.setFont(make_font(theme.FONT_GADGET, u * 0.056, True, spacing=1.2))
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
                    "CRIMINAL" if criminal else "INNOCENT", theme.FONT_GADGET, int(u * 0.1), 8,
                    accent.lighter(135), bold=True, fl=ALIGN_CENTER)
        p.restore()

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
        if self._hint:
            self._paint_hint(p, r, u, t)

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


class GridView(QWidget):
    """Lưới N×N + nhãn tọa độ (A, B, C... / 1, 2, 3...)."""

    cardClicked = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.cards: Dict[str, CardView] = {}
        self._layout = QGridLayout(self)
        self._layout.setSpacing(12)
        self._layout.setContentsMargins(6, 6, 6, 6)

    def set_board(self, n: int, info: Dict[str, Tuple[str, str]]) -> None:
        """info: cell -> (name, profession)."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()
        self.cards = {}
        for c in range(n):
            self._layout.addWidget(self._coord(board.COLS[c], height=24), 0, c + 1)
        for r in range(n):
            self._layout.addWidget(self._coord(str(r + 1), width=26), r + 1, 0)
            for c in range(n):
                cell = board.cell_id(r, c)
                card = CardView(cell)
                card.set_identity(*info[cell])
                card.clicked.connect(self.cardClicked)
                self._layout.addWidget(card, r + 1, c + 1)
                self.cards[cell] = card
        for i in range(1, n + 1):
            self._layout.setRowStretch(i, 1)
            self._layout.setColumnStretch(i, 1)

    @staticmethod
    def _coord(text: str, width: int = 0, height: int = 0) -> QLabel:
        label = QLabel(text)
        label.setObjectName("coord")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if width:
            label.setFixedWidth(width)
        if height:
            label.setFixedHeight(height)
        return label

    def set_input_enabled(self, enabled: bool) -> None:
        for card in self.cards.values():
            card.set_input_enabled(enabled)


# --------------------------------------------------------------------------------------
# Bảo bối (nút điều khiển)
# --------------------------------------------------------------------------------------
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


# --------------------------------------------------------------------------------------
# Radial menu
# --------------------------------------------------------------------------------------
class RadialMenu(QWidget):
    """Vòng chọn verdict hiện quanh thẻ: còng tay (CRIMINAL) / huy hiệu (INNOCENT)."""

    chosen = Signal(str, str)      # cell, verdict
    closed = Signal()
    BTN_RADIUS = 42.0

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._cell, self._name, self._anchor = "", "", QPointF()
        self._hover = -1
        self._open = Tween(self, self.update, QEasingCurve.Type.OutBack)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

    def open_at(self, cell: str, name: str, anchor: QPointF) -> None:
        self._cell, self._name, self._anchor, self._hover = cell, name, anchor, -1
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.setFocus()
        self._open.jump(0.0)
        self._open.go(1.0, 320)

    def close_menu(self) -> None:
        if self.isVisible():
            self.hide()
            self.closed.emit()

    def _layout(self) -> Tuple[QPointF, float, List[Tuple[str, QPointF]]]:
        k = self._open.now
        reach = 96.0 * k
        margin = 96.0 + self.BTN_RADIUS + 24
        x = min(max(self._anchor.x(), margin), max(margin, self.width() - margin))
        y = min(max(self._anchor.y(), self.BTN_RADIUS + 50), max(self.BTN_RADIUS + 50, self.height() - 90))
        center = QPointF(x, y)
        return center, reach, [("CRIMINAL", QPointF(x - reach, y)), ("INNOCENT", QPointF(x + reach, y))]

    def _hit(self, pos: QPointF) -> int:
        _, _, buttons = self._layout()
        for i, (_, c) in enumerate(buttons):
            if math.hypot(pos.x() - c.x(), pos.y() - c.y()) <= self.BTN_RADIUS * 1.1:
                return i
        return -1

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        k = min(1.0, self._open.now)
        p.fillRect(self.rect(), QColor(2, 6, 16, int(165 * k)))
        center, reach, buttons = self._layout()
        p.setOpacity(min(1.0, k * 1.5))
        p.setBrush(NO_BRUSH)
        for width, alpha in ((10, 25), (3, 150)):
            p.setPen(pen(QColor(226, 185, 71, alpha), width))
            p.drawEllipse(center, reach, reach)
        p.setBrush(QColor(8, 14, 30, 235))
        p.setPen(pen(theme.GOLD, 2))
        p.drawEllipse(center, 36, 36)
        p.setPen(QColor(theme.GOLD_SOFT))
        p.setFont(make_font(theme.FONT_MONO, 18, True))
        p.drawText(QRectF(center.x() - 36, center.y() - 20, 72, 24), ALIGN_CENTER, self._cell)
        p.setFont(make_font(theme.FONT_DOSSIER, 11, False, True))
        p.setPen(QColor("#cdd7f0"))
        p.drawText(QRectF(center.x() - 36, center.y() + 2, 72, 18), ALIGN_CENTER, self._name)
        specs = {"CRIMINAL": ("#ff3b4e", "#7a0f1d", icons.draw_handcuffs, "CRIMINAL", "Còng tay"),
                 "INNOCENT": ("#3b8bff", "#123a7a", icons.draw_badge, "INNOCENT", "Huy hiệu")}
        for i, (verdict, c) in enumerate(buttons):
            rim, fill, painter_fn, title, sub = specs[verdict]
            rad = self.BTN_RADIUS * (1.14 if i == self._hover else 1.0)
            if i == self._hover:
                glow = QColor(rim)
                for width, alpha in ((18, 40), (10, 80)):
                    glow.setAlpha(alpha)
                    p.setPen(pen(glow, width))
                    p.setBrush(NO_BRUSH)
                    p.drawEllipse(c, rad, rad)
            body = QRadialGradient(QPointF(c.x(), c.y() - rad * 0.4), rad * 1.6)
            body.setColorAt(0, QColor(fill).lighter(160))
            body.setColorAt(1, QColor(fill).darker(220))
            p.setBrush(QBrush(body))
            p.setPen(pen(rim, 3))
            p.drawEllipse(c, rad, rad)
            painter_fn(p, QRectF(c.x() - rad * 0.62, c.y() - rad * 0.62, rad * 1.24, rad * 1.24))
            p.setPen(QColor(rim).lighter(135))
            p.setFont(make_font(theme.FONT_GADGET, 12, True, spacing=1))
            p.drawText(QRectF(c.x() - 70, c.y() + rad + 4, 140, 18), ALIGN_CENTER, title)
            p.setPen(QColor("#9fb0d8"))
            p.setFont(make_font(theme.FONT_DOSSIER, 11, False, True))
            p.drawText(QRectF(c.x() - 70, c.y() + rad + 22, 140, 16), ALIGN_CENTER, sub)

    def mouseMoveEvent(self, event) -> None:
        hover = self._hit(event.position())
        if hover != self._hover:
            self._hover = hover
            self.setCursor(Qt.CursorShape.PointingHandCursor if hover >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()

    def mousePressEvent(self, event) -> None:
        index = self._hit(event.position())
        if index >= 0 and event.button() == Qt.MouseButton.LeftButton:
            verdict = self._layout()[2][index][0]
            self.hide()
            self.chosen.emit(self._cell, verdict)
        else:
            self.close_menu()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()


# --------------------------------------------------------------------------------------
# Conan + bong bóng thoại
# --------------------------------------------------------------------------------------
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
        return QPoint(parent.width() - self.width() - 24, parent.height() - self.height() - 150)

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


# --------------------------------------------------------------------------------------
# Hiệu ứng toàn màn hình
# --------------------------------------------------------------------------------------
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
                       make_font(theme.FONT_TITLE, h * 0.07, True, spacing=5),
                       "#ff6b78", theme.RED_NEON, 1.0, ALIGN_CENTER, alpha)
        p.setFont(make_font(theme.FONT_DOSSIER, h * 0.03, False, True))
        p.setPen(QColor(255, 255, 255, alpha))
        p.drawText(QRectF(0, h * 0.2, w, h * 0.05), ALIGN_CENTER, "Kết luận ngược lại mới là hệ quả bắt buộc.")

    def _paint_victory(self, p: QPainter, t: float) -> None:
        w, h = float(self.width()), float(self.height())
        p.fillRect(self.rect(), QColor(4, 10, 28, int(220 * min(1.0, t * 3))))
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
        font = make_font(theme.FONT_TITLE, px, True, spacing=6)
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


# --------------------------------------------------------------------------------------
# Sổ tay + danh sách clue
# --------------------------------------------------------------------------------------
class NotebookPanel(QFrame):
    """Sổ tay phá án: thống kê realtime + log từng bước suy luận dạng thẻ dịu mắt."""

    _CHIPS = (("steps", "BƯỚC"), ("sat", "SAT CALLS"), ("ms", "DPLL (ms)"))

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("notebookCover")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(NeonTitle("SỔ TAY PHÁ ÁN", px=15, spacing=3.0, gadget=True, core="#dce8ff"),
                         0, Qt.AlignmentFlag.AlignHCenter)
        grid = QGridLayout()
        grid.setSpacing(8)
        self._chips: Dict[str, QLabel] = {}
        for i, (key, caption) in enumerate(self._CHIPS):
            chip = QLabel()
            chip.setObjectName("statchip")
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setTextFormat(Qt.TextFormat.RichText)
            self._chips[key] = chip
            grid.addWidget(chip, i // 3, i % 3)
        layout.addLayout(grid)
        self.view = QTextBrowser()
        self.view.setObjectName("notebook")
        self.view.setOpenLinks(False)
        layout.addWidget(self.view, 1)
        self._targets = {"steps": 0.0, "sat": 0.0, "ms": 0.0}
        self._from = dict(self._targets)
        self._shown = dict(self._targets)
        self._count = Tween(self, self._on_count, QEasingCurve.Type.OutCubic)
        self._render_stats()

    def set_stats(self, steps: int, sat: int, dec: int, prop: int, back: int, ms: float) -> None:
        """Số chạy lướt từ giá trị cũ lên giá trị mới."""
        new = {"steps": float(steps), "sat": float(sat), "ms": float(ms)}
        if new == self._targets:
            return
        self._from, self._targets = dict(self._shown), new
        self._count.jump(0.0)
        self._count.go(1.0, 600)

    def _on_count(self) -> None:
        k = self._count.now
        for key, target in self._targets.items():
            self._shown[key] = self._from[key] + (target - self._from[key]) * k
        self._render_stats()

    def _render_stats(self) -> None:
        texts = {"steps": str(round(self._shown["steps"])), "sat": str(round(self._shown["sat"])),
                 "ms": f"{self._shown['ms']:.1f}"}
        for key, caption in self._CHIPS:
            self._chips[key].setText(
                f"<div style='font-size:17px;font-weight:bold;color:#f2f6ff'>{texts[key]}</div>"
                f"<div style='font-size:9px;letter-spacing:0.8px;color:#8aa4d6;margin-top:2px'>{caption}</div>")

    def reset(self) -> None:
        self.view.clear()
        self._count.stop()
        zero = {"steps": 0.0, "sat": 0.0, "ms": 0.0}
        self._targets, self._from, self._shown = dict(zero), dict(zero), dict(zero)
        self._render_stats()

    def _append(self, body: str) -> None:
        self.view.append(body)
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    _NOTE_TONES = {
        "#7a5a1a": ("#e5b95c", "#1c1a17"),   # NOT_PROVABLE / STUCK: chữ vàng ấm trên nền tối dịu
        "#a3121f": ("#f27983", "#21131b"),   # CONTRADICTED / INCONSISTENT: chữ đỏ san hô dịu
    }

    def add_note(self, text: str, color: str = "#8ea2c8") -> None:
        fg, bg = self._NOTE_TONES.get(color, (color, "#131c30"))
        self._append(
            f"<table width='100%' cellspacing='0' cellpadding='7' style='margin:4px 0'>"
            f"<tr><td bgcolor='{bg}' style='border-left:3px solid {fg};color:{fg};font-size:12px'>"
            f"{html.escape(text)}</td></tr></table>"
        )

    def add_entry(self, step: int, who: str, cell_label: str, cell: str, verdict: str,
                  queries: List[Tuple[str, str]], active: int, clue_text: str, ms: float,
                  note: str = "") -> None:
        """Mỗi bước hiển thị thành 1 thẻ log tách bạch, dễ quét."""
        is_criminal = verdict == "CRIMINAL"
        accent = "#f26d7d" if is_criminal else "#63a4ff"
        badge_bg = "#331722" if is_criminal else "#142847"
        mono = f"font-family:\"{theme.FONT_MONO}\",Consolas,monospace;font-size:12px;color:#9fb4db"
        extra = "(tóm tắt)" if "tóm tắt" in note else note

        header = (
            _span("color:#7cc4fa;font-weight:bold;font-size:11px", f"BƯỚC {step:02d}")
            + _span("color:#7f93ba;font-size:11px", f" · {html.escape(who)}")
        )
        verdict_line = (
            f"<span style='color:#f0f4fc;font-weight:bold;font-size:13px'>{html.escape(cell_label)}</span> "
            f"<span style='background-color:{badge_bg};color:{accent};font-weight:bold;font-size:11px'>"
            f"&nbsp;{STATUS_VN[verdict].upper()}&nbsp;</span>"
        )

        rows = [header, verdict_line]
        if queries:
            for i, (query, result) in enumerate(queries):
                tail = (f" <span style='color:#7f93ba;font-size:11px'>{html.escape(extra)}</span>"
                        if extra and i == len(queries) - 1 else "")
                rows.append(
                    f"<span style='{mono}'>{html.escape(query)} → "
                    f"<b style='color:#dce8ff'>{html.escape(result)}</b></span>{tail}"
                )
        elif extra:
            rows.append(f"<span style='{mono}'>{html.escape(extra)}</span>")

        if clue_text:
            rows.append(
                f"<span style='color:#cfd9ec;font-size:12.5px'>"
                f"<b style='color:#8aa4d6'>Manh mối:</b> {html.escape(clue_text)}</span>"
            )

        content = "<br/>".join(rows)
        self._append(
            f"<table width='100%' cellspacing='0' cellpadding='8' style='margin:5px 0'>"
            f"<tr><td bgcolor='#131e36' style='border-left:3px solid {accent};line-height:140%'>"
            f"{content}</td></tr></table>"
        )


class _ClueDelegate(QStyledItemDelegate):
    """Vẽ item như mặc định rồi phủ vệt sáng vàng quét qua clue vừa lộ (1 giây)."""

    def __init__(self, view: "ClueListView") -> None:
        super().__init__(view)
        self._view = view

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        started = self._view.fresh.get(index.data(Qt.ItemDataRole.UserRole))
        if started is None:
            return
        k = (time.perf_counter() - started) / ClueListView.SWEEP_SECONDS
        if k >= 1.0:
            return
        rect = QRectF(option.rect)
        x = rect.left() - rect.width() * 0.2 + rect.width() * 1.4 * k
        band = rect.width() * 0.18
        sweep = QLinearGradient(x - band, 0, x + band, 0)
        sweep.setColorAt(0.0, QColor(255, 214, 80, 0))
        sweep.setColorAt(0.5, QColor(255, 232, 120, 190))
        sweep.setColorAt(1.0, QColor(255, 214, 80, 0))
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QBrush(sweep))
        painter.restore()


class ClueListView(QListWidget):
    """Danh sách clue đã mở; bấm vào một dòng để highlight các ô clue nhắc tới.
    Clue mới thêm vào được vệt sáng vàng lướt qua để thu hút ánh nhìn."""

    clueSelected = Signal(str)
    SWEEP_SECONDS = 1.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("cluelist")
        self.setWordWrap(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.fresh: Dict[str, float] = {}
        self._known: Optional[set] = None
        self.setItemDelegate(_ClueDelegate(self))
        self.itemClicked.connect(lambda item: self.clueSelected.emit(item.data(Qt.ItemDataRole.UserRole)))
        clock().tick.connect(self._on_tick)

    def _on_tick(self) -> None:
        if not self.fresh:
            return
        now = time.perf_counter()
        self.fresh = {k: v for k, v in self.fresh.items() if now - v < self.SWEEP_SECONDS}
        self.viewport().update()

    def set_clues(self, items: List[Tuple[str, str]]) -> None:
        """items: (clue_id, text) theo thứ tự lật."""
        current = self.currentItem().data(Qt.ItemDataRole.UserRole) if self.currentItem() else None
        ids = [clue_id for clue_id, _text in items]
        if self._known is not None:                  # lần nạp đầu không quét; sau đó clue nào mới thì quét
            now = time.perf_counter()
            for clue_id in ids:
                if clue_id not in self._known:
                    self.fresh[clue_id] = now
        self._known = set(ids)
        self.blockSignals(True)
        self.clear()
        for clue_id, text in items:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, clue_id)
            self.addItem(item)
            if clue_id == current:
                self.setCurrentItem(item)
        self.blockSignals(False)
        if self.fresh:
            self.scrollToBottom()

    def select(self, clue_id: str) -> None:
        self.blockSignals(True)
        for i in range(self.count()):
            if self.item(i).data(Qt.ItemDataRole.UserRole) == clue_id:
                self.setCurrentRow(i)
        self.blockSignals(False)

    def clear_selection(self) -> None:
        self.blockSignals(True)
        self.setCurrentRow(-1)
        self.clearSelection()
        self.blockSignals(False)


class BeamOverlay(QWidget):
    """Tia laser nối ô chủ manh mối với các ô được nhắc tới, nhấp nháy, có hạt năng lượng chạy dọc dây.

    Phủ lên toàn bộ vùng giao diện, không nhận chuột. Tọa độ ô lấy qua resolver (cell -> QPointF
    trong hệ tọa độ của widget cha) nên tự theo kịp khi đổi kích thước cửa sổ."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._resolver: Optional[Callable[[str], Optional[QPointF]]] = None
        self._origin, self._targets = "", []
        self._grow = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        clock().tick.connect(self._on_tick)
        self.show()

    def set_resolver(self, resolver: Callable[[str], Optional[QPointF]]) -> None:
        self._resolver = resolver

    def show_links(self, origin: str, targets: List[str]) -> None:
        self._origin, self._targets = origin, [c for c in targets if c != origin]
        self._grow.jump(0.0)
        self._grow.go(1.0, 450)

    def clear(self) -> None:
        self._origin, self._targets = "", []
        self.update()

    def _on_tick(self) -> None:
        if self._targets:
            self.update()

    def paintEvent(self, _event) -> None:
        if not (self._origin and self._targets and self._resolver):
            return
        origin = self._resolver(self._origin)
        if origin is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t, grow = clock().t, self._grow.now
        flicker = 0.85 + 0.15 * math.sin(t * 37)
        for i, cell in enumerate(self._targets):
            target = self._resolver(cell)
            if target is None:
                continue
            end = origin + (target - origin) * grow
            for width, alpha in ((9, 22), (5, 45)):
                glow = QColor(57, 255, 20, int(alpha * flicker))
                p.setPen(pen(glow, width))
                p.drawLine(origin, end)
            core = QPen(QColor(220, 255, 210, int(230 * flicker)), 2)
            core.setDashPattern([3.0, 4.0])
            core.setDashOffset(-t * 18)
            p.setPen(core)
            p.drawLine(origin, end)
            p.setPen(NO_PEN)
            for j in range(3):                                   # hạt năng lượng chạy từ gốc tới đích
                pos = origin + (end - origin) * ((t * 0.55 + j / 3.0 + i * 0.17) % 1.0)
                p.setBrush(QColor(57, 255, 20, 70))
                p.drawEllipse(pos, 7, 7)
                p.setBrush(QColor(235, 255, 225))
                p.drawEllipse(pos, 2.6, 2.6)
            if grow > 0.95:                                      # vòng nhịp ở ô đích
                ring = 9 + 5 * (0.5 + 0.5 * math.sin(t * 6))
                p.setBrush(NO_BRUSH)
                p.setPen(pen(QColor(57, 255, 20, 210), 2))
                p.drawEllipse(target, ring, ring)
        p.setPen(pen(QColor(255, 214, 80, 230), 2))
        p.setBrush(QColor(255, 214, 80, 90))
        p.drawEllipse(origin, 7, 7)


# --------------------------------------------------------------------------------------
# Nền đêm
# --------------------------------------------------------------------------------------
class NightBackdrop(QWidget):
    """Nền thành phố ban đêm: trăng, sao nhấp nháy, nhà cao tầng, vệt đèn pin quét chậm."""

    resized = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        rng = random.Random(11)
        self._stars = [(rng.random(), rng.random() * 0.6, rng.uniform(0, 6.28), rng.uniform(0.6, 2.2))
                       for _ in range(110)]
        self._buildings, x = [], 0.0
        while x < 1.0:
            bw, bh = rng.uniform(0.04, 0.09), rng.uniform(0.07, 0.2)
            lit = [rng.random() < 0.35 for _ in range(30)]
            self._buildings.append((x, bw, bh, lit))
            x += bw + rng.uniform(0.0, 0.01)
        self._t, self._t0 = 0.0, clock().t
        clock().tick.connect(self._tick)

    def _tick(self) -> None:
        self._t = clock().t - self._t0
        if self.isVisible():
            self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.resized.emit()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor(theme.NIGHT_TOP))
        sky.setColorAt(0.65, QColor(theme.NIGHT_MID))
        sky.setColorAt(1, QColor(theme.NIGHT_BOTTOM))
        p.fillRect(self.rect(), QBrush(sky))
        moon = QPointF(w * 0.9, h * 0.13)
        glow = QRadialGradient(moon, min(w, h) * 0.16)
        glow.setColorAt(0, QColor(255, 244, 200, 120))
        glow.setColorAt(1, QColor(255, 244, 200, 0))
        p.fillRect(self.rect(), QBrush(glow))
        p.setPen(NO_PEN)
        p.setBrush(QColor("#fff4cf"))
        p.drawEllipse(moon, min(w, h) * 0.035, min(w, h) * 0.035)
        for sx, sy, phase, speed in self._stars:
            alpha = int(60 + 150 * (0.5 + 0.5 * math.sin(self._t * speed + phase)))
            p.setBrush(QColor(255, 255, 255, alpha))
            p.drawEllipse(QPointF(sx * w, sy * h), 1.2, 1.2)
        angle = math.radians(-62 + 10 * math.sin(self._t * 0.45))
        origin, length, spread = QPointF(w * 0.04, h), h * 1.1, math.radians(9)
        tip1 = origin + QPointF(math.cos(angle - spread), math.sin(angle - spread)) * length
        tip2 = origin + QPointF(math.cos(angle + spread), math.sin(angle + spread)) * length
        beam = QLinearGradient(origin, (tip1 + tip2) / 2)
        beam.setColorAt(0, QColor(255, 255, 235, 46))
        beam.setColorAt(1, QColor(255, 255, 235, 0))
        p.setBrush(QBrush(beam))
        p.drawPolygon(QPolygonF([origin, tip1, tip2]))
        for bx, bw, bh, lit in self._buildings:
            rect = QRectF(bx * w, h - bh * h, bw * w, bh * h)
            p.setBrush(QColor("#060b19"))
            p.drawRect(rect)
            cols, rows = 3, 6
            for i in range(cols * rows):
                if lit[i % len(lit)]:
                    wx = rect.left() + rect.width() * (0.15 + 0.28 * (i % cols))
                    wy = rect.top() + rect.height() * (0.1 + 0.14 * (i // cols))
                    p.setBrush(QColor(242, 193, 78, 150))
                    p.drawRect(QRectF(wx, wy, rect.width() * 0.14, rect.height() * 0.07))


# --------------------------------------------------------------------------------------
# Tiêu đề neon + khung thông báo terminal
# --------------------------------------------------------------------------------------
class NeonTitle(QWidget):
    """Tiêu đề phát sáng: chữ giãn cách, quầng cyan + đỏ nhịp thở, vệt laser quét qua chữ."""

    def __init__(self, text: str, parent: Optional[QWidget] = None, px: int = 26, spacing: float = 5.0,
                 gadget: bool = False, core: str = "#f5e7b8") -> None:
        super().__init__(parent)
        self._text, self._px, self._spacing, self._gadget, self._core = text, px, spacing, gadget, core
        self._glow_cache: Optional[QPixmap] = None
        self._glow_key: tuple = ()
        self._anim = Tween(self, self.update, QEasingCurve.Type.Linear)
        self._anim.loop(3600)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _font(self) -> QFont:
        family = theme.FONT_GADGET if self._gadget else theme.FONT_TITLE
        return make_font(family, self._px, True, spacing=self._spacing)

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self._font())
        return QSize(int(metrics.horizontalAdvance(self._text) + len(self._text) * self._spacing) + 30,
                     int(metrics.height()) + 16)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def _glow_pixmap(self, font: QFont, rect: QRectF) -> QPixmap:
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr, self._text, self._px)
        if self._glow_cache is None or self._glow_key != key:
            pix = QPixmap(int(rect.width() * dpr), int(rect.height() * dpr))
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.GlobalColor.transparent)
            g = QPainter(pix)
            g.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            g.setFont(font)
            for color, offset in ((theme.RED_NEON, QPointF(2, 1)), (theme.CYAN_LASER, QPointF(0, 0))):
                for radius, alpha in ((7, 12), (5, 22), (3, 40), (1.5, 70)):
                    tint = QColor(color)
                    tint.setAlpha(alpha)
                    g.setPen(tint)
                    for k in range(12):
                        angle = 2 * math.pi * k / 12
                        g.drawText(rect.translated(offset + QPointF(math.cos(angle) * radius,
                                                                    math.sin(angle) * radius)),
                                   ALIGN_CENTER, self._text)
            g.end()
            self._glow_cache, self._glow_key = pix, key
        return self._glow_cache

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect, font, t = QRectF(self.rect()), self._font(), self._anim.now
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * t)
        p.setOpacity(0.55 + 0.45 * pulse)
        p.drawPixmap(QPointF(0, 0), self._glow_pixmap(font, rect))
        p.setOpacity(1.0)
        p.setFont(font)
        stops = {0.0: QColor(self._core), 1.0: QColor(self._core)}
        centre = -0.15 + 1.3 * t                       # vệt laser quét từ trái sang phải
        for pos, color in ((centre - 0.1, self._core), (centre, "#ffffff"), (centre + 0.1, self._core)):
            if 0.0 <= pos <= 1.0:
                stops[pos] = QColor(color)
        sweep = QLinearGradient(rect.left(), 0, rect.right(), 0)
        for pos in sorted(stops):
            sweep.setColorAt(pos, stops[pos])
        p.setPen(QPen(QBrush(sweep), 1))
        p.drawText(rect, ALIGN_CENTER, self._text)


class TerminalMessage(QWidget):
    """Khung thông báo kiểu terminal: gõ chữ từng ký tự, viền đổi màu theo kind (info/ok/warn/bad)
    và một đèn LED ở góc trái (xanh nhịp tim = ok, vàng nhấp nháy = warn, đỏ chớp = bad)."""

    _TONES = {"info": ("#2c4170", "#dfe7fb"), "ok": ("#2fae6b", "#b9f5d2"),
              "warn": (theme.GOLD, "#ffe9a6"), "bad": (theme.RED_NEON, "#ffc2c8")}
    _LEDS = {"info": "#4aa8ff", "ok": "#39ff14", "warn": "#ffd166", "bad": "#ff3b4e"}

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._kind = "info"
        self.typer = Typer(self)
        self.typer.changed.connect(self.update)
        self.setMinimumHeight(70)
        clock().tick.connect(self._on_tick)

    def set_message(self, text: str, kind: str = "info") -> None:
        self._kind = kind if kind in self._TONES else "info"
        self.typer.start(text)
        self.update()

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def _led_level(self) -> float:
        t = clock().t
        if self._kind == "bad":
            return 1.0 if int(t * 3) % 2 == 0 else 0.15                         # chớp liên tục
        if self._kind == "warn":
            return 0.4 + 0.6 * (0.5 + 0.5 * math.sin(2 * math.pi * 1.6 * t))    # nhấp nháy
        if self._kind == "ok":
            return 0.35 + 0.65 * max(0.0, math.sin(2 * math.pi * 1.1 * t)) ** 3   # nhịp tim
        return 0.7

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        border, color = self._TONES[self._kind]
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(QColor(8, 14, 30, 220))
        p.setPen(pen(border, 1.5))
        p.drawRoundedRect(rect, 8, 8)
        level, led = self._led_level(), QColor(self._LEDS[self._kind])
        center = QPointF(rect.left() + 18, rect.top() + 18)
        p.setPen(NO_PEN)
        halo = QColor(led)
        halo.setAlpha(int(75 * level))
        p.setBrush(halo)
        p.drawEllipse(center, 9, 9)
        core = QColor(led)
        core.setAlpha(int(255 * level))
        p.setBrush(core)
        p.drawEllipse(center, 4.5, 4.5)
        draw_typed(p, rect.adjusted(34, 8, -14, -8), self.typer.text, self.typer.shown,
                   theme.FONT_DOSSIER, 15, 10, color, cursor=self.typer.cursor_visible)