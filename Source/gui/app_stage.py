"""StageMixin: dàn cảnh một lần lật thẻ theo thứ tự "căn cứ → suy ra → lật". (Scope F)

Dùng chung cho Auto Solve, Bước tiếp và người chơi tự đoán:
  1. Làm tối mọi highlight cũ, nổi bật các thẻ căn cứ (số [1], [2]... khớp với sổ tay).
  2. Đánh dấu thẻ sắp được lật là "SUY RA".
  3. Gỡ hết highlight rồi mới lật thẻ.
Không còn vệt laser của manh mối cũ treo trên lưới khi thẻ tiếp theo lật, nên không bị hiểu nhầm
là thẻ đó dựa vào các ô đang sáng.

Mixin của MainWindow: dùng self.grid, self.notebook, self.sound, self.conan, self.names, self.kb...
"""
from typing import Callable, Dict, List

from PySide6.QtCore import QTimer

from gui.clue_text import STATUS_VN, format_clue_text

BASIS_MS, INFER_MS = 1900, 1100          # Auto / Bước tiếp: đủ thời gian đọc sổ tay
BASIS_FAST_MS, INFER_FAST_MS = 800, 500   # người chơi tự đoán: họ đã suy luận rồi, chỉ xác nhận


class StageMixin:
    def _clear_highlights(self) -> None:
        for card in self.grid.cards.values():
            card.set_highlight("")

    def _cancel_staging(self) -> None:
        self._stage_token += 1
        self._staging = False
        self._clear_highlights()

    def _present_reveal(self, who: str, cell: str, verdict: str, support_ids: List[str],
                        after: Callable[[], None], fast: bool = False, sound: str = "step") -> None:
        """Ghi sổ tay, nổi bật căn cứ, nổi bật thẻ sắp lật, rồi lật (refresh) và gọi `after()`.

        Gọi khi engine ĐÃ nhận verdict nhưng GUI chưa refresh: self.kb vẫn là trạng thái trước khi lật."""
        clues = [c for c in (self._clue_of(i) for i in support_ids) if c is not None]
        name = f"{self.names[cell]} ({cell})"
        word = STATUS_VN[verdict].lower()
        owners: Dict[str, List[str]] = {}
        for n, clue in enumerate(clues, 1):
            owners.setdefault(clue.owner, []).append(str(n))
        basis = [(f"{self.names.get(c.owner, c.owner)} ({c.owner})", format_clue_text(c, self.names))
                 for c in clues]
        self.notebook.add_entry(self._step_no, who, name, verdict, basis)

        token = self._stage_token = self._stage_token + 1
        self._staging = True
        self._clear_highlights()
        self._update_controls()
        for owner, numbers in owners.items():
            self.grid.cards[owner].set_highlight("basis", ",".join(numbers))
        if clues:
            self.sound.play("clue")
            who_text = ", ".join(f"{self.names.get(o, o)} ({o})" for o in owners)
            self.conan.say(f"Căn cứ: manh mối của {who_text}.", "think")
            self._say(f"Căn cứ vào manh mối của {who_text}...")
        else:
            self.conan.say("Chỉ cần dữ kiện ban đầu là đủ rồi.", "think")
            self._say("Suy ra trực tiếp từ dữ kiện ban đầu của vụ án...")
        basis_ms, infer_ms = (BASIS_FAST_MS, INFER_FAST_MS) if fast else (BASIS_MS, INFER_MS)

        def infer() -> None:
            if token != self._stage_token:
                return
            self.grid.cards[cell].set_highlight("infer")
            self.sound.play("hint")
            self.conan.say(f"Vậy {self.names[cell]} là {word}!", "happy")
            self._say(f"Suy ra: {name} là {word}.", "ok")
            QTimer.singleShot(infer_ms, flip)

        def flip() -> None:
            if token != self._stage_token:
                return
            self._clear_highlights()
            self._staging = False
            self.backdrop.react_good()
            self._refresh(animate={cell})
            self.sound.play(sound)
            self._update_controls()
            after()

        QTimer.singleShot(basis_ms, infer)
