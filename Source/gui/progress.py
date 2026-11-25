"""Tiến độ chơi (màn đã phá + số sao), lưu ra một file JSON nhỏ. (Scope F)

Không phụ thuộc Qt nên test được trong CI. Hỏng file hoặc không ghi được thì im lặng bỏ qua:
tiến độ chỉ là tiện ích, không được làm hỏng game.

Cách tính sao (compute_stars):
  3 sao: tự suy luận, không dùng Hint, không bị NOT_PROVABLE/CONTRADICTED
  -1 sao nếu có dùng Hint; -1 sao nếu từng bị từ chối verdict (tối thiểu 1 sao)
  1 sao: nếu nhờ Agent (Auto Solve / Bước tiếp) phá án hộ
"""
import json
from pathlib import Path
from typing import Dict

MAX_STARS = 3
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "progress.json"


def compute_stars(hints_used: int, wrong_attempts: int, auto_used: bool) -> int:
    """Số sao (1..3) của một lần phá án."""
    if auto_used:
        return 1
    penalty = (1 if hints_used > 0 else 0) + (1 if wrong_attempts > 0 else 0)
    return max(1, MAX_STARS - penalty)


def stars_text(stars: int) -> str:
    """'★★☆' cho 2 sao."""
    stars = max(0, min(MAX_STARS, stars))
    return "★" * stars + "☆" * (MAX_STARS - stars)


class Progress:
    """key màn (vd 'puzzles_3x3/p01.json') -> số sao tốt nhất. Chưa phá thì không có key."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = Path(path)
        self._stars: Dict[str, int] = {}
        self.load()

    def load(self) -> None:
        """Đọc lại từ file; file thiếu hoặc hỏng thì coi như chưa phá màn nào."""
        self._stars = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        cleared = data.get("cleared") if isinstance(data, dict) else None
        if not isinstance(cleared, dict):
            return
        for key, value in cleared.items():
            if isinstance(key, str) and type(value) is int and 1 <= value <= MAX_STARS:
                self._stars[key] = value

    def stars(self, key: str) -> int:
        """Số sao tốt nhất của màn, 0 nếu chưa phá."""
        return self._stars.get(key, 0)

    def is_cleared(self, key: str) -> bool:
        return key in self._stars

    def record(self, key: str, stars: int) -> int:
        """Ghi kết quả một lần phá án, giữ số sao cao nhất. Trả về số sao tốt nhất sau khi ghi."""
        stars = max(1, min(MAX_STARS, int(stars)))
        best = max(self._stars.get(key, 0), stars)
        if best != self._stars.get(key):
            self._stars[key] = best
            self.save()
        return best

    def reset(self) -> None:
        """Xóa toàn bộ tiến độ."""
        self._stars = {}
        self.save()

    def save(self) -> bool:
        """Ghi file (qua file tạm rồi thay thế). Trả False nếu không ghi được."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            payload = {"version": 1, "cleared": self._stars}
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                           encoding="utf-8")
            tmp.replace(self.path)
            return True
        except OSError:
            return False
