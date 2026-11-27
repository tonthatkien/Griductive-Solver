"""HomePage: trang chủ là mặt bàn thám tử về đêm, mỗi vật trên bàn là một chức năng. (Scope F)

  hồ sơ vụ án -> bản đồ vụ án     sổ tay -> màn Cách chơi     radio -> bật/tắt âm thanh
  thẻ THOÁT   -> đóng game        huy chương -> số sao đã có  ảnh bóng đen -> chỉ để tạo không khí

Chỉ nhận danh sách `Level` và `Progress` để hiện tiến độ; không đọc nội dung puzzle, không có luật chơi.
Phát tín hiệu kèm tâm của vật được bấm để lớp chuyển cảnh khép vòng tròn về đúng chỗ đó.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui import desk_scene, theme
from gui.anim import Tween, clock
from gui.draw_utils import ALIGN_CENTER, draw_fitted, draw_neon_text, make_font
from gui.icons import NO_PEN, pen
from gui.levels import Level
from gui.progress import MAX_STARS, Progress

IDLE_INFO = "Chọn một vật trên bàn để bắt đầu. Dùng chuột, hoặc phím ← → rồi Enter."
SUBTITLE = "HỒ SƠ ĐIỀU TRA  ·  SỰ THẬT CHỈ CÓ MỘT"


@dataclass(frozen=True)
class _Prop:
    key: str
    fx: float            # tâm theo tỉ lệ chiều rộng / chiều cao của trang
    fy: float
    wf: float            # kích thước theo tỉ lệ s = min(rộng, cao * 1.35)
    hf: float
    rot: float           # độ nghiêng (độ)
    label: str = ""      # có nhãn = bấm được
    delay: int = 0       # ms: lúc vật "đặt xuống bàn" khi mở màn


PROPS = (
    _Prop("folder", 0.50, 0.58, 0.54, 0.40, -1.5, "VÀO VỤ ÁN", 300),
    _Prop("notebook", 0.19, 0.62, 0.25, 0.34, 4.0, "CÁCH CHƠI", 520),
    _Prop("radio", 0.82, 0.69, 0.33, 0.23, -3.0, "ÂM THANH", 740),
    _Prop("medal", 0.13, 0.31, 0.12, 0.17, 0.0, "", 900),
    _Prop("photo", 0.88, 0.31, 0.16, 0.21, 6.0, "", 1050),
    _Prop("cup", 0.37, 0.90, 0.13, 0.13, 0.0, "", 1150),
    _Prop("quit", 0.93, 0.945, 0.13, 0.05, 0.0, "THOÁT", 1250),
)
ORDER = tuple(p.key for p in PROPS if p.label)          # thứ tự phím mũi tên
BY_KEY = {p.key: p for p in PROPS}


class HomePage(QWidget):
    mapRequested = Signal(object)          # tâm của hồ sơ (tọa độ trang)
    tutorialRequested = Signal(object)
    soundToggled = Signal()
    quitRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._levels: List[Level] = []
        self._progress: Optional[Progress] = None
        self._cleared = self._total = self._stars = self._max_stars = 0
        self._next = ""
        self._sound_on = True
        self._hover, self._focus = "", ""
        self._rects: Dict[str, QRectF] = {}
        self._hovers = {p.key: Tween(self, self.update, QEasingCurve.Type.OutCubic) for p in PROPS}
        self._appear = {p.key: Tween(self, self.update, QEasingCurve.Type.OutBack) for p in PROPS}
        self._title = Tween(self, self.update, QEasingCurve.Type.OutCubic)
        self._lamp = Tween(self, self.update, QEasingCurve.Type.Linear)
        for tween in (*self._appear.values(), self._title, self._lamp):
            tween.now = 1.0
        self._intro_token = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        clock().tick.connect(self._on_tick)

    # ---- API ----------------------------------------------------------------------------
    def set_levels(self, levels: List[Level], progress: Progress) -> None:
        self._levels, self._progress = list(levels), progress
        self.refresh()

    def refresh(self) -> None:
        """Đọc lại tiến độ để hiện số vụ đã phá, số sao và vụ án tiếp theo."""
        normal = [lv for lv in self._levels if not lv.sealed]
        stars = (lambda lv: self._progress.stars(lv.key)) if self._progress else (lambda lv: 0)
        self._cleared = sum(1 for lv in normal if stars(lv) > 0)
        self._total = len(normal)
        self._stars = sum(stars(lv) for lv in normal)
        self._max_stars = MAX_STARS * len(normal)
        todo = next((lv for lv in normal if stars(lv) == 0), None)
        self._next = f"{todo.title} · {todo.place}" if todo else ""
        self.update()

    def set_sound(self, on: bool) -> None:
        self._sound_on = on
        self.update()

    def play_intro(self) -> None:
        """Bật đèn bàn (nhấp nháy), chữ hiện dần, các vật lần lượt đặt xuống bàn."""
        self._intro_token += 1
        token = self._intro_token
        for tween in self._appear.values():
            tween.jump(0.0)
        self._title.jump(0.0)
        self._lamp.jump(0.0)
        self._lamp.go(1.0, 1400)
        QTimer.singleShot(500, lambda: self._title.go(1.0, 1100) if token == self._intro_token else None)
        for prop in PROPS:
            QTimer.singleShot(prop.delay, lambda k=prop.key: self._drop(k, token))

    def _drop(self, key: str, token: int) -> None:
        if token == self._intro_token:
            self._appear[key].go(1.0, 650)

    # ---- hình học -----------------------------------------------------------------------
    def _layout(self) -> Dict[str, QRectF]:
        w, h = float(self.width()), float(self.height())
        s = min(w, h * 1.35)
        rects = {}
        for prop in PROPS:
            pw, ph = prop.wf * s, prop.hf * s
            rects[prop.key] = QRectF(prop.fx * w - pw / 2, prop.fy * h - ph / 2, pw, ph)
        return rects

    def _active(self) -> str:
        return self._hover or self._focus

    def _hit(self, pos: QPointF) -> str:
        for key in reversed([p.key for p in PROPS]):
            if self._rects.get(key, QRectF()).adjusted(-6, -6, 6, 6).contains(pos):
                return key
        return ""

    # ---- tương tác ----------------------------------------------------------------------
    def _set_hover(self, key: str) -> None:
        if key == self._hover:
            return
        self._hover = key
        self._sync_tweens()
        clickable = bool(key and BY_KEY[key].label)
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)

    def _sync_tweens(self) -> None:
        active = self._active()
        for key, tween in self._hovers.items():
            tween.go(1.0 if key == active else 0.0, 180)

    def mouseMoveEvent(self, event) -> None:
        self._focus = ""
        self._set_hover(self._hit(event.position()))

    def leaveEvent(self, event) -> None:
        self._set_hover("")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            key = self._hit(event.position())
            if key and BY_KEY[key].label:
                self._activate(key)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Up):
            step = 1 if key in (Qt.Key.Key_Right, Qt.Key.Key_Down) else -1
            cur = ORDER.index(self._active()) if self._active() in ORDER else (-1 if step > 0 else 0)
            self._hover, self._focus = "", ORDER[(cur + step) % len(ORDER)]
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._sync_tweens()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._activate(self._active() or "folder")
        else:
            super().keyPressEvent(event)

    def _activate(self, key: str) -> None:
        center = self._rects[key].center() if key in self._rects else QPointF(self.width() / 2, self.height() / 2)
        if key == "folder":
            self.mapRequested.emit(center)
        elif key == "notebook":
            self.tutorialRequested.emit(center)
        elif key == "radio":
            self.soundToggled.emit()
        elif key == "quit":
            self.quitRequested.emit()

    def _info(self, key: str) -> str:
        if key == "folder":
            tail = f"Tiếp theo: {self._next}." if self._next else "Bạn đã phá mọi vụ án!"
            return f"Mở hồ sơ và chọn một vụ án trên bản đồ. {tail}"
        if key == "notebook":
            return "Học cách suy luận qua một vụ mẫu 3×3, từng bước một."
        if key == "radio":
            return "Nhạc nền: " + ("BẬT. Bấm để tắt." if self._sound_on else "TẮT. Bấm để bật.")
        if key == "medal":
            return f"Đã phá {self._cleared}/{self._total} vụ án · {self._stars}/{self._max_stars} sao."
        if key == "photo":
            return "Hắn vẫn đang chờ ở cuối mỗi vụ án..."
        if key == "quit":
            return "Rời khỏi game."
        return IDLE_INFO

    # ---- vẽ -----------------------------------------------------------------------------
    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        t = clock().t
        w, h = float(self.width()), float(self.height())
        lamp = self._lamp.now
        if lamp < 1.0:                                   # bật đèn: chập chờn rồi sáng hẳn
            lamp *= 0.35 + 0.65 * (int(t * 14) % 3 != 1)
        desk_scene.paint_desk(p, QRectF(0, 0, w, h), t, lamp)
        self._rects = self._layout()
        self._paint_title(p, w, h)
        for prop in PROPS:
            self._paint_prop(p, prop, t)
        self._paint_info(p, w, h)

    def _paint_title(self, p: QPainter, w: float, h: float) -> None:
        k = self._title.now
        if k <= 0.0:
            return
        p.save()
        p.setOpacity(k)
        px = max(28, int(min(w * 0.075, h * 0.115)))
        box = QRectF(0, h * 0.055 - (1 - k) * 14, w, px * 1.5)
        draw_neon_text(p, box, "GRIDUCTIVE", make_font(theme.FONT_TITLE, px, True, spacing=px * 0.18),
                       "#f3d36b", theme.GOLD, 1.0)
        sub = QRectF(0, box.bottom() - px * 0.1, w, px * 0.42)
        p.setPen(QColor(205, 190, 150, 220))
        p.setFont(make_font(theme.display(SUBTITLE), max(11, int(px * 0.24)), True, spacing=3.0))
        p.drawText(sub, ALIGN_CENTER, SUBTITLE)
        p.restore()

    def _paint_prop(self, p: QPainter, prop: _Prop, t: float) -> None:
        rect = self._rects[prop.key]
        appear = max(0.0, min(1.0, self._appear[prop.key].now))
        if appear <= 0.0:
            return
        hover = self._hovers[prop.key].now
        p.save()
        p.setOpacity(min(1.0, appear * 1.6))
        p.translate(rect.center().x(), rect.center().y() - (1.0 - appear) * 70 - 7 * hover)
        p.rotate(prop.rot * (1.0 + (1.0 - appear) * 3))
        p.scale(1.0 + 0.045 * hover, 1.0 + 0.045 * hover)
        if hover > 0.01:                                  # quầng sáng ấm sau vật đang chọn
            r = max(rect.width(), rect.height()) * 0.78
            glow = QRadialGradient(QPointF(0, 0), r)
            glow.setColorAt(0.0, QColor(255, 205, 120, int(95 * hover)))
            glow.setColorAt(1.0, QColor(255, 190, 100, 0))
            p.setPen(NO_PEN)
            p.setBrush(glow)
            p.drawEllipse(QPointF(0, 0), r, r)
        local = QRectF(-rect.width() / 2, -rect.height() / 2, rect.width(), rect.height())
        key = prop.key
        if key == "folder":
            desk_scene.draw_folder(p, local, t)
        elif key == "notebook":
            desk_scene.draw_notebook(p, local, t)
        elif key == "radio":
            desk_scene.draw_radio(p, local, t, self._sound_on)
        elif key == "medal":
            ratio = self._stars / self._max_stars if self._max_stars else 0.0
            desk_scene.draw_medal(p, local, t, ratio)
        elif key == "photo":
            desk_scene.draw_photo(p, local, t)
        elif key == "cup":
            desk_scene.draw_cup(p, local, t)
        p.restore()
        if prop.label:
            self._paint_label(p, prop, rect, hover, appear)

    def _paint_label(self, p: QPainter, prop: _Prop, rect: QRectF, hover: float, appear: float) -> None:
        if prop.key == "quit":                            # thẻ THOÁT nằm gọn ở góc, không dây
            tag = rect
        else:
            width = max(rect.width() * 0.42, 110.0)
            tag = QRectF(rect.center().x() - width / 2, rect.bottom() + 12 - 7 * hover, width, 26)
        desk_scene.draw_tag(p, tag, prop.label, active=hover > 0.5, alpha=min(1.0, appear) * (0.7 + 0.3 * hover))

    def _paint_info(self, p: QPainter, w: float, h: float) -> None:
        text = self._info(self._active())
        if self._title.now < 0.9:
            return
        rect = QRectF(w * 0.24, h - 52, w * 0.52, 34)
        p.save()
        p.setPen(pen(QColor(226, 185, 71, 90), 1.2))
        p.setBrush(QColor(6, 4, 2, 170))
        p.drawRoundedRect(rect, 8, 8)
        draw_fitted(p, rect.adjusted(14, 3, -14, -3), text, theme.FONT_CLUE_BODY, 14, 9, "#e8dfc4",
                    fl=ALIGN_CENTER)
        p.restore()
