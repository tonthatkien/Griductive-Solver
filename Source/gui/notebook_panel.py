"""NotebookPanel: sổ tay phá án, thống kê realtime + log từng bước. (Scope F)
"""
import html
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (QEasingCurve, Qt)
from PySide6.QtWidgets import (QFrame, QGridLayout, QLabel, QTextBrowser, QVBoxLayout,
                               QWidget)

from gui import theme
from gui.clue_text import STATUS_VN
from gui.anim import Tween
from gui.draw_utils import (_span)
from gui.neon_widgets import NeonTitle


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
