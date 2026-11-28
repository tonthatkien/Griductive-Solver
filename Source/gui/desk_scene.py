"""Cảnh bàn thám tử về đêm: nền gỗ tối + đèn bàn + các vật dụng vẽ bằng QPainter. (Scope F)

Dùng chung cho trang chủ (home_page.py) và màn Cách chơi (tutorial_page.py).
Mỗi hàm draw_* nhận hình chữ nhật `r` có TÂM Ở GỐC (0, 0): người gọi tự translate/rotate trước.
Không chứa luật chơi.
"""
import math
import random
from typing import Dict

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath, QPixmap, QPolygonF,
                           QRadialGradient)

from gui import icons, theme
from gui.draw_utils import ALIGN_CENTER, draw_fitted
from gui.icons import NO_BRUSH, NO_PEN, pen

_STATIC: Dict[str, object] = {"key": None, "pix": None}


def _wood(w: int, h: int, dpr: float) -> QPixmap:
    """Lớp tĩnh (vẽ một lần cho mỗi kích thước): mặt bàn gỗ sẫm, vân gỗ, tối góc."""
    pix = QPixmap(int(w * dpr) + 1, int(h * dpr) + 1)
    pix.setDevicePixelRatio(dpr)
    g = QPainter(pix)
    g.setRenderHint(QPainter.RenderHint.Antialiasing)
    base = QLinearGradient(0, 0, 0, h)
    base.setColorAt(0.0, QColor("#1d120a"))
    base.setColorAt(0.55, QColor("#150c06"))
    base.setColorAt(1.0, QColor("#0b0603"))
    g.fillRect(0, 0, w, h, base)
    rng = random.Random(11)
    g.setBrush(NO_BRUSH)
    for _ in range(54):                                   # vân gỗ: các đường lượn ngang rất mờ
        y0, amp = rng.uniform(0, h), rng.uniform(1.5, 7.0)
        wave, phase = rng.uniform(90, 260), rng.uniform(0, 6.28)
        shade = QColor(0, 0, 0, rng.randint(14, 34)) if rng.random() < 0.6 else QColor(255, 214, 160, rng.randint(5, 12))
        g.setPen(pen(shade, rng.uniform(0.8, 2.2)))
        path = QPainterPath(QPointF(0, y0))
        for x in range(0, w + 40, 40):
            path.lineTo(x, y0 + amp * math.sin(x / wave + phase))
        g.drawPath(path)
    vignette = QRadialGradient(QPointF(w * 0.36, h * 0.42), max(w, h) * 0.82)
    vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
    vignette.setColorAt(0.5, QColor(0, 0, 0, 40))
    vignette.setColorAt(1.0, QColor(0, 0, 0, 215))
    g.fillRect(0, 0, w, h, vignette)
    g.end()
    return pix


def paint_desk(p: QPainter, rect: QRectF, t: float, lamp: float = 1.0) -> None:
    """Vẽ nền bàn + vùng sáng của đèn bàn (nhấp nháy nhẹ) + bụi bay trong ánh đèn.

    t: giờ chạy (giây); lamp: độ sáng 0..1 của đèn (dùng cho cảnh bật đèn lúc mở màn)."""
    w, h = int(rect.width()), int(rect.height())
    dpr = p.device().devicePixelRatioF() if hasattr(p.device(), "devicePixelRatioF") else 1.0
    key = (w, h, dpr)
    if _STATIC["key"] != key:
        _STATIC["key"], _STATIC["pix"] = key, _wood(w, h, dpr)
    p.drawPixmap(0, 0, _STATIC["pix"])
    flicker = 0.93 + 0.07 * math.sin(t * 7.3) * math.sin(t * 2.1)
    level = max(0.0, min(1.0, lamp)) * flicker
    pool = QRadialGradient(QPointF(w * 0.30, h * 0.40), max(w, h) * 0.75)
    pool.setColorAt(0.0, QColor(255, 196, 120, int(78 * level)))
    pool.setColorAt(0.45, QColor(255, 170, 90, int(30 * level)))
    pool.setColorAt(1.0, QColor(255, 150, 80, 0))
    p.fillRect(QRectF(0, 0, w, h), pool)
    rng = random.Random(5)                                # bụi bay chậm trong vùng sáng
    p.setPen(NO_PEN)
    for _ in range(22):
        bx, by = rng.uniform(0.05, 0.75) * w, rng.uniform(0.05, 0.85) * h
        sp, ph = rng.uniform(0.15, 0.5), rng.uniform(0, 6.28)
        x = bx + 18 * math.sin(t * sp + ph)
        y = by + 12 * math.cos(t * sp * 0.8 + ph)
        p.setBrush(QColor(255, 226, 170, int((26 + 22 * math.sin(t * sp * 2 + ph)) * level)))
        p.drawEllipse(QPointF(x, y), 1.6, 1.6)
    _paint_lamp(p, w, h, level)


