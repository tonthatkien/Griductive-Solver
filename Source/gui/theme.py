"""Màu sắc, typography và QSS cho giao diện Agasa Modern Gadgets. (Scope F)

Bốn lớp font (Cinzel / Orbitron / Courier Prime / Share Tech Mono). Font không có trên máy sẽ
tự rơi về font hệ thống trong FONT_STACKS. QSS KHÔNG hỗ trợ letter-spacing hay danh sách
font dự phòng đáng tin cậy, nên: tên font được chọn lúc chạy (init_fonts) rồi nhúng vào QSS
(build_qss); chữ cần giãn cách/phát sáng thì vẽ bằng QPainter (NeonTitle trong components.py).
"""
from pathlib import Path
from typing import Dict, List

GOLD = "#e2b947"
GOLD_SOFT = "#f3d36b"
RED_NEON = "#ff3b4e"
CYAN_LASER = "#38f2ff"
TERMINAL_GREEN = "#39ff14"
TERMINAL_BG = "#050b14"
PAPER = "#efe2b6"
INK = "#2b1d0e"
CRIMINAL_COLOR = "#c0182b"
INNOCENT_COLOR = "#1f5fbf"
NIGHT_TOP = "#050a18"
NIGHT_MID = "#10213f"
NIGHT_BOTTOM = "#1b3157"

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FONT_STACKS: Dict[str, List[str]] = {
    "title": ["Cinzel", "Trajan Pro", "Georgia", "Times New Roman", "serif"],
    "gadget": ["Orbitron", "Bahnschrift", "Segoe UI", "Arial", "sans-serif"],
    "dossier": ["Courier Prime", "Courier New", "Cousine", "Courier", "monospace"],
    "mono": ["Share Tech Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New", "monospace"],
}
# Giá trị mặc định; init_fonts() cập nhật theo font thực sự có trên máy.
FONT_TITLE = FONT_STACKS["title"][0]
FONT_GADGET = FONT_STACKS["gadget"][0]
FONT_DOSSIER = FONT_STACKS["dossier"][0]
FONT_MONO = FONT_STACKS["mono"][0]


def init_fonts() -> Dict[str, str]:
    """Nạp font trong assets/fonts (nếu có), chọn font đầu tiên có sẵn cho từng lớp.

    Phải gọi SAU khi tạo QApplication và TRƯỚC build_qss(). Trả về {lớp: tên font}.
    """
    global FONT_TITLE, FONT_GADGET, FONT_DOSSIER, FONT_MONO
    from PySide6.QtGui import QFontDatabase
    if FONT_DIR.is_dir():
        for path in sorted(FONT_DIR.iterdir()):
            if path.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(path))
    installed = {name.lower(): name for name in QFontDatabase.families()}
    resolved = {layer: next((installed[n.lower()] for n in stack if n.lower() in installed), stack[-1])
                for layer, stack in FONT_STACKS.items()}
    FONT_TITLE, FONT_GADGET = resolved["title"], resolved["gadget"]
    FONT_DOSSIER, FONT_MONO = resolved["dossier"], resolved["mono"]
    return resolved


def supports_vietnamese(family: str) -> bool:
    """Font có bộ ký tự tiếng Việt không (dùng trong tools/check_fonts.py)."""
    from PySide6.QtGui import QFontDatabase
    return QFontDatabase.WritingSystem.Vietnamese in QFontDatabase.writingSystems(family)


def build_qss() -> str:
    """Stylesheet toàn ứng dụng, dùng tên font đã chọn bởi init_fonts()."""
    return f"""
QToolTip {{ background: #0b1429; color: {CYAN_LASER}; border: 1px solid {CYAN_LASER};
    font-family: "{FONT_GADGET}"; font-size: 11px; padding: 5px; }}
QLabel {{ color: #e8dfc4; }}
QLabel#subtitle {{ color: {GOLD_SOFT}; font-family: "{FONT_DOSSIER}"; font-size: 14px; font-style: italic; }}
QLabel#coord {{ color: {CYAN_LASER}; font-family: "{FONT_MONO}"; font-size: 16px; font-weight: bold; }}

QFrame#notebookCover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #17233b, stop:1 #0b1222);
    border: 1.5px solid #2d4373; border-radius: 12px;
}}
QLabel#statchip {{
    background: #10192e; border: 1px solid #2b3f6b; border-radius: 8px;
    color: #e6eefc; font-family: "{FONT_MONO}"; font-size: 12px; padding: 5px 4px;
}}
QTextBrowser#notebook {{
    background: #0d1526; color: #dce6f7; border: 1px solid #253861; border-radius: 8px;
    font-family: "Segoe UI", "{FONT_DOSSIER}", sans-serif; font-size: 13px; padding: 8px;
    selection-background-color: #264278; selection-color: #ffffff;
}}
QListWidget#cluelist {{
    background: {PAPER}; color: {INK}; border: 1px solid #8a6a3a; border-radius: 6px;
    font-family: "{FONT_DOSSIER}"; font-size: 13px; font-style: italic; outline: none;
}}
QListWidget#cluelist::item {{ padding: 7px 6px; border-bottom: 1px dashed #b49a64; }}
QListWidget#cluelist::item:selected {{ background: #f0c96a; color: #1a0f06; font-weight: bold; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: #1b2b4d; color: #b9c6e6; padding: 8px 18px; margin-right: 4px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-family: "{FONT_GADGET}"; font-size: 11px; font-weight: bold;
}}
QTabBar::tab:selected {{ background: #2c4170; color: {CYAN_LASER}; }}

QPushButton {{
    background: #1b2b4d; color: #e8dfc4; border: 1px solid #3d5486; border-radius: 8px;
    padding: 7px 14px; font-family: "{FONT_GADGET}"; font-size: 11px; font-weight: bold;
}}
QPushButton:hover {{ border-color: {CYAN_LASER}; color: {CYAN_LASER}; }}
QPushButton:pressed {{ background: #14213c; }}
QPushButton:disabled {{ color: #6a7592; border-color: #26324f; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3d5486; border-radius: 4px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""
