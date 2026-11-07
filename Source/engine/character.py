"""Nhân vật. (Scope A)

Character chứa nhãn ẨN (is_criminal) -> CHỈ Game Engine được giữ.
Logic Agent KHÔNG ĐƯỢC import/đọc is_criminal (xem docs/INTERFACES.md).

TODO(A3):
  - hoàn thiện Character (trạng thái hiển thị: FACE_DOWN / CRIMINAL / INNOCENT)
  - nhân vật sắp xếp theo tên (theo đề: "ordered alphabetically by display name")
"""
from dataclasses import dataclass


@dataclass
class Character:
    cell: str
    name: str
    profession: str
    is_criminal: bool          # HIDDEN
    revealed: bool = False     # đã lật chưa
    # clue được giữ ở GameEngine (dict cell -> Clue), không để trong Character