def _paint_lamp(p: QPainter, w: int, h: int, level: float) -> None:
    """Đèn bàn ở góc trên trái: chao đèn, cần đèn và quầng bóng đèn."""
    s = min(w, h * 1.4)
    head = QPointF(w * 0.075, h * 0.085)
    p.save()
    p.setPen(pen("#1b1b20", s * 0.012))
    p.drawLine(QPointF(-4, h * 0.30), head + QPointF(s * 0.02, s * 0.015))           # cần đèn
    shade = QPolygonF([head + QPointF(-s * 0.075, s * 0.045), head + QPointF(s * 0.075, s * 0.045),
                       head + QPointF(s * 0.035, -s * 0.045), head + QPointF(-s * 0.035, -s * 0.045)])
    grad = QLinearGradient(head.x() - s * 0.075, 0, head.x() + s * 0.075, 0)
    grad.setColorAt(0.0, QColor("#2c2f38"))
    grad.setColorAt(0.5, QColor("#4b505d"))
    grad.setColorAt(1.0, QColor("#1d1f26"))
    p.setBrush(grad)
    p.setPen(pen("#0d0e12", 2))
    p.drawPolygon(shade)
    bulb = QRadialGradient(head + QPointF(0, s * 0.05), s * 0.07)
    bulb.setColorAt(0.0, QColor(255, 236, 190, int(255 * level)))
    bulb.setColorAt(1.0, QColor(255, 190, 110, 0))
    p.setPen(NO_PEN)
    p.setBrush(bulb)
    p.drawEllipse(head + QPointF(0, s * 0.05), s * 0.07, s * 0.07)
    p.restore()


# ---- các vật dụng (r có tâm ở gốc) ---------------------------------------------------------
def _shadow(p: QPainter, r: QRectF, grow: float = 0.0) -> None:
    p.save()
    p.setPen(NO_PEN)
    for spread, alpha in ((14, 22), (8, 34), (3, 50)):
        p.setBrush(QColor(0, 0, 0, alpha))
        p.drawRoundedRect(r.translated(5, 9).adjusted(-spread + grow, -spread + grow, spread - grow, spread - grow),
                          10, 10)
    p.restore()


