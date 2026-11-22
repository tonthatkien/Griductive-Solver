"""Animation nền dùng chung: Tween, Typer (gõ chữ), Clock (một QTimer cho mọi animation), ảnh nhân vật. (Scope F)
"""
import time
from pathlib import Path
from typing import Callable, Dict, Optional

from PySide6.QtCore import (QEasingCurve, QObject, QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QPixmap)


ASSET_DIR = Path(__file__).resolve().parent / "assets" / "characters"


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
