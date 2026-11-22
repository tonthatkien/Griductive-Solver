"""Hàm vẽ dùng chung: font, chữ vừa khung, chữ gõ từng ký tự, chữ neon, bốn góc ngắm. (Scope F)

Enum viết đầy đủ (Qt.AlignmentFlag.X) để đổi sang PyQt6 chỉ cần sửa dòng import.
"""
import math
from typing import Dict

from PySide6.QtCore import (QPointF, QRectF, Qt)
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QPainter,
                           QTextLayout, QTextOption)

from gui.icons import NO_BRUSH, pen


def flags(*items) -> int:
    value = 0
    for item in items:
        value |= int(item.value)
    return value


A = Qt.AlignmentFlag
ALIGN_CENTER = flags(A.AlignCenter)
ALIGN_LEFT_MID = flags(A.AlignLeft, A.AlignVCenter)
WRAP_TOP = flags(A.AlignLeft, A.AlignTop, Qt.TextFlag.TextWordWrap)
WRAP_CENTER = flags(A.AlignCenter, Qt.TextFlag.TextWordWrap)

def draw_brackets(p: QPainter, rect: QRectF, color, size: float, width: float = 2.0) -> None:
    """Bốn góc ngắm hình chữ L quanh một khung (kiểu kính định vị / màn hình quét)."""
    p.save()
    p.setBrush(NO_BRUSH)
    p.setPen(pen(color, width))
    for cx, cy, sx, sy in ((rect.left(), rect.top(), 1, 1), (rect.right(), rect.top(), -1, 1),
                           (rect.left(), rect.bottom(), 1, -1), (rect.right(), rect.bottom(), -1, -1)):
        p.drawLine(QPointF(cx, cy), QPointF(cx + size * sx, cy))
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy + size * sy))
    p.restore()


def make_font(family: str, px: int, bold: bool = False, italic: bool = False,
              spacing: float = 0.0) -> QFont:
    font = QFont(family)
    font.setPixelSize(max(6, int(px)))
    font.setBold(bold)
    font.setItalic(italic)
    if spacing:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


_FIT_PX: Dict[tuple, int] = {}
_FIT_LINES: Dict[tuple, tuple] = {}


def draw_fitted(p: QPainter, rect: QRectF, text: str, family: str, max_px: int, min_px: int,
                color, bold: bool = False, italic: bool = False, fl: int = WRAP_TOP) -> None:
    """Vẽ text, tự giảm cỡ chữ đến khi vừa khung (kết quả được nhớ để khỏi tính lại mỗi khung hình)."""
    key = (text, family, int(max_px), min_px, bold, italic, fl, int(rect.width()), int(rect.height()))
    px = _FIT_PX.get(key)
    if px is None:
        px = max(int(max_px), min_px)
        while True:
            p.setFont(make_font(family, px, bold, italic))
            box = p.boundingRect(rect, fl, text)
            if px <= min_px or (box.height() <= rect.height() + 0.5 and box.width() <= rect.width() + 0.5):
                break
            px -= 1
        if len(_FIT_PX) > 800:
            _FIT_PX.clear()
        _FIT_PX[key] = px
    p.setFont(make_font(family, px, bold, italic))
    p.setPen(QColor(color))
    p.drawText(rect, fl, text)


def _span(style: str, text: str) -> str:
    return f'<span style="{style}">{text}</span>'


def _layout_lines(font: QFont, text: str, width: float):
    """Xếp chữ theo chiều rộng: [(vị trí đầu, độ dài, y, bề rộng, ascent)], tổng chiều cao."""
    layout = QTextLayout(text, font)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(option)
    lines, y = [], 0.0
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max(1.0, width))
        line.setPosition(QPointF(0.0, y))
        lines.append((line.textStart(), line.textLength(), y, line.naturalTextWidth(), line.ascent()))
        y += line.height()
    layout.endLayout()
    return lines, y


def draw_typed(p: QPainter, rect: QRectF, text: str, shown: int, family: str, max_px: int,
               min_px: int, color, bold: bool = False, italic: bool = False,
               center: bool = False, cursor: bool = False) -> None:
    """Vẽ `shown` ký tự đầu của text. Cỡ chữ và chỗ xuống dòng tính trên TOÀN BỘ text nên chữ
    không nhảy dòng hay đổi cỡ khi đang gõ. cursor=True vẽ con trỏ gạch dưới kiểu terminal."""
    text = text.replace("\n", "\u2028")
    key = (text, family, int(max_px), min_px, bold, italic, int(rect.width()), int(rect.height()))
    cached = _FIT_LINES.get(key)
    if cached is None:
        px = max(int(max_px), min_px)
        while True:
            lines, height = _layout_lines(make_font(family, px, bold, italic), text, rect.width()) \
                if text else ([], 0.0)
            if px <= min_px or height <= rect.height() + 0.5:
                break
            px -= 1
        if len(_FIT_LINES) > 400:
            _FIT_LINES.clear()
        cached = _FIT_LINES[key] = (px, lines, height)
    px, lines, height = cached
    font = make_font(family, px, bold, italic)
    p.save()
    p.setFont(font)
    p.setPen(QColor(color))
    metrics = QFontMetricsF(font)
    top = rect.top() + ((rect.height() - height) / 2 if center else 0.0)
    cursor_at = QPointF(rect.left(), top + metrics.ascent())
    for start, length, y, line_width, ascent in lines:
        visible = min(length, max(0, shown - start))
        if visible <= 0:
            continue
        chunk = text[start:start + visible]
        x = rect.left() + ((rect.width() - line_width) / 2 if center else 0.0)
        base = top + y + ascent
        p.drawText(QPointF(x, base), chunk)
        cursor_at = QPointF(x + metrics.horizontalAdvance(chunk), base)
    if cursor:
        p.fillRect(QRectF(cursor_at.x() + px * 0.1, cursor_at.y() + 1, px * 0.55, max(2.0, px * 0.11)),
                   QColor(color))
    p.restore()


def draw_neon_text(p: QPainter, rect: QRectF, text: str, font: QFont, color, glow, strength: float = 1.0,
                   fl: int = ALIGN_CENTER, alpha: int = 255) -> None:
    """Chữ neon: vài vòng bóng mờ quanh chữ (màu glow) rồi lõi sáng (màu color)."""
    p.save()
    p.setFont(font)
    for radius, base_alpha in ((6, 10), (4, 20), (2, 40)):
        tint = QColor(glow)
        tint.setAlpha(int(base_alpha * strength * alpha / 255))
        p.setPen(tint)
        for k in range(12):
            angle = 2 * math.pi * k / 12
            p.drawText(rect.translated(math.cos(angle) * radius, math.sin(angle) * radius), fl, text)
    core = QColor(color)
    core.setAlpha(alpha)
    p.setPen(core)
    p.drawText(rect, fl, text)
    p.restore()
