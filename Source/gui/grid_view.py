"""GridView: lưới N×N các thẻ + nhãn tọa độ. (Scope F)
"""
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (Qt,
                            Signal)
from PySide6.QtWidgets import (QGridLayout, QLabel, QWidget)

from engine import board
from gui.card_view import CardView


class GridView(QWidget):
    """Lưới N×N + nhãn tọa độ (A, B, C... / 1, 2, 3...)."""

    cardClicked = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.cards: Dict[str, CardView] = {}
        self._order: List[Tuple[int, int, CardView]] = []
        self._layout = QGridLayout(self)
        self._layout.setSpacing(12)
        self._layout.setContentsMargins(6, 6, 6, 6)

    def set_board(self, n: int, info: Dict[str, Tuple[str, str]]) -> None:
        """info: cell -> (name, profession)."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.cards = {}
        self._order = []
        # QGridLayout nhớ stretch/min-size của hàng/cột cũ: reset hết, nếu không
        # hàng/cột thừa của lưới 5x5 vẫn chiếm chỗ khi quay lại 3x3.
        for i in range(max(self._layout.rowCount(), self._layout.columnCount())):
            self._layout.setRowStretch(i, 0)
            self._layout.setColumnStretch(i, 0)
            self._layout.setRowMinimumHeight(i, 0)
            self._layout.setColumnMinimumWidth(i, 0)
        self._layout.setSpacing(12 if n <= 3 else 5)   # lưới lớn: thu khoảng cách để thẻ rộng hơn
        for c in range(n):
            self._layout.addWidget(self._coord(board.COLS[c], height=24), 0, c + 1)
        for r in range(n):
            self._layout.addWidget(self._coord(str(r + 1), width=26), r + 1, 0)
            for c in range(n):
                cell = board.cell_id(r, c)
                card = CardView(cell)
                if n > 3:                       # lưới lớn: cho phép thẻ co nhỏ hơn để vừa khung
                    card.setMinimumSize(92, 116)
                card.set_identity(*info[cell])
                card.clicked.connect(self.cardClicked)
                self._layout.addWidget(card, r + 1, c + 1)
                self.cards[cell] = card
                self._order.append((r, c, card))
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

    def stagger_in(self, delay_ms: int = 0, step_ms: int = 70) -> None:
        """Cho các thẻ lật vào lần lượt theo đường chéo, bắt đầu sau `delay_ms`."""
        for r, c, card in self._order:
            card.appear(delay_ms + (r + c) * step_ms)

    def set_input_enabled(self, enabled: bool) -> None:
        for card in self.cards.values():
            card.set_input_enabled(enabled)