def draw_folder(p: QPainter, r: QRectF, t: float) -> None:
    """Hồ sơ vụ án: bìa giấy manila, tờ giấy thò ra, dấu đỏ TUYỆT MẬT."""
    _shadow(p, r)
    paper = QRectF(r.left() + r.width() * 0.07, r.top() - r.height() * 0.02, r.width() * 0.82, r.height() * 0.5)
    p.save()
    p.translate(paper.center())
    p.rotate(-2.0)
    p.setPen(pen("#9a8f72", 1.5))
    p.setBrush(QColor("#eee6cf"))
    p.drawRect(QRectF(-paper.width() / 2, -paper.height() / 2, paper.width(), paper.height()))
    p.setPen(pen(QColor(60, 50, 30, 90), 2))
    for i in range(1, 5):
        y = -paper.height() / 2 + paper.height() * i * 0.16
        p.drawLine(QPointF(-paper.width() * 0.4, y), QPointF(paper.width() * (0.4 - 0.05 * (i % 2)), y))
    p.restore()
    tab = QRectF(r.left(), r.top() + r.height() * 0.04, r.width() * 0.30, r.height() * 0.12)
    body = QRectF(r.left(), r.top() + r.height() * 0.12, r.width(), r.height() * 0.88)
    tone = QLinearGradient(0, body.top(), 0, body.bottom())
    tone.setColorAt(0.0, QColor("#d9b873"))
    tone.setColorAt(1.0, QColor("#a98445"))
    p.setPen(pen("#5e4522", 2))
    p.setBrush(tone)
    p.drawRoundedRect(tab, 6, 6)
    p.drawRoundedRect(body, 8, 8)
    p.setPen(pen(QColor(80, 55, 20, 90), 2))
    p.drawLine(QPointF(body.left() + 8, body.top() + 10), QPointF(body.right() - 8, body.top() + 10))
    strip = QRectF(body.left() + body.width() * 0.08, body.top() + body.height() * 0.58,
                   body.width() * 0.52, body.height() * 0.2)
    p.setPen(pen("#8a7a52", 1.5))
    p.setBrush(QColor("#f3ecd4"))
    p.drawRect(strip)
    draw_fitted(p, strip.adjusted(8, 3, -8, -3), "HỒ SƠ ĐIỀU TRA", theme.FONT_CLUE_TITLE, 18, 8,
                theme.INK, bold=True, fl=ALIGN_CENTER)
    p.save()                                                 # dấu đỏ nghiêng
    p.translate(body.center().x() + body.width() * 0.2, body.top() + body.height() * 0.34)
    p.rotate(-13)
    box = QRectF(-body.width() * 0.2, -body.height() * 0.1, body.width() * 0.4, body.height() * 0.2)
    p.setBrush(NO_BRUSH)
    p.setPen(pen(QColor(200, 30, 45, 215), 4))
    p.drawRoundedRect(box, 5, 5)
    draw_fitted(p, box.adjusted(6, 2, -6, -2), "TUYỆT MẬT", theme.FONT_CLUE_TITLE, 26, 9,
                QColor(210, 35, 50, 225), bold=True, fl=ALIGN_CENTER)
    p.restore()


def draw_notebook(p: QPainter, r: QRectF, t: float) -> None:
    """Sổ tay lò xo bìa xanh đậm với nhãn SỔ TAY và kính lúp nhỏ."""
    _shadow(p, r)
    cover = QLinearGradient(r.left(), 0, r.right(), 0)
    cover.setColorAt(0.0, QColor("#16294a"))
    cover.setColorAt(1.0, QColor("#22407a"))
    p.setPen(pen("#0c1730", 2.5))
    p.setBrush(cover)
    p.drawRoundedRect(r, 8, 8)
    p.setPen(pen(QColor(120, 160, 230, 70), 1.5))
    p.setBrush(NO_BRUSH)
    p.drawRoundedRect(r.adjusted(7, 7, -7, -7), 5, 5)
    rings = 9
    for i in range(rings):                                    # gáy lò xo
        y = r.top() + r.height() * (i + 0.7) / (rings + 0.4)
        p.setPen(pen("#c8ccd6", 3.2))
        p.drawArc(QRectF(r.left() - 7, y - 5, 16, 10), 270 * 16, 180 * 16)
    plate = QRectF(r.left() + r.width() * 0.2, r.top() + r.height() * 0.58, r.width() * 0.66, r.height() * 0.2)
    p.setPen(pen("#d9b873", 1.8))
    p.setBrush(QColor("#efe3bd"))
    p.drawRoundedRect(plate, 4, 4)
    draw_fitted(p, plate.adjusted(6, 2, -6, -2), "SỔ TAY", theme.FONT_CLUE_TITLE, 20, 8, theme.INK,
                bold=True, fl=ALIGN_CENTER)
    icons.draw_magnifier(p, QRectF(r.center().x() - r.width() * 0.05 - r.width() * 0.2, r.top() + r.height() * 0.14,
                                   r.width() * 0.5, r.width() * 0.5))


