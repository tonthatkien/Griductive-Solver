"""ViewMixin: cảnh mở đầu khi vào màn, ẩn/hiện giao diện để ngắm nền, bố trí các lớp phủ. (Scope F)

Mixin của MainWindow: dùng self.hud, self.intro, self.eye_float, self.backdrop, self.grid... do BuildMixin tạo.
Trạng thái: _intro_active (cảnh mở đầu đang chạy), _hud_hidden (giao diện đang ẩn để ngắm nền).
"""
from gui.case_intro import case_time


class ViewMixin:
    def _layout_overlays(self) -> None:
        for overlay in (self.radial, self.effect, self.intro):
            if overlay.isVisible():
                overlay.setGeometry(self.backdrop.rect())
        self.eye_float.move(self.backdrop.width() - self.eye_float.width() - 16, 14)

    def _layout_iris(self) -> None:
        if self.iris.isVisible():
            self.iris.setGeometry(self.stage.rect())

    # ---- cảnh mở đầu + ẩn/hiện giao diện để ngắm nền ---------------------------------------
    def _start_intro(self, place: str, fallback: str = "") -> None:
        """Nền "diễn" trước: chữ địa điểm + giờ giữa màn hình, xong mới cho giao diện và thẻ hiện lên."""
        level = self.menu.level_by_key(self._level_key) if self._level_key else None
        n = self.engine.n
        title = place or fallback or "HIỆN TRƯỜNG"
        self._intro_active, self._hud_hidden = True, False
        self.eye_float.hide()
        self.radial.close_menu()
        self.effect.dismiss()
        self.hud.hide_now()
        self.backdrop.set_veil_now(0.0)
        self._layout_overlays()
        self.intro.play(level.title.upper() if level else "HỒ SƠ ĐIỀU TRA", title.upper(),
                        case_time(self._level_key or title), f"{n * n} nghi phạm · lưới {n}×{n}")

    def _on_intro_reveal(self) -> None:
        self.sound.play("radial")
        self.grid.stagger_in(240, 75)              # đặt thẻ về trạng thái ẩn TRƯỚC khi hiện khung giao diện
        self.hud.fade_to(1.0, 450)
        self.backdrop.set_veil(1.0, 1000)

    def _on_intro_done(self) -> None:
        self._intro_active = False

    def _set_hud_hidden(self, hidden: bool) -> None:
        """Ẩn mờ dần toàn bộ giao diện để chỉ còn nền (hoặc hiện lại)."""
        if hidden == self._hud_hidden or self._intro_active or self._transitioning:
            return
        self._hud_hidden = hidden
        self.radial.close_menu()
        if hidden:
            self.hud.fade_to(0.0, 380)
            self.backdrop.set_veil(0.0, 600)
        else:
            self.eye_float.hide()
            self.hud.fade_to(1.0, 380)
            self.backdrop.set_veil(1.0, 600)

    def _on_hud_faded_out(self) -> None:
        if self._hud_hidden:                       # nút mắt nổi chỉ hiện khi giao diện đã ẩn hẳn
            self._layout_overlays()
            self.eye_float.show()
            self.eye_float.raise_()

    def _on_backdrop_clicked(self) -> None:
        if self._hud_hidden and not self._intro_active:
            self._set_hud_hidden(False)

    def _on_space(self) -> None:
        if self._intro_active:
            self.intro.skip()
        elif self.stage.currentWidget() is self.backdrop:
            self._set_hud_hidden(not self._hud_hidden)

    def _reset_view(self) -> None:
        """Về trạng thái xem bình thường (khi quay lại bản đồ)."""
        self.intro.hide()
        self._intro_active = self._hud_hidden = False
        self.eye_float.hide()
        self.hud.show_now()
        self.backdrop.set_veil_now(1.0)
        self.backdrop.reset_mood()
