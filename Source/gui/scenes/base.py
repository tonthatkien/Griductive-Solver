"""Lớp cơ sở `Scene` + bộ hàm vẽ dùng chung cho các cảnh nền theo địa điểm. (Scope F)

Mỗi cảnh gồm hai lớp:
  - `paint_static`  : vẽ MỘT lần rồi cache thành QPixmap (trời, nhà cửa, đồ vật...).
  - `paint_dynamic` : vẽ mỗi khung hình (mưa, ánh đèn nhấp nháy, hạt bụi, tia chớp...).
Toạ độ dùng phân số của w/h để cảnh co giãn theo cửa sổ.
"""
import math
import random
from typing import List, Optional, Sequence, Tuple, Union

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPixmap, QPolygonF,
                           QRadialGradient)

from gui.icons import NO_BRUSH, NO_PEN, pen

Color = Union[str, QColor]


def col(color: Color, alpha: Optional[float] = None) -> QColor:
    """QColor từ chuỗi/QColor; alpha (0..255) tuỳ chọn, tự kẹp trong khoảng hợp lệ."""
    c = QColor(color)
    if alpha is not None:
        c.setAlpha(int(max(0, min(255, alpha))))
    return c


class Scene:
    """Một cảnh nền. Lớp con ghi đè `setup`, `paint_static`, `paint_dynamic`."""

    name = "scene"
    seed = 1
    accent = "#fff1c8"        # màu quầng sáng khi phá án đúng (lớp con có thể đổi)

    def __init__(self) -> None:
        self._pix = None
        self._key: tuple = ()
        self._good_at = self._bad_at = -999.0     # thời điểm (giây của nền) lần phá đúng / kết luận sai gần nhất
        self.dawn = 0.0                           # 0 = đêm, 1 = bình minh
        self.setup()

    def setup(self) -> None:
        """Sinh dữ liệu ngẫu nhiên cố định (vị trí sao, giọt mưa...) bằng random.Random(self.seed)."""

    def fresh_rng(self) -> random.Random:
        """RNG mới cùng hạt giống: vẽ lại lớp tĩnh sau khi đổi cỡ cửa sổ vẫn ra đúng bố cục cũ."""
        return random.Random(self.seed)

    def paint_static(self, p: QPainter, w: float, h: float) -> None:
        vgrad(p, w, h, [(0, "#050a18"), (1, "#1b3157")])

    def paint_dynamic(self, p: QPainter, w: float, h: float, t: float) -> None:
        """Lớp động, vẽ mỗi khung hình."""

    # ---- phản ứng với trò chơi (do NightBackdrop gọi) ----------------------------------------
    def on_good(self, t: float) -> None:
        self._good_at = t

    def on_bad(self, t: float) -> None:
        self._bad_at = t

    def set_dawn(self, k: float) -> None:
        self.dawn = max(0.0, min(1.0, k))

    def reset_mood(self) -> None:
        self._good_at = self._bad_at = -999.0
        self.dawn = 0.0

    def good_k(self, t: float, dur: float = 1.1) -> float:
        """1 lúc vừa phá đúng, tắt dần về 0 sau `dur` giây. Cảnh dùng để tự làm nổi bật mình."""
        return max(0.0, 1.0 - (t - self._good_at) / dur) ** 2

    def bad_k(self, t: float, dur: float = 2.0) -> float:
        return max(0.0, 1.0 - (t - self._bad_at) / dur)

    def _paint_mood(self, p: QPainter, w: float, h: float, t: float) -> None:
        """Lớp phủ chung: sáng lên một nhịp khi đúng, chập chờn rồi tối khi sai, ửng bình minh khi thắng."""
        full = QRectF(0, 0, w, h)
        gk = self.good_k(t)
        if gk > 0:
            glow(p, w / 2, h / 2, max(w, h) * 0.65, self.accent, 120 * gk)
            p.fillRect(full, col(self.accent, 26 * gk))
        bk = self.bad_k(t)
        if bk > 0:
            flick = 1.0 if int(t * 9) % 3 else 0.25      # đèn chập chờn rồi tắt dần
            p.fillRect(full, col("#000000", 170 * bk * flick))
        if self.dawn > 0:
            d = self.dawn
            sky = QLinearGradient(0, 0, 0, h)
            sky.setColorAt(0, col("#3a5a9a", 90 * d))
            sky.setColorAt(0.6, col("#ff9a6b", 120 * d))
            sky.setColorAt(1, col("#ffd27a", 170 * d))
            p.fillRect(full, QBrush(sky))
            sx, sy, sr = w * 0.5, h * (1.05 - 0.22 * d), min(w, h) * 0.05
            glow(p, sx, sy, max(w, h) * 0.55, "#ffcf8a", 190 * d)
            p.setPen(NO_PEN)
            p.setBrush(col("#fff3c4", 255 * d))
            p.drawEllipse(QPointF(sx, sy), sr, sr)

    def paint(self, p: QPainter, w: float, h: float, t: float, dpr: float = 1.0) -> None:
        key = (int(w), int(h), dpr)
        if self._key != key:
            pix = QPixmap(int(w * dpr) + 1, int(h * dpr) + 1)
            pix.setDevicePixelRatio(dpr)
            pix.fill(Qt.GlobalColor.transparent)
            g = QPainter(pix)
            g.setRenderHint(QPainter.RenderHint.Antialiasing)
            g.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            self.paint_static(g, w, h)
            g.end()
            self._pix, self._key = pix, key
        p.drawPixmap(QPointF(0, 0), self._pix)
        self.paint_dynamic(p, w, h, t)
        self._paint_mood(p, w, h, t)