def draw_radio(p: QPainter, r: QRectF, t: float, on: bool = True) -> None:
    """Radio cũ: loa chấm, mặt số, đèn LED và thanh cân bằng âm nhảy theo nhạc (khi bật)."""
    _shadow(p, r)
    p.setPen(pen("#08080a", 2.5))
    tone = QLinearGradient(0, r.top(), 0, r.bottom())
    tone.setColorAt(0.0, QColor("#3a3a42"))
    tone.setColorAt(1.0, QColor("#1c1c22"))
    p.setBrush(tone)
    p.drawRoundedRect(r, 12, 12)
    p.setPen(pen("#2a2a30", 3))
    p.drawLine(QPointF(r.right() - r.width() * 0.12, r.top()), QPointF(r.right() + r.width() * 0.04, r.top() - r.height() * 0.45))
    grille = QRectF(r.left() + r.width() * 0.07, r.top() + r.height() * 0.16, r.width() * 0.42, r.height() * 0.68)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#0d0d10"))
    p.drawRoundedRect(grille, 6, 6)
    p.setBrush(QColor(150, 150, 165, 150))
    for ix in range(7):
        for iy in range(6):
            p.drawEllipse(QPointF(grille.left() + grille.width() * (ix + 0.7) / 7.4,
                                  grille.top() + grille.height() * (iy + 0.7) / 6.4), 1.8, 1.8)
    screen = QRectF(r.left() + r.width() * 0.54, r.top() + r.height() * 0.16, r.width() * 0.38, r.height() * 0.34)
    p.setBrush(QColor("#0b1a10"))
    p.drawRoundedRect(screen, 4, 4)
    bars = 7
    for i in range(bars):
        k = (0.5 + 0.5 * math.sin(t * (3.0 + i * 0.7) + i)) if on else 0.08
        bw = screen.width() / (bars * 1.5)
        x = screen.left() + screen.width() * 0.08 + i * bw * 1.5
        hh = (screen.height() - 6) * (0.15 + 0.8 * k)
        p.setBrush(QColor(57, 255, 20, 210) if on else QColor(57, 255, 20, 50))
        p.drawRect(QRectF(x, screen.bottom() - 3 - hh, bw, hh))
    dial = QPointF(r.left() + r.width() * 0.72, r.top() + r.height() * 0.74)
    p.setBrush(QColor("#101014"))
    p.setPen(pen("#8a8a96", 2))
    p.drawEllipse(dial, r.height() * 0.16, r.height() * 0.16)
    p.setPen(pen("#e2b947", 2.4))
    ang = math.radians(-50 if on else 130)
    p.drawLine(dial, dial + QPointF(math.cos(ang), math.sin(ang)) * r.height() * 0.13)
    p.setPen(NO_PEN)
    led = QColor(255, 60, 60) if on else QColor(90, 30, 30)
    if on:
        led.setAlpha(int(150 + 105 * math.sin(t * 3) ** 2))
    p.setBrush(led)
    p.drawEllipse(QPointF(r.left() + r.width() * 0.57, r.top() + r.height() * 0.62), 3.6, 3.6)


def draw_medal(p: QPainter, r: QRectF, t: float, ratio: float = 0.0) -> None:
    """Huy chương: dải ruy băng + đĩa vàng, càng nhiều sao thì càng sáng."""
    ratio = max(0.0, min(1.0, ratio))
    p.save()
    p.setPen(pen("#1a0e0a", 1.5))
    for sign, color in ((-1, "#b3202f"), (1, "#1f5fbf")):
        ribbon = QPolygonF([QPointF(sign * r.width() * 0.04, r.top()), QPointF(sign * r.width() * 0.36, r.top()),
                            QPointF(sign * r.width() * 0.2, r.center().y()), QPointF(sign * -r.width() * 0.0, r.center().y())])
        p.setBrush(QColor(color))
        p.drawPolygon(ribbon)
    center = QPointF(0, r.height() * 0.2)
    rad = r.width() * 0.4
    disc = QRadialGradient(center - QPointF(rad * 0.3, rad * 0.3), rad * 1.4)
    disc.setColorAt(0.0, QColor("#fff0a8"))
    disc.setColorAt(1.0, QColor("#b8871c"))
    dim = 0.35 + 0.65 * ratio
    p.setOpacity(p.opacity() * dim)
    p.setPen(pen("#6b4a10", 3))
    p.setBrush(disc)
    p.drawEllipse(center, rad, rad)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#7a5410"))
    p.drawPolygon(icons.star_polygon(center.x(), center.y(), rad * 0.62, rad * 0.26))
    p.restore()


