"""TutorialPage: màn "Cách chơi", diễn một vụ mẫu 3x3 bằng đúng các thẻ và hiệu ứng của màn chơi. (Scope F)

Kịch bản viết sẵn (không gọi engine/agent): mỗi bước có chữ giải thích và một đoạn diễn trên lưới
  căn cứ nhấp nháy -> thẻ sắp lật "SUY RA" -> lật thẻ.
Đi tới/lui bằng nút hoặc phím ← →; Esc về trang chủ. Chạy lại bước nào thì dựng lại trạng thái đầu bước đó.

Vụ mẫu (lưới 3x3, chỉ có đúng một cách điền khớp với các manh mối hiện ra):
  Heiji (B2) lật sẵn, vô tội: "Không có tội phạm nào trong cột C."  => Ayumi (C1) vô tội
  Ayumi (C1): "Có đúng 2 tội phạm trong hàng 1."                    => Ran (A1) tội phạm
  Ran (A1): "Có ít nhất 1 tội phạm trong hàng 3."                   (chưa đủ để chứng minh Kogoro (A2))
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from engine import board
from gui import desk_scene, theme
from gui.anim import clock
from gui.conan_widgets import ConanWidget
from gui.grid_view import GridView
from gui.neon_widgets import NeonTitle, TerminalMessage

# (tên, nghề) theo thứ tự hàng 1 -> 3, cột A -> C. Tên khớp ảnh trong assets/characters.
CAST = (("Ran", "Học sinh"), ("Kazuha", "Học sinh"), ("Ayumi", "Học sinh"),
        ("Kogoro", "Thám tử"), ("Heiji", "Thám tử"), ("Mitsuhiko", "Học sinh"),
        ("Agasa", "Nhà phát minh"), ("Ai", "Nhà khoa học"), ("Genta", "Học sinh"))
CRIM = "<b style='color:#ff6b7b'>TỘI PHẠM</b>"
INNO = "<b style='color:#6fb3ff'>VÔ TỘI</b>"


@dataclass(frozen=True)
class Reveal:
    cell: str
    status: str
    clue: str


@dataclass(frozen=True)
class Step:
    title: str
    body: str
    conan: str
    mood: str = "think"


def _cells() -> Dict[str, str]:
    """Nhãn hiển thị 'A1'..'C3' (cột chữ, hàng số) -> id ô của engine, lấy từ engine.board."""
    return {f"{board.COLS[c]}{r + 1}": board.cell_id(r, c) for r in range(3) for c in range(3)}


STEPS = (
    Step("MỤC TIÊU",
         f"Trên bàn có <b>9 nghi phạm</b> xếp lưới 3×3, hồ sơ nào cũng đang úp. Mỗi người chỉ có thể là {CRIM} "
         f"hoặc {INNO}.<br><br>Nhiệm vụ của bạn: <b>lật hết các hồ sơ</b> bằng suy luận. Không được đoán.",
         "Sự thật chỉ có một. Hãy bắt đầu từ những gì chắc chắn."),
    Step("HỒ SƠ VÀ MANH MỐI",
         "Hồ sơ của <b>Heiji</b> đã được lật sẵn. Mỗi hồ sơ lật ra đều <b>tiết lộ một manh mối</b>.<br><br>"
         "Manh mối này nói về <b>cột C</b>: ba ô cột C sáng laser xanh. Trong game, bấm vào một hồ sơ đã mở "
         "để xem manh mối của nó nhắc tới những ô nào.",
         "Không có tội phạm nào trong cột C. Nhớ kỹ điều này."),
    Step("SUY LUẬN ĐẦU TIÊN",
         "Muốn lật một hồ sơ, bạn phải <b>chứng minh</b> nó từ các manh mối đã có.<br><br>"
         "Manh mối của Heiji <b style='color:#ffd23c'>[1]</b> cho thấy cột C không có tội phạm, nên "
         f"<b>Ayumi (C1)</b> chắc chắn {INNO}. Hồ sơ <b style='color:#ffd23c'>CĂN CỨ</b> nhấp nháy vàng, "
         "hồ sơ <b style='color:#7af5ff'>SUY RA</b> sáng xanh lơ, rồi mới được lật.",
         "Căn cứ trước, kết luận sau. Thứ tự đó không bao giờ đổi."),
    Step("NỐI TIẾP",
         "Ayumi vừa lộ manh mối mới: <i>hàng 1 có đúng 2 tội phạm</i>.<br><br>"
         f"Heiji <b style='color:#ffd23c'>[1]</b> cho biết Ayumi {INNO}, Ayumi <b style='color:#ffd23c'>[2]</b> "
         f"cho biết hàng 1 có 2 tội phạm. Vậy hai người còn lại của hàng 1 đều là {CRIM}: lật <b>Ran (A1)</b>.<br><br>"
         "Sổ tay trong game ghi lại từng bước như vậy: lật ai, dựa vào manh mối của ai.",
         "Mỗi hồ sơ lật ra lại mở thêm một manh mối. Cứ thế nối đi.", "happy"),
    Step("KHÔNG ĐOÁN MÒ",
         "Thử lật <b>Kogoro (A2)</b>? Các manh mối hiện có chưa đủ để chắc chắn: hồ sơ rung lên và vẫn úp.<br><br>"
         "Mỗi lần bị từ chối như vậy bạn <b>mất sao</b>. Chưa đủ bằng chứng thì hãy tìm hồ sơ khác "
         "đang đủ bằng chứng.",
         "Chưa đủ bằng chứng thì không kết luận!", "shake"),
    Step("CÔNG CỤ VÀ SAO",
         "Bị kẹt? <b>Hint</b> chỉ ra một hồ sơ có thể chứng minh tiếp (trừ 1 sao). "
         "<b>Bước tiếp / Auto Solve</b> để Agent suy luận hộ, vụ án chỉ còn 1 sao.<br><br>"
         "Tự phá án, không dùng Hint, không bị từ chối lần nào: <b style='color:#ffd23c'>★★★</b>.",
         "Tự mình phá án mới là chiến thắng thật sự.", "happy"),
    Step("SẴN SÀNG",
         "Bạn đã biết hết luật chơi: <b>đọc manh mối, chứng minh, rồi mới lật</b>.<br><br>"
         "Bấm <b>BẮT ĐẦU ĐIỀU TRA</b> để mở bản đồ vụ án và chọn vụ đầu tiên.",
         "Vụ án đang chờ chúng ta. Đi thôi!", "happy"),
)


# Các hồ sơ lật theo thứ tự kịch bản: (nhãn ô, trạng thái, manh mối).
KNOWN: Tuple[Tuple[str, str, str], ...] = (
    ("B2", "INNOCENT", "Không có tội phạm nào trong cột C."),
    ("C1", "INNOCENT", "Có đúng 2 tội phạm trong hàng 1."),
    ("A1", "CRIMINAL", "Có ít nhất 1 tội phạm trong hàng 3."),
)
BASIS = {2: ("B2",), 3: ("B2", "C1")}        # thẻ căn cứ, đúng thứ tự số [1], [2]
TARGET = {2: "C1", 3: "A1"}                  # thẻ được suy ra rồi lật
BASE_COUNT = {0: 0, 1: 0, 2: 1, 3: 2}        # số hồ sơ đã lật ở ĐẦU mỗi bước; bước 4 trở đi đủ 3


class TutorialPage(QWidget):
    backRequested = Signal(object)         # về trang chủ (tâm vòng tròn chuyển cảnh)
    playRequested = Signal(object)         # sang bản đồ vụ án

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._step, self._token = 0, 0
        self._ids = _cells()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build_ui()
        clock().tick.connect(self._on_tick)

    # ---- dựng giao diện -----------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 16, 28, 18)
        root.setSpacing(8)
        header = QHBoxLayout()
        self.btn_home = QPushButton("◀  TRANG CHỦ")
        self.btn_home.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_home.clicked.connect(lambda: self.backRequested.emit(self.btn_home.mapTo(self, self.btn_home.rect().center())))
        self.counter = QLabel("")
        self.counter.setObjectName("subtitle")
        header.addWidget(self.btn_home)
        header.addSpacing(14)
        header.addWidget(NeonTitle("CÁCH CHƠI", px=30, spacing=6.0))
        header.addStretch(1)
        header.addWidget(self.counter)
        root.addLayout(header)

        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.grid = GridView()
        self.grid.set_board(3, {board.cell_id(r, c): CAST[r * 3 + c] for r in range(3) for c in range(3)})
        self.grid.set_input_enabled(False)
        middle.addWidget(self.grid, 1)
        middle.addWidget(self._build_panel())
        root.addLayout(middle, 1)

        footer = QHBoxLayout()
        self.conan = ConanWidget(plate=True)
        self.conan.setFixedSize(480, 132)
        self.btn_prev = QPushButton("◀  Trước")
        self.btn_next = QPushButton("Tiếp  ▶")
        for button in (self.btn_prev, self.btn_next):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setMinimumHeight(40)
            button.setMinimumWidth(130)
        self.btn_prev.clicked.connect(lambda: self._go(self._step - 1))
        self.btn_next.clicked.connect(self._next)
        footer.addWidget(self.conan)
        footer.addStretch(1)
        footer.addWidget(self.btn_prev)
        footer.addSpacing(8)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)

    def _build_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("tutorialPanel")
        panel.setFixedWidth(400)
        panel.setStyleSheet(
            "QFrame#tutorialPanel { background: rgba(8, 12, 24, 215); border: 1.5px solid #6b5232; border-radius: 12px; }"
            f"QLabel#tutTitle {{ color: {theme.GOLD_SOFT}; font-family: \"{theme.FONT_CLUE_TITLE}\"; "
            "font-size: 20px; font-weight: bold; }"
            f"QLabel#tutBody {{ color: #e8dfc4; font-family: \"{theme.FONT_CLUE_BODY}\"; font-size: 14px; }}")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        self.step_title = QLabel("")
        self.step_title.setObjectName("tutTitle")
        self.step_body = QLabel("")
        self.step_body.setObjectName("tutBody")
        self.step_body.setWordWrap(True)
        self.step_body.setTextFormat(Qt.TextFormat.RichText)
        self.step_body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.terminal = TerminalMessage()
        self.terminal.setMinimumHeight(78)
        layout.addWidget(self.step_title)
        layout.addWidget(self.step_body, 1)
        layout.addWidget(self.terminal)
        return panel

    # ---- điều hướng ---------------------------------------------------------------------
    def restart(self) -> None:
        """Gọi mỗi khi vào màn: về bước đầu."""
        self._go(0)

    def _go(self, index: int) -> None:
        if not 0 <= index < len(STEPS):
            return
        self._token += 1
        self._step = index
        step = STEPS[index]
        last = index == len(STEPS) - 1
        self.step_title.setText(f"{index + 1}. {step.title}")
        self.step_body.setText(step.body)
        self.counter.setText(f"BƯỚC {index + 1} / {len(STEPS)}")
        self.btn_prev.setEnabled(index > 0)
        self.btn_next.setText("BẮT ĐẦU ĐIỀU TRA" if last else "Tiếp  ▶")
        self.btn_next.setMinimumWidth(220 if last else 130)
        self.terminal.set_message("Bấm 'Tiếp' hoặc phím → để đi tiếp." if index == 0 else "", "info")
        self.conan.say(step.conan, step.mood)
        self._perform(index, self._token)

    def _next(self) -> None:
        if self._step >= len(STEPS) - 1:
            self.playRequested.emit(self.btn_next.mapTo(self, self.btn_next.rect().center()))
        else:
            self._go(self._step + 1)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.backRequested.emit(self.rect().center())
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._next()
        elif key == Qt.Key.Key_Left:
            self._go(self._step - 1)
        else:
            super().keyPressEvent(event)

    # ---- diễn trên lưới -----------------------------------------------------------------
    def _card(self, name: str):
        return self.grid.cards[self._ids[name]]

    def _clear(self) -> None:
        for card in self.grid.cards.values():
            card.set_highlight("")

    def _show(self, name: str, status: str, clue: str, animate: bool) -> None:
        self._card(name).set_face_up(status, clue, animate)

    def _reset_board(self, step: int) -> None:
        """Dựng trạng thái ĐẦU bước `step` (không hiệu ứng): các hồ sơ đã lật ở những bước trước."""
        self._clear()
        for card in self.grid.cards.values():
            card.set_face_down()
        for name, status, clue in KNOWN[:BASE_COUNT.get(step, 3)]:
            self._show(name, status, clue, False)

    def _mark(self, mode: str, cells, numbered: bool = False) -> None:
        for n, name in enumerate(cells, 1):
            self._card(name).set_highlight(mode, str(n) if numbered else "")

    def _flip_next(self, index: int) -> None:
        self._clear()
        self._show(*KNOWN[index - 1], True)

    def _perform(self, index: int, token: int) -> None:
        """Dựng trạng thái đầu bước rồi chạy đoạn diễn của bước (theo mốc thời gian, hủy được bằng token)."""
        self._reset_board(index)

        def later(ms: int, fn: Callable[[], None]) -> None:
            QTimer.singleShot(ms, lambda: fn() if token == self._token else None)

        if index == 1:                                    # lật Heiji, rồi laser cột C
            later(500, lambda: self._show(*KNOWN[0], True))
            later(3200, lambda: (self._mark("target", ("C1", "C2", "C3")), self._mark("source", ("B2",))))
        elif index in (2, 3):                             # căn cứ -> suy ra -> lật
            later(500, lambda: self._mark("basis", BASIS[index], numbered=True))
            later(2700, lambda: self._mark("infer", (TARGET[index],)))
            later(3900, lambda: self._flip_next(index))
        elif index == 4:                                  # đoán khi chưa đủ bằng chứng
            later(700, self._reject)

    def _reject(self) -> None:
        self._card("A2").shake()
        self.terminal.set_message("Chưa đủ bằng chứng: chưa chắc Kogoro (A2) là vô tội "
                                  "(cũng chưa chắc điều ngược lại). Thẻ vẫn úp.", "warn")

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        desk_scene.paint_desk(p, QRectF(self.rect()), clock().t, 0.85)
