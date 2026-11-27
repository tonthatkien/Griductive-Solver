"""NotebookPanel: sổ tay phá án, ghi lại vì sao mỗi hồ sơ được lật. (Scope F)

Chỉ dùng ngôn ngữ của người chơi: hồ sơ nào được lật, kết luận gì, dựa vào manh mối của những hồ sơ nào.
Không hiển thị thuật ngữ SAT / KB / UNSAT.
"""
import html
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QTextBrowser, QVBoxLayout, QWidget)

from gui.clue_text import STATUS_VN
from gui.draw_utils import (_span)
from gui.neon_widgets import NeonTitle

EMPTY_HINT = ("Mỗi lần một hồ sơ được lật, sổ tay sẽ ghi lại hồ sơ đó được suy ra từ "
              "manh mối của những hồ sơ nào.")


class NotebookPanel(QFrame):
    """Sổ tay phá án: mỗi hồ sơ được lật là một thẻ ghi chú "căn cứ → kết luận"."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("notebookCover")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(NeonTitle("SỔ TAY PHÁ ÁN", px=15, spacing=3.0, gadget=True, core="#dce8ff"),
                         0, Qt.AlignmentFlag.AlignHCenter)
        self.view = QTextBrowser()
        self.view.setObjectName("notebook")
        self.view.setOpenLinks(False)
        layout.addWidget(self.view, 1)
        self.reset()

    def reset(self) -> None:
        self.view.clear()
        self._empty = True
        self.view.setHtml(
            f"<p style='color:#7f93ba;font-size:12px;margin:8px 4px'>{html.escape(EMPTY_HINT)}</p>")

    def _append(self, body: str) -> None:
        if self._empty:                       # bỏ dòng hướng dẫn khi có ghi chú đầu tiên
            self.view.clear()
            self._empty = False
        self.view.append(body)
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    _NOTE_TONES = {
        "#7a5a1a": ("#e5b95c", "#1c1a17"),   # chưa đủ bằng chứng / bế tắc: chữ vàng ấm trên nền tối dịu
        "#a3121f": ("#f27983", "#21131b"),   # mâu thuẫn: chữ đỏ san hô dịu
    }

    def add_note(self, text: str, color: str = "#8ea2c8") -> None:
        fg, bg = self._NOTE_TONES.get(color, (color, "#131c30"))
        self._append(
            f"<table width='100%' cellspacing='0' cellpadding='7' style='margin:4px 0'>"
            f"<tr><td bgcolor='{bg}' style='border-left:3px solid {fg};color:{fg};font-size:12px'>"
            f"{html.escape(text)}</td></tr></table>"
        )

    def add_entry(self, step: int, who: str, cell_label: str, verdict: str,
                  basis: List[Tuple[str, str]]) -> None:
        """Một thẻ ghi chú cho mỗi hồ sơ được lật.

        basis: [(chủ manh mối, nội dung manh mối)], theo đúng thứ tự số 1, 2, 3... đang hiện
        trên các thẻ căn cứ ở lưới."""
        is_criminal = verdict == "CRIMINAL"
        accent = "#f26d7d" if is_criminal else "#63a4ff"
        badge_bg = "#331722" if is_criminal else "#142847"
        word = STATUS_VN[verdict].lower()

        rows = [
            _span("color:#7cc4fa;font-weight:bold;font-size:11px", f"BƯỚC {step:02d}")
            + _span("color:#7f93ba;font-size:11px", f" · {html.escape(who)}"),
            f"<span style='color:#f0f4fc;font-weight:bold;font-size:13px'>{html.escape(cell_label)}</span> "
            f"<span style='background-color:{badge_bg};color:{accent};font-weight:bold;font-size:11px'>"
            f"&nbsp;{STATUS_VN[verdict].upper()}&nbsp;</span>",
        ]
        if basis:
            rows.append("<span style='color:#8aa4d6;font-size:11px'><b>VÌ SAO? Căn cứ vào manh mối của:</b></span>")
            for i, (owner, text) in enumerate(basis, 1):
                rows.append(
                    f"<span style='color:#f3d36b;font-weight:bold;font-size:12px'>[{i}]</span> "
                    f"<span style='color:#dce8ff;font-weight:bold;font-size:12px'>{html.escape(owner)}</span><br/>"
                    f"<span style='color:#b9c7e2;font-size:12px'>&nbsp;&nbsp;&nbsp;&nbsp;“{html.escape(text)}”</span>")
            joined = "các manh mối trên" if len(basis) > 1 else "manh mối này"
            rows.append(f"<span style='color:#cfd9ec;font-size:12px'>Ghép {joined} lại, chỉ còn một khả năng: "
                        f"<b style='color:{accent}'>{html.escape(cell_label)} là {word}</b>.</span>")
        else:
            rows.append("<span style='color:#cfd9ec;font-size:12px'>Suy ra trực tiếp từ dữ kiện ban đầu "
                        "của vụ án, chưa cần manh mối nào.</span>")
        self._append(
            f"<table width='100%' cellspacing='0' cellpadding='8' style='margin:5px 0'>"
            f"<tr><td bgcolor='#131e36' style='border-left:3px solid {accent};line-height:140%'>"
            f"{'<br/>'.join(rows)}</td></tr></table>"
        )