def draw_photo(p: QPainter, r: QRectF, t: float) -> None:
    """Ảnh ghim trên bàn: bóng đen hung thủ, viền đỏ thở nhẹ, dấu hỏi và hai miếng băng dính."""
    _shadow(p, r)
    p.setPen(pen("#8a826c", 1.5))
    p.setBrush(QColor("#e6dfc9"))
    p.drawRect(r)
    inner = QRectF(r.left() + r.width() * 0.08, r.top() + r.height() * 0.08, r.width() * 0.84, r.height() * 0.7)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#0b0d14"))
    p.drawRect(inner)
    icons.draw_villain(p, inner.adjusted(6, 6, -6, -4), 235)
    pulse = 0.5 + 0.5 * math.sin(t * 1.8)
    p.setBrush(NO_BRUSH)
    p.setPen(pen(QColor(255, 40, 60, int(70 + 120 * pulse)), 3))
    p.drawRect(inner)
    caption = QRectF(r.left() + 6, inner.bottom() + 2, r.width() - 12, r.bottom() - inner.bottom() - 4)
    draw_fitted(p, caption, "???", theme.FONT_CLUE_TITLE, 22, 8, "#7a1020", bold=True, fl=ALIGN_CENTER)
    p.setPen(NO_PEN)
    p.setBrush(QColor(240, 215, 120, 150))
    for dx in (-0.32, 0.32):
        p.save()
        p.translate(r.center().x() + r.width() * dx, r.top())
        p.rotate(-12 if dx < 0 else 12)
        p.drawRect(QRectF(-r.width() * 0.13, -6, r.width() * 0.26, 13))
        p.restore()


def draw_cup(p: QPainter, r: QRectF, t: float) -> None:
    """Tách cà phê nhìn từ trên xuống, có làn khói mảnh."""
    _shadow(p, r.adjusted(r.width() * 0.1, r.height() * 0.1, -r.width() * 0.1, -r.height() * 0.1))
    rad = min(r.width(), r.height()) * 0.38
    p.setPen(pen("#8d8570", 2))
    p.setBrush(QColor("#e9e3d2"))
    p.drawEllipse(QPointF(0, 0), rad, rad)
    p.setPen(pen("#d9d2bd", 5))
    p.drawArc(QRectF(rad * 0.7, -rad * 0.35, rad * 0.9, rad * 0.7), -80 * 16, 160 * 16)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#2a1608"))
    p.drawEllipse(QPointF(0, 0), rad * 0.78, rad * 0.78)
    p.setBrush(QColor(255, 235, 200, 40))
    p.drawEllipse(QPointF(-rad * 0.25, -rad * 0.25), rad * 0.3, rad * 0.2)
    p.setBrush(NO_BRUSH)
    for i in range(3):                                       # khói
        phase = t * 0.9 + i * 2.1
        path = QPainterPath(QPointF(-rad * 0.3 + i * rad * 0.3, -rad * 0.2))
        for k in range(1, 6):
            path.lineTo(-rad * 0.3 + i * rad * 0.3 + math.sin(phase + k * 0.9) * rad * 0.18, -rad * 0.2 - k * rad * 0.28)
        p.setPen(pen(QColor(235, 235, 240, int(40 + 25 * math.sin(phase))), 2.2))
        p.drawPath(path)


def draw_tag(p: QPainter, rect: QRectF, text: str, active: bool = False, alpha: float = 1.0) -> None:
    """Thẻ giấy buộc dây ghi tên chức năng (dưới mỗi vật dụng bấm được)."""
    p.save()
    p.setOpacity(p.opacity() * alpha)
    p.setPen(pen("#6b5a30" if not active else "#ffd23c", 1.8))
    p.setBrush(QColor("#f6e7a8") if active else QColor("#cdbf8c"))
    p.drawRoundedRect(rect, 5, 5)
    p.setPen(NO_PEN)
    p.setBrush(QColor("#2a1d08"))
    p.drawEllipse(QPointF(rect.left() + 9, rect.center().y()), 2.6, 2.6)
    draw_fitted(p, rect.adjusted(18, 2, -8, -2), text, theme.display(text), 15, 8, theme.INK, bold=True,
                fl=ALIGN_CENTER)
    p.restore()
