"""Task: chạy một hàm nặng ngoài luồng giao diện. (Scope F)"""
from typing import Callable

from PySide6.QtCore import QThread, Signal


class Task(QThread):
    """Chạy một hàm nặng (DPLL/SAT) ngoài luồng giao diện để GUI không đứng hình."""

    done = Signal(object, object)       # (kết quả, lỗi)

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn(), None)
        except BaseException as exc:    # noqa: BLE001 - chuyển lỗi về luồng GUI để hiển thị
            self.done.emit(None, exc)