# ---- hàm vẽ dùng chung ------------------------------------------------------------------
def vgrad(p: QPainter, w: float, h: float, stops: Sequence[Tuple[float, Color]],
          y0: float = 0.0, y1: float = 1.0) -> None:
    """Đổ gradient dọc cho dải từ y0 đến y1 (phân số chiều cao); mặc định cả khung."""
    g = QLinearGradient(0, y0 * h, 0, y1 * h)
    for pos, color in stops:
        g.setColorAt(pos, col(color))
    p.fillRect(QRectF(0, y0 * h, w, (y1 - y0) * h), QBrush(g))


def glow(p: QPainter, cx: float, cy: float, r: float, color: Color, alpha: float = 120) -> None:
    """Quầng sáng tròn mờ dần ra ngoài."""
    c = QPointF(cx, cy)
    g = QRadialGradient(c, max(1.0, r))
    g.setColorAt(0, col(color, alpha))
    g.setColorAt(1, col(color, 0))
    p.setPen(NO_PEN)
    p.setBrush(QBrush(g))
    p.drawEllipse(c, r, r)


def egl(p: QPainter, cx: float, cy: float, rx: float, ry: float, color: Color, alpha: float = 60) -> None:
    """Quầng sáng/đám mây dạng elip (sương mù, mây, vệt khói)."""
    p.save()
    p.translate(cx, cy)
    p.scale(1.0, max(0.01, ry / max(1.0, rx)))
    glow(p, 0, 0, rx, color, alpha)
    p.restore()


def poly(p: QPainter, pts: Sequence[Tuple[float, float]], color: Color, edge: Union[Color, None] = None,
         edge_w: float = 1.2) -> None:
    p.setPen(pen(col(edge), edge_w) if edge else NO_PEN)
    p.setBrush(col(color))
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


def beam(p: QPainter, ox: float, oy: float, angle: float, spread: float, length: float,
         color: Color, alpha: float = 50) -> None:
    """Chùm sáng hình quạt từ (ox, oy), hướng `angle` (radian, y hướng xuống), mờ dần theo chiều dài."""
    o = QPointF(ox, oy)
    t1 = QPointF(ox + math.cos(angle - spread) * length, oy + math.sin(angle - spread) * length)
    t2 = QPointF(ox + math.cos(angle + spread) * length, oy + math.sin(angle + spread) * length)
    g = QLinearGradient(o, QPointF(ox + math.cos(angle) * length, oy + math.sin(angle) * length))
    g.setColorAt(0, col(color, alpha))
    g.setColorAt(1, col(color, 0))
    p.setPen(NO_PEN)
    p.setBrush(QBrush(g))
    p.drawPolygon(QPolygonF([o, t1, t2]))


