"""Icon + nhân vật vẽ bằng QPainter (vector, không cần file ảnh). (Scope F)

Mọi hàm vẽ vào hình chữ nhật `r` (QRectF), giữ nguyên trạng thái painter.
Muốn dùng ảnh thật: bỏ PNG vào gui/assets/characters/<tên-thường>.png (xem components.py).
"""
import math
import zlib
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QRadialGradient)

NO_PEN = Qt.PenStyle.NoPen
NO_BRUSH = Qt.BrushStyle.NoBrush



_ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"
_ICON_CACHE: Dict[str, Optional[QPixmap]] = {}
_SCALED_CACHE: Dict[tuple, QPixmap] = {}


def load_icon(name: str) -> Optional[QPixmap]:
    """Nạp gui/assets/icons/<name>.png (có cache). Trả None nếu không có file."""
    if name not in _ICON_CACHE:
        path = _ICON_DIR / f"{name}.png"
        _ICON_CACHE[name] = QPixmap(str(path)) if path.exists() else None
    return _ICON_CACHE[name]


def clear_icon_cache() -> None:
    """Gọi khi đổi file ảnh runtime (dev nóng)."""
    _ICON_CACHE.clear()
    _SCALED_CACHE.clear()


def _scaled(name: str, pix: QPixmap, size) -> QPixmap:
    """Scale ảnh một lần cho mỗi (tên, kích thước) rồi dùng lại ở các khung hình sau."""
    key = (name, size.width(), size.height())
    if key not in _SCALED_CACHE:
        _SCALED_CACHE[key] = pix.scaled(size, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
    return _SCALED_CACHE[key]


def _draw_image_or(p: QPainter, r: QRectF, name: str,
                   rotate: float = 0.0, opacity: float = 1.0) -> bool:
    """Vẽ ảnh giữ tỉ lệ, canh giữa `r`. Trả True nếu đã vẽ (bỏ qua vector)."""
    pix = load_icon(name)
    if pix is None or pix.isNull():
        return False
    p.save()
    p.translate(r.center())
    if rotate:
        p.rotate(rotate)
    p.translate(-r.center())
    p.setOpacity(p.opacity() * opacity)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    scaled = _scaled(name, pix, r.size().toSize())
    x = r.left() + (r.width() - scaled.width()) / 2.0
    y = r.top() + (r.height() - scaled.height()) / 2.0
    p.drawPixmap(QPointF(x, y), scaled)
    p.restore()
    return True


def pen(color, width: float) -> QPen:
    p = QPen(QColor(color), width)
    p.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return p


def _begin(p: QPainter, r: QRectF) -> None:
    """Đưa hệ tọa độ về hình vuông -50..50 ở giữa r."""
    p.save()
    p.translate(r.center())
    s = min(r.width(), r.height()) / 100.0
    p.scale(s, s)


def star_polygon(cx: float, cy: float, big: float, small: float, points: int = 5) -> QPolygonF:
    poly = QPolygonF()
    for i in range(points * 2):
        ang = -math.pi / 2 + i * math.pi / points
        rad = big if i % 2 == 0 else small
        poly.append(QPointF(cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return poly


def draw_handcuffs(p: QPainter, r: QRectF, color: str = "#ff3b4e") -> None:
    if _draw_image_or(p, r, "handcuffs"):
        return
    _begin(p, r)
    p.setBrush(NO_BRUSH)
    p.setPen(pen(color, 9))
    p.drawEllipse(QPointF(-24, 6), 20, 20)
    p.drawEllipse(QPointF(24, 6), 20, 20)
    p.setPen(pen("#d9dde6", 4.5))
    for x in (-7, 0, 7):
        p.drawEllipse(QPointF(x, 6), 3.3, 3.3)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#d9dde6"))
    p.drawRoundedRect(QRectF(-31, -24, 14, 9), 3, 3)
    p.drawRoundedRect(QRectF(17, -24, 14, 9), 3, 3)
    p.restore()


def draw_badge(p: QPainter, r: QRectF, color: str = "#3b8bff") -> None:
    if _draw_image_or(p, r, "badge"):
        return
    _begin(p, r)
    path = QPainterPath()
    path.moveTo(0, -46)
    path.cubicTo(18, -40, 32, -40, 40, -36)
    path.lineTo(40, 0)
    path.cubicTo(40, 26, 18, 40, 0, 48)
    path.cubicTo(-18, 40, -40, 26, -40, 0)
    path.lineTo(-40, -36)
    path.cubicTo(-32, -40, -18, -40, 0, -46)
    grad = QLinearGradient(0, -46, 0, 48)
    grad.setColorAt(0, QColor(color).lighter(140))
    grad.setColorAt(1, QColor(color).darker(150))
    p.setBrush(QBrush(grad))
    p.setPen(pen("#f3d36b", 4))
    p.drawPath(path)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#fff3b0"))
    p.drawPolygon(star_polygon(0, 3, 22, 9))
    p.restore()


def draw_magnifier(p: QPainter, r: QRectF, color: str = "#8fe9ff") -> None:
    if _draw_image_or(p, r, "magnifier"):
        return
    _begin(p, r)
    p.setPen(pen("#6b4a2b", 11))
    p.drawLine(QPointF(12, 12), QPointF(40, 40))
    p.setBrush(QColor(143, 233, 255, 60))
    p.setPen(pen(color, 8))
    p.drawEllipse(QPointF(-8, -8), 26, 26)
    p.setBrush(NO_BRUSH)
    p.setPen(pen("#ffffff", 4))
    p.drawArc(QRectF(-26, -26, 36, 36), 100 * 16, 60 * 16)
    p.restore()


def draw_bowtie(p: QPainter, r: QRectF, color: str = "#e0364a") -> None:
    if _draw_image_or(p, r, "bowtie"):
        return
    _begin(p, r)
    base = QColor(color)
    p.setPen(pen(base.darker(160), 3))
    p.setBrush(base)
    p.drawPolygon(QPolygonF([QPointF(-6, 0), QPointF(-46, -24), QPointF(-46, 24)]))
    p.drawPolygon(QPolygonF([QPointF(6, 0), QPointF(46, -24), QPointF(46, 24)]))
    p.setPen(pen(base.lighter(150), 2.5))
    for x in (-38, -28, -18):
        p.drawLine(QPointF(x, -(x + 46) * 0.5 + 2), QPointF(x, (x + 46) * 0.5 - 2))
    for x in (38, 28, 18):
        p.drawLine(QPointF(x, -(46 - x) * 0.5 + 2), QPointF(x, (46 - x) * 0.5 - 2))
    p.setPen(pen(base.darker(160), 3))
    p.setBrush(base.lighter(115))
    p.drawRoundedRect(QRectF(-10, -14, 20, 28), 6, 6)
    p.restore()


def draw_shoe(p: QPainter, r: QRectF) -> None:
    if _draw_image_or(p, r, "shoe"):
        return
    _begin(p, r)
    upper = QPainterPath()
    upper.moveTo(-44, 22)
    upper.lineTo(-44, -6)
    upper.cubicTo(-30, -10, -18, -2, -6, -22)
    upper.lineTo(8, -28)
    upper.lineTo(12, -14)
    upper.cubicTo(24, -4, 40, 2, 44, 12)
    upper.lineTo(44, 22)
    upper.closeSubpath()
    p.setPen(pen("#5a1010", 3))
    p.setBrush(QColor("#e0363a"))
    p.drawPath(upper)
    p.setBrush(QColor("#f4f4f4"))
    p.drawRoundedRect(QRectF(-47, 20, 94, 13), 6, 6)
    p.setPen(pen("#ffffff", 2.5))
    for i in range(3):
        p.drawLine(QPointF(-4 + i * 7, -14 + i * 3), QPointF(4 + i * 7, -10 + i * 3))
    p.setPen(NO_PEN)
    p.setBrush(QColor("#ffd23c"))
    p.drawPolygon(QPolygonF([QPointF(-24, 0), QPointF(-12, 0), QPointF(-18, 8),
                             QPointF(-10, 8), QPointF(-26, 20), QPointF(-21, 10),
                             QPointF(-28, 10)]))
    p.restore()


def draw_watch(p: QPainter, r: QRectF, second: Optional[int] = None) -> None:
    """Đồng hồ gây mê. `second` (0-59) vẽ thêm kim giây đỏ nhích từng nốt (chỉ bản vector)."""
    if _draw_image_or(p, r, "watch"):
        return
    _begin(p, r)
    p.setPen(pen("#1c2a4a", 2))
    p.setBrush(QColor("#3a4c78"))
    p.drawRoundedRect(QRectF(-12, -48, 24, 24), 5, 5)
    p.drawRoundedRect(QRectF(-12, 24, 24, 24), 5, 5)
    p.setPen(pen("#f3d36b", 5))
    p.setBrush(QColor("#16213d"))
    p.drawEllipse(QPointF(0, 0), 28, 28)
    p.setPen(pen("#8fe9ff", 2))
    for i in range(12):
        a = i * math.pi / 6
        p.drawLine(QPointF(math.sin(a) * 22, -math.cos(a) * 22),
                   QPointF(math.sin(a) * 25, -math.cos(a) * 25))
    p.setPen(pen("#ffffff", 3))
    p.drawLine(QPointF(0, 0), QPointF(0, -15))
    p.drawLine(QPointF(0, 0), QPointF(11, 5))
    if second is not None:
        angle = math.radians(second * 6)
        p.setPen(pen("#ff3b4e", 1.6))
        p.drawLine(QPointF(0, 0), QPointF(math.sin(angle) * 21, -math.cos(angle) * 21))
    p.setPen(NO_PEN)
    p.setBrush(QColor("#ff3b4e"))
    p.drawEllipse(QPointF(0, -34), 4, 4)
    p.restore()


def draw_ball(p: QPainter, r: QRectF) -> None:
    if _draw_image_or(p, r, "ball"):
        return
    _begin(p, r)
    grad = QRadialGradient(-12, -14, 60)
    grad.setColorAt(0, QColor("#ffffff"))
    grad.setColorAt(1, QColor("#c9d1de"))
    p.setPen(pen("#1a1f2b", 3))
    p.setBrush(QBrush(grad))
    p.drawEllipse(QPointF(0, 0), 40, 40)
    p.setBrush(QColor("#1a1f2b"))
    penta = star_polygon(0, 0, 14, 14, 5)
    p.drawPolygon(penta)
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        p.drawLine(QPointF(14 * math.cos(a), 14 * math.sin(a)),
                   QPointF(27 * math.cos(a), 27 * math.sin(a)))
        b = a + math.pi / 5
        p.drawEllipse(QPointF(37 * math.cos(b), 37 * math.sin(b)), 7, 7)
    p.restore()


def draw_pause(p: QPainter, r: QRectF, color: str = "#f3d36b") -> None:
    if _draw_image_or(p, r, "pause"):
        return
    _begin(p, r)
    p.setPen(NO_PEN)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(-26, -34, 20, 68), 6, 6)
    p.drawRoundedRect(QRectF(6, -34, 20, 68), 6, 6)
    p.restore()


def draw_lightning(p: QPainter, points) -> None:
    """Vẽ tia sét (đa tuyến) có quầng sáng. `points` là list[QPointF]."""
    path = QPainterPath(points[0])
    for pt in points[1:]:
        path.lineTo(pt)
    p.setBrush(NO_BRUSH)
    for width, alpha in ((14, 35), (8, 70), (4, 255)):
        p.setPen(pen(QColor(255, 255, 255, alpha), width))
        p.drawPath(path)


def draw_conan(p: QPainter, r: QRectF, mood: str = "neutral", angle: float = 0.0) -> None:
    """Conan vẽ tay: mood = neutral | think | shake | shock | happy."""
    if _draw_image_or(p, r, f"conan_{mood}", rotate=angle):
        return
    if _draw_image_or(p, r, "conan", rotate=angle):
        return
    _begin(p, r)
    p.rotate(angle)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#2a4fa3"))                       # áo vest xanh
    body = QPainterPath()
    body.moveTo(-42, 50)
    body.cubicTo(-40, 28, -22, 24, 0, 24)
    body.cubicTo(22, 24, 40, 28, 42, 50)
    body.closeSubpath()
    p.drawPath(body)
    p.setBrush(QColor("#f6f6f6"))
    p.drawPolygon(QPolygonF([QPointF(-12, 24), QPointF(12, 24), QPointF(0, 40)]))
    p.setBrush(QColor("#e0364a"))                       # nơ đỏ
    p.drawPolygon(QPolygonF([QPointF(0, 33), QPointF(-12, 27), QPointF(-12, 39)]))
    p.drawPolygon(QPolygonF([QPointF(0, 33), QPointF(12, 27), QPointF(12, 39)]))
    p.setBrush(QColor("#ffdcb8"))                       # đầu
    p.drawEllipse(QPointF(0, -2), 31, 32)
    p.setBrush(QColor("#2b1a12"))                       # tóc
    hair = QPainterPath()
    hair.moveTo(-31, -4)
    hair.cubicTo(-34, -40, -12, -46, 0, -44)
    hair.cubicTo(14, -46, 34, -38, 31, -4)
    hair.lineTo(22, -14)
    for x, y in ((14, -20), (6, -12), (-2, -22), (-10, -12), (-18, -20), (-22, -12)):
        hair.lineTo(x, y)
    hair.closeSubpath()
    p.drawPath(hair)
    p.drawPolygon(QPolygonF([QPointF(-4, -46), QPointF(4, -58), QPointF(10, -45)]))  # ahoge
    glare = mood == "think"
    p.setPen(pen("#1b1b1b", 3.2))
    p.setBrush(QColor("#ffffff") if glare else QColor(255, 255, 255, 70))
    p.drawEllipse(QPointF(-13, -1), 11, 11)
    p.drawEllipse(QPointF(13, -1), 11, 11)
    p.drawLine(QPointF(-2, -3), QPointF(2, -3))
    if not glare:
        p.setPen(NO_PEN)
        p.setBrush(QColor("#1b1b1b"))
        ry = 5.5 if mood == "shock" else 3.5
        p.drawEllipse(QPointF(-13, -1), 3.2, ry)
        p.drawEllipse(QPointF(13, -1), 3.2, ry)
    p.setBrush(NO_BRUSH)
    p.setPen(pen("#7a3b2a", 2.6))
    if mood == "happy" or mood == "think":
        p.drawArc(QRectF(-8, 8, 16, 11), 200 * 16, 140 * 16)
    elif mood == "shake":
        p.drawArc(QRectF(-8, 14, 16, 9), 20 * 16, 140 * 16)
        p.setPen(pen("#8fd3ff", 2))
        p.setBrush(QColor("#8fd3ff"))
        p.drawEllipse(QPointF(30, -22), 3, 5)
    elif mood == "shock":
        p.setBrush(QColor("#7a3b2a"))
        p.drawEllipse(QPointF(0, 15), 4, 5.5)
    else:
        p.drawLine(QPointF(-5, 14), QPointF(5, 14))
    p.restore()


def draw_villain(p: QPainter, r: QRectF, alpha: int = 255) -> None:
    """Bóng đen hung thủ trong Conan: toàn đen, mắt và nụ cười trắng."""
    if _draw_image_or(p, r, "villain", opacity=alpha / 255.0):
        return
    _begin(p, r)
    p.setPen(NO_PEN)
    p.setBrush(QColor(0, 0, 0, alpha))
    body = QPainterPath()
    body.moveTo(-48, 50)
    body.cubicTo(-46, 22, -26, 14, 0, 14)
    body.cubicTo(26, 14, 46, 22, 48, 50)
    body.closeSubpath()
    p.drawPath(body)
    p.drawEllipse(QPointF(0, -14), 30, 34)
    white = QColor(255, 255, 255, alpha)
    p.setBrush(white)
    for sign in (-1, 1):
        eye = QPainterPath()
        eye.moveTo(sign * 6, -12)
        eye.quadTo(sign * 16, -22, sign * 25, -14)
        eye.quadTo(sign * 16, -8, sign * 6, -12)
        p.drawPath(eye)
    grin = QPainterPath()
    grin.moveTo(-20, 2)
    grin.quadTo(0, 28, 20, 2)
    grin.quadTo(0, 14, -20, 2)
    p.drawPath(grin)
    p.setPen(pen(QColor(0, 0, 0, alpha), 1.6))
    for x in range(-14, 15, 7):
        p.drawLine(QPointF(x, 6 + (14 - abs(x)) * 0.1), QPointF(x, 12 + (14 - abs(x)) * 0.2))
    p.restore()


_HAIR = ["#2b1a12", "#6b3a1c", "#d9a441", "#1c1c28", "#8b2e2e", "#4a3a2a"]
_SHIRT = ["#2c6bd6", "#c0392b", "#2e8b57", "#8e44ad", "#e08a1e", "#34495e"]
_SKIN = ["#ffdcb8", "#f2c79c", "#e3b087", "#c99a73"]


def draw_avatar(p: QPainter, r: QRectF, name: str) -> None:
    """Chân dung dự phòng, sinh theo tên nên mỗi nhân vật một vẻ khác nhau."""
    h = zlib.crc32(name.encode("utf-8"))
    hair, shirt = QColor(_HAIR[h % 6]), QColor(_SHIRT[(h >> 3) % 6])
    skin, style = QColor(_SKIN[(h >> 6) % 4]), (h >> 9) % 3
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(r, 8, 8)
    p.setClipPath(clip)
    bg = QLinearGradient(r.topLeft(), r.bottomLeft())
    bg.setColorAt(0, QColor("#3b5a93"))
    bg.setColorAt(1, QColor("#16253f"))
    p.fillRect(r, bg)
    _begin(p, r)
    p.setPen(NO_PEN)
    p.setBrush(shirt)
    p.drawEllipse(QPointF(0, 58), 46, 30)
    p.setBrush(skin)
    p.drawRect(QRectF(-7, 18, 14, 14))
    if style == 1:                                       # tóc dài phía sau
        p.setBrush(hair)
        p.drawRoundedRect(QRectF(-31, -34, 62, 74), 22, 22)
    p.setBrush(skin)
    p.drawEllipse(QPointF(0, 0), 25, 29)
    p.setBrush(hair)
    cap = QPainterPath()
    cap.moveTo(-27, -4)
    cap.cubicTo(-30, -38, 30, -38, 27, -4)
    cap.cubicTo(18, -18, -18, -18, -27, -4)
    p.drawPath(cap)
    if style == 2:                                       # tóc dựng
        for x in (-16, -6, 6, 16):
            p.drawPolygon(QPolygonF([QPointF(x - 6, -26), QPointF(x, -42), QPointF(x + 6, -26)]))
    p.setBrush(QColor("#1b1b1b"))
    p.drawEllipse(QPointF(-9, 2), 2.8, 3.4)
    p.drawEllipse(QPointF(9, 2), 2.8, 3.4)
    p.setBrush(NO_BRUSH)
    p.setPen(pen("#7a3b2a", 2))
    p.drawArc(QRectF(-7, 10, 14, 9), 200 * 16, 140 * 16)
    p.restore()
    p.restore()