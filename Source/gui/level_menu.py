"""LevelMenu: bản đồ thành phố về đêm để chọn màn chơi. (Scope F)

Mỗi vụ án là một địa điểm phát sáng trên bản đồ. Các khu phố chia theo kích thước lưới
(3x3 / 4x4 / 5x5), các ghim trong một khu nối nhau bằng đường điều tra nét đứt.
  - ghim đỏ nhấp nháy "?"   : vụ án chưa phá
  - ghim xanh + huy hiệu    : đã phá (kèm số sao)
  - ghim vàng + băng niêm phong + đèn hú : hồ sơ lỗi dùng để demo (STUCK / INCONSISTENT)

Chỉ nhận danh sách `Level` và `Progress`; không đọc nội dung file puzzle, không có luật chơi hay
suy luận. Bấm vào ghim (hoặc phím mũi tên + Enter) thì phát tín hiệu `levelChosen(key, tâm ghim)`.
"""
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPixmap,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from gui import icons, theme
from gui.anim import Tween, clock
from gui.conan_widgets import ConanWidget
from gui.header_chip import HeaderChip
from gui.draw_utils import (ALIGN_CENTER, ALIGN_LEFT_MID, draw_brackets, draw_fitted,
                            draw_neon_text, make_font)
from gui.icons import NO_BRUSH, NO_PEN, pen
from gui.levels import Level
from gui.neon_widgets import NeonTitle
from gui.progress import MAX_STARS, Progress, stars_text

ACCENT_NEW, ACCENT_DONE, ACCENT_SEALED = "#ff3b4e", "#4aa8ff", "#ffd23c"
DIFFICULTY_VN = {3: "TẬP SỰ", 4: "THÁM TỬ", 5: "THÁM TỬ LỪNG DANH"}
MAP_MARGIN_X, MAP_TOP, MAP_BOTTOM = 70.0, 104.0, 168.0   # lề của vùng đặt ghim
WELCOME = "Chọn một địa điểm trên bản đồ để bắt đầu điều tra. Sự thật chỉ có một!"


class _Pin:
    """Một ghim trên bản đồ: màn chơi, tâm, bán kính và hiệu ứng rê chuột."""

    def __init__(self, level: Level, center: QPointF, radius: float, hover: Tween) -> None:
        self.level, self.center, self.radius, self.hover = level, center, radius, hover
        self.target = 0.0


@dataclass
class _District:
    """Một khu phố = các màn cùng kích thước lưới."""

    n: int
    index: int
    panel: QRectF
    levels: List[Level]
    start: int            # chỉ số ghim đầu tiên của khu trong LevelMenu._pins