def gear(p: QPainter, cx: float, cy: float, r: float, teeth: int, angle: float,
         color: Color, edge: Color) -> None:
    pts = []
    for i in range(teeth * 4):
        a = angle + i * 2 * math.pi / (teeth * 4)
        rr = r if i % 4 in (0, 1) else r * 0.8
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    poly(p, pts, color, edge, 1.4)
    p.setBrush(col("#04070d"))
    p.drawEllipse(QPointF(cx, cy), r * 0.22, r * 0.22)


def make_drops(rng: random.Random, n: int) -> List[Tuple[float, float, float, float]]:
    """Giọt mưa: (x, pha, tốc độ, độ dài)."""
    return [(rng.uniform(-0.1, 1.0), rng.random(), rng.uniform(0.7, 1.4), rng.uniform(9, 22))
            for _ in range(n)]


def rain(p: QPainter, w: float, h: float, t: float, drops, color: Color = "#9fd0ff",
         alpha: float = 90, wind: float = 0.3) -> None:
    p.setPen(pen(col(color, alpha), 1.1))
    for x, ph, sp, ln in drops:
        y = ((t * sp * 0.9 + ph) % 1.0) * (h + ln) - ln
        xx = x * w + wind * y * 0.35
        p.drawLine(QPointF(xx, y), QPointF(xx - wind * ln * 0.35, y - ln))


def make_motes(rng: random.Random, n: int) -> List[Tuple[float, float, float, float, float]]:
    """Hạt bụi / đom đóm: (x, y, pha, tốc độ, cỡ)."""
    return [(rng.random(), rng.random(), rng.uniform(0, 6.28), rng.uniform(0.5, 1.5), rng.uniform(1.0, 2.4))
            for _ in range(n)]


def dust(p: QPainter, w: float, h: float, t: float, motes, color: Color = "#ffe9b0",
         alpha: float = 150, rise: float = 0.012) -> None:
    p.setPen(NO_PEN)
    for x, y, ph, sp, sz in motes:
        yy = (y - t * rise * sp) % 1.0
        xx = x + 0.015 * math.sin(t * sp * 0.7 + ph)
        a = alpha * (0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * sp + ph)))
        p.setBrush(col(color, a))
        p.drawEllipse(QPointF(xx * w, yy * h), sz, sz)


def fog(p: QPainter, w: float, h: float, t: float, color: Color = "#9fb4d8", bands: int = 4,
        alpha: float = 24, y: float = 0.75) -> None:
    """Các dải sương trôi ngang chậm."""
    for i in range(bands):
        x = (((t * 0.012 * (1 + i * 0.35)) + i * 0.29) % 1.5 - 0.25) * w
        egl(p, x, h * (y + 0.04 * math.sin(i * 2.0 + t * 0.2)), w * 0.38, h * 0.07, color, alpha)


def lightning(t: float, period: float = 9.0, offset: float = 0.0) -> float:
    """Cường độ chớp 0..1: hai lần loé liên tiếp mỗi chu kỳ."""
    u = (t + offset) % period
    return max(max(0.0, 1 - abs(u - 0.30) / 0.08), 0.6 * max(0.0, 1 - abs(u - 0.52) / 0.06))


def vignette(p: QPainter, w: float, h: float, edge: float = 150, center: float = 0) -> None:
    g = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w, h) * 0.55)
    g.setColorAt(0, col("#000000", center))
    g.setColorAt(0.55, col("#000000", center * 0.7))
    g.setColorAt(1, col("#000000", edge))
    p.fillRect(QRectF(0, 0, w, h), QBrush(g))


def strokes(p: QPainter, color: Color, width: float = 1.0) -> None:
    """Đặt bút vẽ nét, không tô."""
    p.setBrush(NO_BRUSH)
    p.setPen(pen(col(color), width))
