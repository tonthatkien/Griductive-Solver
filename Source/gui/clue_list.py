"""ClueListView: danh sách clue đã mở, vệt sáng quét clue mới. (Scope F)
"""
import time
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (QRectF, Qt,
                            Signal)
from PySide6.QtGui import (QBrush, QColor, QLinearGradient)
from PySide6.QtWidgets import (QListWidget,
                               QListWidgetItem, QStyledItemDelegate, QWidget)

from gui.anim import clock


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
