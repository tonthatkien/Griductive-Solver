"""Cảnh nền theo địa điểm của vụ án. `scene_for(place)` trả về cảnh tương ứng (mặc định: thành phố ban đêm).

Tên địa điểm lấy từ `gui.levels.PLACES` / `SEALED_PLACE`; thêm địa điểm mới = thêm một lớp Scene + một dòng ở _BY_PLACE.
"""
from gui.levels import SEALED_PLACE
from gui.scenes.base import Scene
from gui.scenes.cafe import CafeScene
from gui.scenes.city import CityNightScene
from gui.scenes.clock_tower import ClockTowerScene
from gui.scenes.harbor import HarborScene
from gui.scenes.hotel import HotelScene
from gui.scenes.lab import LabScene
from gui.scenes.library import LibraryScene
from gui.scenes.mansion import MansionScene
from gui.scenes.museum import MuseumScene
from gui.scenes.park import ParkScene
from gui.scenes.rooftop import RooftopScene
from gui.scenes.sealed import SealedScene
from gui.scenes.station import StationScene
from gui.scenes.theater import TheaterScene

_BY_PLACE = {
    "Quán cà phê góc phố": CafeScene,
    "Biệt thự bỏ hoang": MansionScene,
    "Phòng thí nghiệm": LabScene,
    "Ga tàu điện": StationScene,
    "Bảo tàng nghệ thuật": MuseumScene,
    "Khách sạn trung tâm": HotelScene,
    "Công viên ven sông": ParkScene,
    "Thư viện cổ": LibraryScene,
    "Bến cảng về đêm": HarborScene,
    "Nhà hát thành phố": TheaterScene,
    "Tháp đồng hồ": ClockTowerScene,
    "Sân thượng cao ốc": RooftopScene,
    SEALED_PLACE: SealedScene,
}


def scene_for(place: str) -> Scene:
    """Cảnh mới cho địa điểm `place`; không khớp thì dùng thành phố ban đêm."""
    return _BY_PLACE.get(place, CityNightScene)()


__all__ = ["Scene", "scene_for"]
