"""Quét thư mục data/ để dựng danh sách màn chơi cho bản đồ. (Scope F)

Không phụ thuộc Qt nên test được trong CI.

Chỉ đọc TÊN file và thư mục, KHÔNG mở file JSON: file puzzle chứa nhãn ẩn `criminal`,
menu không có lý do gì để đọc chúng (kích thước lưới lấy từ tên thư mục `puzzles_NxN`).

Quy ước:
  data/puzzles_3x3/p01.json            -> màn thường, lưới 3x3
  data/puzzles_3x3/bad_xxx.json        -> hồ sơ niêm phong (puzzle lỗi cố ý, để demo STUCK/INCONSISTENT)
  data/puzzles_3x3/<thư mục con>/*.json -> cũng là hồ sơ niêm phong
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

SEALED_PREFIX = "bad_"
SEALED_PLACE = "Hiện trường bị phong tỏa"
TRACK_COUNT = 9            # số bài nhạc nền theo màn: level_01 ... level_09 (quá 9 màn thì quay vòng)
PLACES = (
    "Quán cà phê góc phố", "Biệt thự bỏ hoang", "Phòng thí nghiệm", "Ga tàu điện",
    "Bảo tàng nghệ thuật", "Khách sạn trung tâm", "Công viên ven sông", "Thư viện cổ",
    "Bến cảng về đêm", "Nhà hát thành phố", "Tháp đồng hồ", "Sân thượng cao ốc",
)
_DIR_RE = re.compile(r"^puzzles_(\d+)x(\d+)$")


@dataclass(frozen=True)
class Level:
    """Một màn chơi trên bản đồ."""

    key: str          # đường dẫn tương đối so với data/, dạng posix: "puzzles_3x3/p01.json"
    path: Path
    n: int            # kích thước lưới n x n
    number: int       # số thứ tự hiển thị (#01)
    title: str        # "Vụ án #01" hoặc "Hồ sơ niêm phong"
    place: str        # tên địa điểm trên bản đồ
    sealed: bool
    track: int = 0    # bài nhạc nền 1..TRACK_COUNT của màn thường; 0 = màn niêm phong (dùng nhạc menu)

    @property
    def code(self) -> str:
        """Mã hồ sơ, lấy từ tên file: 'P01'."""
        return self.path.stem.upper()

    @property
    def tag(self) -> str:
        """Nhãn ngắn dưới ghim trên bản đồ."""
        return "NIÊM PHONG" if self.sealed else f"#{self.number:02d}"


def _natural_key(name: str) -> list:
    """Sắp xếp tự nhiên: p2 < p10. Các phần tử chẵn là chuỗi, lẻ là số, nên so sánh luôn hợp lệ."""
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", name)]


def discover_levels(data_dir: Path) -> List[Level]:
    """Danh sách màn theo thứ tự: kích thước lưới tăng dần, màn thường trước, niêm phong sau."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return []
    entries = []
    for folder in data_dir.iterdir():
        match = _DIR_RE.match(folder.name)
        if not folder.is_dir() or match is None or match.group(1) != match.group(2):
            continue
        n = int(match.group(1))
        if n < 1:
            continue
        for path in folder.rglob("*.json"):
            rel = path.relative_to(folder)
            sealed = len(rel.parts) > 1 or path.stem.lower().startswith(SEALED_PREFIX)
            entries.append((n, sealed, _natural_key(rel.as_posix()), path))
    entries.sort(key=lambda e: (e[0], e[1], e[2]))

    levels: List[Level] = []
    counters: dict = {}
    normal_seen = 0
    for n, sealed, _key, path in entries:
        counters[(n, sealed)] = counters.get((n, sealed), 0) + 1
        digits = re.search(r"\d+", path.stem)
        number = int(digits.group()) if digits and not sealed else counters[(n, sealed)]
        track = 0
        if sealed:
            title, place = "Hồ sơ niêm phong", SEALED_PLACE
        else:
            title, place = f"Vụ án #{number:02d}", PLACES[normal_seen % len(PLACES)]
            track = normal_seen % TRACK_COUNT + 1
            normal_seen += 1
        levels.append(Level(path.relative_to(data_dir).as_posix(), path, n, number,
                            title, place, sealed, track))
    return levels