"""Kiểm tra font nào đang được dùng cho 4 lớp typography và có hỗ trợ tiếng Việt không. (Scope F)

Chạy từ thư mục Source/:  python tools/check_fonts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import theme  # noqa: E402

SAMPLE = "HỒ SƠ MẬT · PHÁ ÁN · MANH MỐI · Sự thật chỉ có một!"


def main() -> None:
    app = QApplication(sys.argv)
    resolved = theme.init_fonts()
    print("Mẫu thử:", SAMPLE)
    for layer, family in resolved.items():
        wanted = theme.FONT_STACKS[layer][0]
        note = "" if family == wanted else f"  <-- chưa có '{wanted}', đang dùng font dự phòng"
        vi = "có" if theme.supports_vietnamese(family) else "KHÔNG (Qt sẽ lấy glyph từ font khác)"
        print(f"{layer:8s} -> {family:20s} tiếng Việt: {vi}{note}")
    del app


if __name__ == "__main__":
    main()