class LevelMenu(QWidget):
    """Trang chọn màn."""

    levelChosen = Signal(str, object)         # (key của màn, tâm ghim theo tọa độ của menu)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._levels: List[Level] = []
        self._progress: Optional[Progress] = None
        self._pins: List[_Pin] = []
        self._districts: List[_District] = []
        self._tweens: Dict[str, Tween] = {}
        self._hover, self._focus, self._said = -1, -1, ""
        self._static: Optional[QPixmap] = None
        self._static_key: tuple = ()
        self._xs: List[float] = []
        self._ys: List[float] = []
        rng = random.Random(7)
        palette = ("#fff3c4", "#bfe6ff", "#ffd1a8", "#ffffff")
        self._cars = [(rng.random() < 0.5, rng.random(), rng.uniform(0.035, 0.08), rng.random(),
                       rng.choice((-1, 1)), QColor(rng.choice(palette))) for _ in range(10)]
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build_ui()
        clock().tick.connect(self._on_tick)

    # ---- dựng giao diện -----------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 16, 28, 18)
        root.setSpacing(0)
        header = QHBoxLayout()
        title = NeonTitle("CASE MAP", px=30, spacing=6.0)
        self.sub_label = HeaderChip("hint", "Chọn một địa điểm để điều tra")
        self.cases_chip = HeaderChip("cases", "ĐÃ PHÁ")
        self.stars_chip = HeaderChip("stars", "SAO")
        header.addWidget(title)
        header.addSpacing(16)
        header.addWidget(self.sub_label)
        header.addStretch(1)
        header.addWidget(self.cases_chip)
        header.addSpacing(10)
        header.addWidget(self.stars_chip)
        root.addLayout(header)
        root.addStretch(1)
        self.conan = ConanWidget(plate=True)
        self.conan.setFixedSize(480, 132)
        footer = QHBoxLayout()
        footer.addWidget(self.conan)
        footer.addStretch(1)
        root.addLayout(footer)
        for widget in (title, self.sub_label, self.cases_chip, self.stars_chip, self.conan):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)   # chuột về menu
        self.conan.say(WELCOME, "think")

    # ---- API ----------------------------------------------------------------------------
    def set_levels(self, levels: List[Level], progress: Progress) -> None:
        """Nạp danh sách màn và tiến độ; dựng lại vị trí ghim."""
        self._levels, self._progress = list(levels), progress
        self._hover = self._focus = -1
        self._layout_pins()
        self.refresh()

    def level_by_key(self, key: str) -> Optional[Level]:
        return next((lv for lv in self._levels if lv.key == key), None)

    def refresh(self) -> None:
        """Đọc lại tiến độ (gọi khi quay về bản đồ) và cập nhật thống kê trên đầu trang."""
        normal = [lv for lv in self._levels if not lv.sealed]
        done = sum(1 for lv in normal if self._stars(lv) > 0)
        stars = sum(self._stars(lv) for lv in normal)
        self.cases_chip.set_value(done, len(normal))
        self.stars_chip.set_value(stars, MAX_STARS * len(normal))
        self.update()

    def _stars(self, level: Level) -> int:
        return self._progress.stars(level.key) if self._progress else 0

    # ---- bố cục ghim --------------------------------------------------------------------
    def _map_rect(self) -> QRectF:
        w, h = float(self.width()), float(self.height())
        return QRectF(MAP_MARGIN_X, MAP_TOP, max(200.0, w - 2 * MAP_MARGIN_X),
                      max(200.0, h - MAP_TOP - MAP_BOTTOM))

    def _layout_pins(self) -> None:
        self._pins, self._districts = [], []
        if not self._levels:
            return
        groups: Dict[int, List[Level]] = {}
        for lv in self._levels:
            groups.setdefault(lv.n, []).append(lv)
        sizes = sorted(groups)
        rect = self._map_rect()
        col_w = rect.width() / len(sizes)
        for di, n in enumerate(sizes):
            items = groups[n]
            panel = QRectF(rect.left() + di * col_w + 8, rect.top(), col_w - 16, rect.height())
            self._districts.append(_District(n, di, panel, items, len(self._pins)))
            y0 = panel.top() + 80
            y1 = max(y0 + 40, panel.bottom() - 36)
            spacing = (y1 - y0) / len(items)
            amp = min(panel.width() * 0.2, 90.0)
            radius = max(15.0, min(28.0, spacing * 0.34, panel.width() * 0.1))
            for i, lv in enumerate(items):
                swing = 0.55 + 0.45 * math.sin(i * 1.3 + di)
                x = panel.center().x() + (0.0 if len(items) == 1
                                          else (amp if i % 2 == 0 else -amp) * swing)
                tween = self._tweens.get(lv.key)
                if tween is None:
                    tween = self._tweens[lv.key] = Tween(self, self.update,
                                                         QEasingCurve.Type.OutCubic)
                self._pins.append(_Pin(lv, QPointF(x, y0 + (i + 0.5) * spacing), radius, tween))
        self._sync_tweens()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_pins()

    # ---- tương tác ----------------------------------------------------------------------
    def _active(self) -> int:
        return self._hover if self._hover >= 0 else self._focus

    def _sync_tweens(self) -> None:
        active = self._active()
        for i, pin in enumerate(self._pins):
            target = 1.0 if i == active else 0.0
            if pin.target != target or abs(pin.hover.now - target) > 0.01:
                pin.target = target
                pin.hover.go(target, 160 if target else 220)

    def _set_hover(self, idx: int) -> None:
        if idx == self._hover:
            return
        self._hover = idx
        self._focus = idx
        self.setCursor(Qt.CursorShape.PointingHandCursor if idx >= 0
                       else Qt.CursorShape.ArrowCursor)
        self._sync_tweens()
        self._announce()
        self.update()

    def _announce(self) -> None:
        """Conan bình luận về màn đang được chọn (chỉ khi đổi sang màn khác)."""
        idx = self._active()
        if idx < 0:
            return
        lv = self._pins[idx].level
        if lv.key == self._said:
            return
        self._said = lv.key
        stars = self._stars(lv)
        if lv.sealed:
            self.conan.say("Hồ sơ niêm phong! Puzzle này cố ý có lỗi để xem agent xử lý ra sao: "
                           "dừng ở STUCK hay báo INCONSISTENT.", "shake")
        elif stars >= MAX_STARS:
            self.conan.say(f"{lv.place}: đã phá hoàn hảo {stars_text(stars)}! "
                           f"Vẫn muốn xem lại hiện trường?", "happy")
        elif stars:
            self.conan.say(f"{lv.place}: vụ này phá rồi ({stars_text(stars)}). "
                           f"Phá lại để lấy đủ 3 sao nhé!", "happy")
        else:
            self.conan.say(f"{lv.place}. Lưới {lv.n}×{lv.n} có {lv.n * lv.n} nghi phạm. "
                           f"Nhớ nhé: không được đoán mò!", "think")

    def _choose(self, idx: int) -> None:
        pin = self._pins[idx]
        self.levelChosen.emit(pin.level.key, QPointF(pin.center))

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        hit = -1
        for i, pin in enumerate(self._pins):
            if math.hypot(pos.x() - pin.center.x(), pos.y() - pin.center.y()) <= pin.radius * 1.35:
                hit = i
                break
        self._set_hover(hit)

    def leaveEvent(self, event) -> None:
        self._set_hover(-1)
        self._focus = -1
        self._sync_tweens()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._hover >= 0:
            self._choose(self._hover)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if not self._pins:
            super().keyPressEvent(event)
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Up):
            step = 1 if key in (Qt.Key.Key_Right, Qt.Key.Key_Down) else -1
            cur = self._active()
            new = (0 if step > 0 else len(self._pins) - 1) if cur < 0 \
                else (cur + step) % len(self._pins)
            self._hover, self._focus = -1, new
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._sync_tweens()
            self._announce()
            self.update()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._active() >= 0:
                self._choose(self._active())
        else:
            super().keyPressEvent(event)

    def _on_tick(self) -> None:
        if self.isVisible():
            self.update()

    # ---- lớp bản đồ tĩnh (vẽ một lần cho mỗi kích thước) ----------------------------------
    def _ensure_static(self) -> QPixmap:
        w, h, dpr = self.width(), self.height(), self.devicePixelRatioF()
        key = (w, h, dpr)
        if self._static is None or self._static_key != key:
            self._static, self._static_key = self._build_static(float(w), float(h), dpr), key
        return self._static

    def _build_static(self, w: float, h: float, dpr: float) -> QPixmap:
        pix = QPixmap(int(w * dpr) + 1, int(h * dpr) + 1)
        pix.setDevicePixelRatio(dpr)
        g = QPainter(pix)
        try:
            self._draw_static(g, w, h)
        finally:                       # lỗi giữa chừng cũng phải đóng painter, tránh lỗi dây chuyền
            g.end()
        return pix

    def _draw_static(self, g: QPainter, w: float, h: float) -> None:
        """Nền đêm, lưới đường phố, khối nhà sáng đèn, công viên, dòng sông, tọa độ, vignette."""
        g.setRenderHint(QPainter.RenderHint.Antialiasing)
        g.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rng = random.Random(2026)
        full = QRectF(0, 0, w, h)
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor(theme.NIGHT_TOP))
        sky.setColorAt(0.6, QColor(theme.NIGHT_MID))
        sky.setColorAt(1, QColor(theme.NIGHT_BOTTOM))
        g.fillRect(full, QBrush(sky))

        xs, x = [], -30.0
        while x < w + 60:
            xs.append(x)
            x += rng.uniform(100, 160)
        ys, y = [], -30.0
        while y < h + 60:
            ys.append(y)
            y += rng.uniform(80, 130)
        self._xs, self._ys = xs, ys

        river = QPainterPath(QPointF(-50, h * 0.78))
        river.cubicTo(QPointF(w * 0.3, h * 0.55), QPointF(w * 0.62, h * 1.02),
                      QPointF(w + 50, h * 0.66))
        samples = [river.pointAtPercent(i / 80) for i in range(81)]
        park = QRectF(w * 0.40, h * 0.12, 260, 150)

        for k, line in enumerate(xs):                      # đường phố (đại lộ sáng hơn)
            main = k % 3 == 0
            g.setPen(pen(QColor(80, 130, 220, 52 if main else 24), 3 if main else 1.2))
            g.drawLine(QPointF(line, 0), QPointF(line, h))
        for k, line in enumerate(ys):
            main = k % 3 == 0
            g.setPen(pen(QColor(80, 130, 220, 52 if main else 24), 3 if main else 1.2))
            g.drawLine(QPointF(0, line), QPointF(w, line))

        for i in range(len(xs) - 1):                       # khối nhà
            for j in range(len(ys) - 1):
                bx, by = xs[i] + 9, ys[j] + 9
                bw, bh = xs[i + 1] - xs[i] - 18, ys[j + 1] - ys[j] - 18
                cx, cy = bx + bw / 2, by + bh / 2
                if park.contains(QPointF(cx, cy)):
                    continue
                if any(math.hypot(cx - s.x(), cy - s.y()) < 58 + 0.25 * max(bw, bh)
                       for s in samples):
                    continue
                shade = rng.randint(0, 10)
                g.setPen(pen(QColor(34, 58, 108, 150), 1))
                g.setBrush(QColor(11 + shade, 22 + shade, 48 + shade))
                g.drawRoundedRect(QRectF(bx, by, bw, bh), 5, 5)
                g.setPen(NO_PEN)
                for _ in range(rng.randint(1, 3)):
                    ww, hh = rng.uniform(bw * 0.25, bw * 0.6), rng.uniform(bh * 0.25, bh * 0.6)
                    ox = bx + rng.uniform(4, max(5.0, bw - ww - 4))
                    oy = by + rng.uniform(4, max(5.0, bh - hh - 4))
                    g.setBrush(QColor(18 + shade, 34 + shade, 70 + shade))
                    g.drawRect(QRectF(ox, oy, ww, hh))
                    for _w in range(rng.randint(0, 5)):
                        g.setBrush(QColor(255, 214, 110, rng.randint(90, 190)))
                        g.drawRect(QRectF(ox + rng.uniform(2, max(3.0, ww - 5)),
                                          oy + rng.uniform(2, max(3.0, hh - 5)), 3, 3))

        g.setPen(pen(QColor(30, 110, 80, 120), 1.5))       # công viên
        g.setBrush(QColor(9, 40, 32, 215))
        g.drawEllipse(park)
        g.setPen(NO_PEN)
        g.setBrush(QColor(16, 74, 52, 230))
        rx, ry, pc = park.width() / 2, park.height() / 2, park.center()
        for _ in range(26):
            tx, ty = rng.uniform(park.left() + 16, park.right() - 16), \
                rng.uniform(park.top() + 12, park.bottom() - 12)
            if ((tx - pc.x()) / rx) ** 2 + ((ty - pc.y()) / ry) ** 2 < 0.85:
                g.drawEllipse(QPointF(tx, ty), rng.uniform(4, 8), rng.uniform(4, 8))

        g.setBrush(NO_BRUSH)                               # dòng sông
        g.setPen(pen(QColor(8, 38, 66, 235), 46))
        g.drawPath(river)
        g.setPen(pen(QColor(14, 70, 112, 230), 38))
        g.drawPath(river)
        g.setPen(pen(QColor(90, 190, 235, 70), 2))
        g.drawPath(river)

        rect = self._map_rect()                            # tọa độ A.. / 1.. như bản đồ thám tử
        g.setFont(make_font(theme.FONT_MONO, 11, True))
        g.setPen(QColor(120, 210, 255, 100))
        cols, rows = 14, 9
        for i in range(cols):
            cx = rect.left() + (i + 0.5) * rect.width() / cols
            g.drawText(QRectF(cx - 10, 2, 20, 14), ALIGN_CENTER, chr(65 + i))
        for j in range(rows):
            cy = rect.top() + (j + 0.5) * rect.height() / rows
            g.drawText(QRectF(4, cy - 8, 20, 16), ALIGN_CENTER, str(j + 1))

        vignette = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w, h) * 0.55)
        vignette.setColorAt(0.55, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 170))
        g.fillRect(full, QBrush(vignette))

    # ---- vẽ động ------------------------------------------------------------------------
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h, t = float(self.width()), float(self.height()), clock().t
        p.drawPixmap(0, 0, self._ensure_static())
        self._paint_beams(p, w, h, t)
        self._paint_cars(p, w, h, t)
        if not self._pins:
            p.setFont(make_font(theme.FONT_DOSSIER, 18, False, True))
            p.setPen(QColor("#cdd7f0"))
            p.drawText(self._map_rect(), ALIGN_CENTER,
                       "Chưa có vụ án nào. Hãy thêm file .json vào data/puzzles_3x3/ ...")
        for d in self._districts:
            p.setBrush(QColor(8, 16, 38, 120))
            p.setPen(pen(QColor(60, 92, 160, 110), 1.5))
            p.drawRoundedRect(d.panel, 16, 16)
        self._paint_routes(p, t)
        active = self._active()
        for i in [i for i in range(len(self._pins)) if i != active] + \
                ([active] if active >= 0 else []):
            self._paint_pin(p, i, t)
        for d in self._districts:
            self._paint_banner(p, d, t)
        self._paint_legend(p, w, h)
        if active >= 0:
            self._paint_preview(p, active, t)

    def _paint_beams(self, p: QPainter, w: float, h: float, t: float) -> None:
        p.setPen(NO_PEN)
        for ox, base in ((w * 0.03, -62.0), (w * 0.97, -118.0)):
            angle = math.radians(base + 10 * math.sin(t * 0.45 + ox))
            origin, length, spread = QPointF(ox, h), h * 1.2, math.radians(8)
            tip1 = origin + QPointF(math.cos(angle - spread), math.sin(angle - spread)) * length
            tip2 = origin + QPointF(math.cos(angle + spread), math.sin(angle + spread)) * length
            beam = QLinearGradient(origin, (tip1 + tip2) / 2)
            beam.setColorAt(0, QColor(255, 255, 235, 34))
            beam.setColorAt(1, QColor(255, 255, 235, 0))
            p.setBrush(QBrush(beam))
            p.drawPolygon(QPolygonF([origin, tip1, tip2]))

    def _paint_cars(self, p: QPainter, w: float, h: float, t: float) -> None:
        """Vài chấm đèn xe chạy dọc các con phố cho bản đồ có sức sống."""
        if not self._xs or not self._ys:
            return
        p.setPen(NO_PEN)
        for horizontal, seed, speed, phase, direction, color in self._cars:
            lines = self._ys if horizontal else self._xs
            pos = lines[int(seed * len(lines)) % len(lines)]
            span = (w if horizontal else h) + 80
            along = ((t * speed * direction + phase) % 1.0) * span - 40
            at = QPointF(along, pos) if horizontal else QPointF(pos, along)
            glow = QColor(color)
            glow.setAlpha(60)
            p.setBrush(glow)
            p.drawEllipse(at, 7, 7)
            p.setBrush(color)
            p.drawEllipse(at, 2.2, 2.2)

    def _paint_routes(self, p: QPainter, t: float) -> None:
        """Đường điều tra nét đứt, chạy từ ghim này tới ghim kế trong cùng một khu."""
        p.setBrush(NO_BRUSH)
        for d in self._districts:
            for i in range(d.start, d.start + len(d.levels) - 1):
                a, b = self._pins[i].center, self._pins[i + 1].center
                color = QColor(ACCENT_SEALED if self._pins[i + 1].level.sealed else "#38f2ff")
                path = QPainterPath(a)
                mid = (a.y() + b.y()) / 2
                path.cubicTo(QPointF(a.x(), mid), QPointF(b.x(), mid), b)
                glow = QColor(color)
                glow.setAlpha(34)
                p.setPen(pen(glow, 9))
                p.drawPath(path)
                color.setAlpha(190)
                dash = pen(color, 3)
                dash.setCapStyle(Qt.PenCapStyle.FlatCap)
                dash.setDashPattern([1.6, 2.6])
                dash.setDashOffset(-t * 3.0)
                p.setPen(dash)
                p.drawPath(path)

    def _paint_banner(self, p: QPainter, d: _District, t: float) -> None:
        """Bảng tên khu phố: huy hiệu số khu (cùng phong cách ghim) + tên neon + thanh tiến độ chia đoạn."""
        r = QRectF(d.panel.left() + 10, d.panel.top() + 8, d.panel.width() - 20, 54)
        normal = [lv for lv in d.levels if not lv.sealed]
        done = sum(1 for lv in normal if self._stars(lv) > 0)
        total = len(normal)
        complete = total > 0 and done == total
        gold = QColor(theme.GOLD)
        p.save()
        # nền + quầng viền
        plate = QPainterPath()
        plate.addRoundedRect(r, 10, 10)
        bg = QLinearGradient(r.topLeft(), r.bottomLeft())
        bg.setColorAt(0, QColor(14, 28, 62, 240))
        bg.setColorAt(1, QColor(5, 10, 24, 245))
        p.fillPath(plate, QBrush(bg))
        p.setBrush(NO_BRUSH)
        breath = 0.5 + 0.5 * math.sin(t * 1.6 + d.index)
        halo = QColor(gold)
        halo.setAlpha(int((50 if complete else 22) + (40 if complete else 16) * breath))
        p.setPen(pen(halo, 6))
        p.drawPath(plate)
        p.setPen(pen(gold, 1.6))
        p.drawPath(plate)
        # vệt sáng quét ngang qua bảng
        p.save()
        p.setClipPath(plate)
        sweep_x = r.left() - 60 + ((t * 0.28 + d.index * 0.37) % 1.0) * (r.width() + 120)
        sheen = QLinearGradient(sweep_x - 40, 0, sweep_x + 40, 0)
        sheen.setColorAt(0, QColor(255, 235, 150, 0))
        sheen.setColorAt(0.5, QColor(255, 235, 150, 34))
        sheen.setColorAt(1, QColor(255, 235, 150, 0))
        p.fillRect(r, QBrush(sheen))
        p.restore()
        draw_brackets(p, r.adjusted(-3, -3, 3, 3), QColor(theme.GOLD_SOFT), 9, 1.6)

        # huy hiệu số khu: cùng ngôn ngữ với ghim (nền cầu tối, viền vàng, vòng radar xoay)
        c = QPointF(r.left() + 30, r.top() + 24)
        br = 16.0
        ring = pen(QColor(243, 211, 107, 150), 1.4)
        ring.setDashPattern([2.0, 3.0])
        ring.setDashOffset(-t * 4.0)
        p.setBrush(NO_BRUSH)
        p.setPen(ring)
        p.drawEllipse(c, br + 5, br + 5)
        body = QRadialGradient(QPointF(c.x(), c.y() - br * 0.4), br * 1.6)
        body.setColorAt(0, QColor("#2a4378"))
        body.setColorAt(1, QColor("#0a1226"))
        p.setBrush(QBrush(body))
        p.setPen(pen(gold, 2.4))
        p.drawEllipse(c, br, br)
        draw_neon_text(p, QRectF(c.x() - br, c.y() - br, 2 * br, 2 * br), str(d.index + 1),
                       make_font(theme.FONT_GADGET, 19, True), theme.GOLD_SOFT, theme.GOLD,
                       0.8 + 0.3 * breath, ALIGN_CENTER)

        # tên khu (neon) + dòng phụ
        tx = r.left() + 62
        right_w = 66.0
        avail = r.right() - right_w - tx - 4
        p.setFont(make_font(theme.FONT_MONO, 10, True, spacing=1.6))
        p.setPen(QColor(theme.CYAN_LASER))
        p.drawText(QRectF(tx, r.top() + 5, avail, 14), ALIGN_LEFT_MID,
                   f"KHU {d.index + 1}  ·  LƯỚI {d.n}×{d.n}")
        title = DIFFICULTY_VN.get(d.n, "THÁM TỬ")
        px = 19
        while px > 10 and QFontMetricsF(make_font(theme.FONT_GADGET, px, True)).horizontalAdvance(title) > avail:
            px -= 1
        draw_neon_text(p, QRectF(tx, r.top() + 18, avail, 24), title,
                       make_font(theme.FONT_GADGET, px, True), theme.GOLD_SOFT, theme.GOLD,
                       0.7 + 0.3 * breath, ALIGN_LEFT_MID)

        # số vụ đã phá
        count_color = QColor(theme.GOLD_SOFT if complete else ACCENT_DONE if done else "#ff8a96")
        draw_neon_text(p, QRectF(r.right() - right_w - 6, r.top() + 5, right_w, 26), f"{done}/{total}",
                       make_font(theme.FONT_GADGET, 19, True), count_color.lighter(120), count_color,
                       0.7, ALIGN_CENTER)
        p.setFont(make_font(theme.FONT_MONO, 9, True, spacing=1.2))
        p.setPen(QColor("#7fdcff"))
        p.drawText(QRectF(r.right() - right_w - 6, r.top() + 30, right_w, 12), ALIGN_CENTER, "ĐÃ PHÁ")

        # thanh tiến độ chia đoạn: mỗi đoạn một vụ án (xanh = đã phá, tối = chưa)
        if total:
            bx, bw, by = r.left() + 14, r.width() - 28, r.bottom() - 9
            gap = 3.0
            seg = (bw - gap * (total - 1)) / total
            p.setPen(NO_PEN)
            for i in range(total):
                rect = QRectF(bx + i * (seg + gap), by, seg, 4)
                if i < done:
                    glow = QColor(complete and theme.GOLD_SOFT or ACCENT_DONE)
                    glow.setAlpha(70)
                    p.setBrush(glow)
                    p.drawRoundedRect(rect.adjusted(-1.5, -2, 1.5, 2), 3, 3)
                    p.setBrush(QColor(complete and theme.GOLD_SOFT or ACCENT_DONE))
                else:
                    p.setBrush(QColor(40, 62, 110, 150))
                p.drawRoundedRect(rect, 2, 2)
        p.restore()

    def _paint_legend(self, p: QPainter, w: float, h: float) -> None:
        plate = QRectF(w - 318, h - 132, 290, 112)
        p.setBrush(QColor(6, 12, 28, 225))
        p.setPen(pen("#2d4373", 1.5))
        p.drawRoundedRect(plate, 10, 10)
        p.setFont(make_font(theme.FONT_MONO, 11, True, spacing=1.5))
        p.setPen(QColor(theme.GOLD))
        p.drawText(QRectF(plate.left() + 14, plate.top() + 6, 200, 18), ALIGN_LEFT_MID, "CHÚ GIẢI")
        rows = ((ACCENT_NEW, "Chưa phá"), (ACCENT_DONE, "Đã phá"),
                (ACCENT_SEALED, "Niêm phong (puzzle lỗi)"))
        p.setFont(make_font(theme.FONT_MONO, 12))
        for i, (color, text) in enumerate(rows):
            y = plate.top() + 30 + i * 20
            p.setPen(NO_PEN)
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(plate.left() + 22, y + 9), 6, 6)
            p.setPen(QColor("#cdd7f0"))
            p.drawText(QRectF(plate.left() + 38, y, 240, 18), ALIGN_LEFT_MID, text)
        p.setFont(make_font(theme.FONT_MONO, 11))
        p.setPen(QColor(theme.CYAN_LASER))
        p.drawText(QRectF(plate.left() + 14, plate.bottom() - 22, 270, 18), ALIGN_LEFT_MID,
                   "← → chọn  ·  Enter vào hiện trường")

    # ---- ghim ---------------------------------------------------------------------------
    @staticmethod
    def _star(p: QPainter, cx: float, cy: float, size: float, filled: bool) -> None:
        color = QColor(theme.GOLD_SOFT)
        if filled:
            p.setPen(NO_PEN)
            p.setBrush(color)
        else:
            color.setAlpha(110)
            p.setPen(pen(color, 1.2))
            p.setBrush(NO_BRUSH)
        p.drawPolygon(icons.star_polygon(cx, cy, size, size * 0.42))

    @staticmethod
    def _lock(p: QPainter, box: QRectF, color: QColor) -> None:
        p.save()
        p.setBrush(NO_BRUSH)
        p.setPen(pen(color, max(2.0, box.width() * 0.1)))
        p.drawArc(QRectF(box.left() + box.width() * 0.26, box.top() + box.height() * 0.04,
                         box.width() * 0.48, box.height() * 0.6), 0, 180 * 16)
        p.setPen(NO_PEN)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(box.left() + box.width() * 0.14, box.top() + box.height() * 0.42,
                                 box.width() * 0.72, box.height() * 0.5), 4, 4)
        p.restore()

    @staticmethod
    def _tape(p: QPainter, c: QPointF, r: float) -> None:
        """Băng niêm phong vàng đen vắt chéo qua ghim."""
        p.save()
        p.translate(c.x(), c.y() + r * 0.55)
        p.rotate(-20)
        w, hh = r * 3.6, max(8.0, r * 0.5)
        p.setClipRect(QRectF(-w / 2, -hh / 2, w, hh))
        p.setPen(NO_PEN)
        p.setBrush(QColor(ACCENT_SEALED))
        p.drawRect(QRectF(-w / 2, -hh / 2, w, hh))
        p.setBrush(QColor(20, 20, 20))
        step, x = hh * 1.4, -w / 2
        while x < w / 2:
            p.drawPolygon(QPolygonF([QPointF(x, hh / 2), QPointF(x + step * 0.5, hh / 2),
                                     QPointF(x + step * 0.5 + hh, -hh / 2),
                                     QPointF(x + hh, -hh / 2)]))
            x += step
        p.restore()

    def _paint_pin(self, p: QPainter, idx: int, t: float) -> None:
        pin = self._pins[idx]
        lv, c = pin.level, pin.center
        stars = self._stars(lv)
        accent = QColor(ACCENT_SEALED if lv.sealed else ACCENT_DONE if stars else ACCENT_NEW)
        k = pin.hover.now
        r = pin.radius * (1.0 + 0.16 * k)
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * (t / 1.8 + idx * 0.23))
        rgb = (accent.red(), accent.green(), accent.blue())
        p.save()
        p.setPen(NO_PEN)
        halo = QRadialGradient(c, r * 2.8)
        halo.setColorAt(0, QColor(*rgb, int(min(255, 70 + 60 * pulse + 50 * k))))
        halo.setColorAt(1, QColor(*rgb, 0))
        p.setBrush(QBrush(halo))
        p.drawEllipse(c, r * 2.8, r * 2.8)
        if not stars and not lv.sealed:                    # sóng lan báo vụ án chưa phá
            phase = (t * 0.55 + idx * 0.31) % 1.0
            ring = QColor(accent)
            ring.setAlpha(int(150 * (1 - phase)))
            p.setBrush(NO_BRUSH)
            p.setPen(pen(ring, 2))
            p.drawEllipse(c, r * (1.0 + 1.1 * phase), r * (1.0 + 1.1 * phase))
        body = QRadialGradient(QPointF(c.x(), c.y() - r * 0.4), r * 1.6)
        body.setColorAt(0, QColor("#2a4378"))
        body.setColorAt(1, QColor("#0a1226"))
        p.setBrush(QBrush(body))
        p.setPen(pen(accent, 3))
        p.drawEllipse(c, r, r)
        inner = QColor(accent)
        inner.setAlpha(90)
        p.setBrush(NO_BRUSH)
        p.setPen(pen(inner, 1))
        p.drawEllipse(c, r * 0.78, r * 0.78)
        box = QRectF(c.x() - r * 0.62, c.y() - r * 0.62, r * 1.24, r * 1.24)
        if lv.sealed:
            self._lock(p, box, accent)
            self._tape(p, c, r)
            on = int(t * 3 + idx) % 2                       # đèn hú đỏ/xanh luân phiên
            for sign, color in ((-1, "#ff3b4e"), (1, "#3b8bff")):
                lit = QColor(color)
                lit.setAlpha(230 if (on == 0) == (sign < 0) else 50)
                p.setPen(NO_PEN)
                p.setBrush(lit)
                p.drawEllipse(QPointF(c.x() + sign * r * 0.9, c.y() - r * 1.15), 4.5, 4.5)
        elif stars:
            icons.draw_badge(p, box)
        else:
            draw_neon_text(p, QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), "?",
                           make_font(theme.FONT_GADGET, r * 1.25, True), "#ff8a96", ACCENT_NEW,
                           0.8 + 0.4 * pulse, ALIGN_CENTER)
        p.restore()

        y = c.y() + pin.radius + 6
        p.setFont(make_font(theme.FONT_MONO, 13, True))
        p.setPen(accent.lighter(135))
        p.drawText(QRectF(c.x() - 90, y, 180, 18), ALIGN_CENTER, lv.tag)
        y += 17
        if pin.radius >= 20:
            draw_fitted(p, QRectF(c.x() - 85, y, 170, 16), lv.place, theme.FONT_DOSSIER, 12, 8,
                        "#b9c6e6", italic=True, fl=ALIGN_CENTER)
            y += 17
        if stars:
            for s in range(MAX_STARS):
                self._star(p, c.x() + (s - 1) * 17, y + 9, 7.0, s < stars)
        if k > 0.05:
            R = r * 1.55
            color = accent.lighter(140)
            color.setAlpha(int(255 * min(1.0, k)))
            draw_brackets(p, QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R), color, R * 0.45, 2.0)

    def _paint_preview(self, p: QPainter, idx: int, t: float) -> None:
        """Hồ sơ xem trước hiện cạnh ghim đang chọn: lưới thu nhỏ, trạng thái, sao."""
        pin = self._pins[idx]
        lv, stars = pin.level, self._stars(pin.level)
        accent = QColor(ACCENT_SEALED if lv.sealed else ACCENT_DONE if stars else ACCENT_NEW)
        n = lv.n
        cell, gap_c = min(20.0, 96.0 / n), 3.0
        grid_h = n * cell + (n - 1) * gap_c
        cw, ch = 276.0, 92.0 + grid_h + 58.0        # cao theo lưới: lưới 5x5 cao hơn 3x3
        gap = pin.radius * 1.6 + 16
        x = pin.center.x() + gap
        if x + cw > self.width() - 12:
            x = pin.center.x() - gap - cw
        y = max(96.0, min(pin.center.y() - ch / 2, self._map_rect().bottom() - ch + 20))
        card = QRectF(x, y, cw, ch)
        p.save()
        p.setBrush(NO_BRUSH)
        for width, alpha in ((12, 25), (6, 55)):
            glow = QColor(accent)
            glow.setAlpha(alpha)
            p.setPen(pen(glow, width))
            p.drawRoundedRect(card, 12, 12)
        p.setBrush(QColor(4, 10, 24, 242))
        p.setPen(pen(accent, 2))
        p.drawRoundedRect(card, 12, 12)
        strip = QRectF(card.left() + 2, card.top() + 2, card.width() - 4, 24)
        p.setPen(NO_PEN)
        p.setBrush(QColor(*(accent.red(), accent.green(), accent.blue()), 50))
        p.drawRoundedRect(strip, 10, 10)
        p.setFont(make_font(theme.FONT_MONO, 12, True, spacing=1))
        p.setPen(accent.lighter(130))
        p.drawText(strip.adjusted(12, 0, -12, 0), ALIGN_LEFT_MID, f"CASE FILE // {lv.code}")
        draw_fitted(p, QRectF(card.left() + 14, card.top() + 32, cw - 28, 28), lv.title,
                    theme.FONT_TITLE, 20, 11, theme.GOLD_SOFT, bold=True, fl=ALIGN_LEFT_MID)
        draw_fitted(p, QRectF(card.left() + 14, card.top() + 60, cw - 28, 20), lv.place,
                    theme.FONT_DOSSIER, 13, 9, "#b9c6e6", italic=True, fl=ALIGN_LEFT_MID)

        gx, gy = card.left() + 16, card.top() + 92
        p.setFont(make_font(theme.FONT_GADGET, cell * 0.62, True))
        for row in range(n):
            for col in range(n):
                rect = QRectF(gx + col * (cell + gap_c), gy + row * (cell + gap_c), cell, cell)
                lit = 0.5 + 0.5 * math.sin(t * 4 - (row + col) * 0.9)     # sóng quét qua lưới
                edge = QColor(accent)
                edge.setAlpha(int(90 + 120 * lit))
                p.setPen(pen(edge, 1.2))
                p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 70) if stars
                           else QColor(20, 34, 64))
                p.drawRoundedRect(rect, 3, 3)
                if cell >= 14 and not stars:
                    p.setPen(accent.lighter(140))
                    p.drawText(rect, ALIGN_CENTER, "?")
        tx = gx + n * cell + (n - 1) * gap_c + 16
        status = ("NIÊM PHONG", ACCENT_SEALED) if lv.sealed else \
            ("ĐÃ PHÁ", ACCENT_DONE) if stars else ("CHƯA PHÁ", ACCENT_NEW)
        p.setFont(make_font(theme.FONT_MONO, 12, True))
        for i, (text, color) in enumerate((("LƯỚI  " + f"{n}×{n}", "#dfe7fb"),
                                           (f"NGHI PHẠM  {n * n}", "#dfe7fb"), status)):
            p.setPen(QColor(color))
            p.drawText(QRectF(tx, gy + i * 22, card.right() - tx - 10, 20), ALIGN_LEFT_MID, text)
        if not lv.sealed:
            for s in range(MAX_STARS):
                self._star(p, gx + 12 + s * 24, gy + grid_h + 16, 9.0, s < stars)   # ngay dưới lưới
        blink = 0.55 + 0.45 * math.sin(t * 5)
        foot = QColor(theme.CYAN_LASER)
        foot.setAlpha(int(255 * blink))
        p.setFont(make_font(theme.FONT_MONO, 12, True))
        p.setPen(foot)
        p.drawText(QRectF(card.left() + 14, card.bottom() - 28, cw - 28, 20), ALIGN_LEFT_MID,
                   "▶ HỒ SƠ LỖI, DÙNG ĐỂ DEMO" if lv.sealed else "▶ BẤM ĐỂ VÀO HIỆN TRƯỜNG")
        p.restore()