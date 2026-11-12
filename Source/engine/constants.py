"""Hằng số dùng chung. (Scope A)

File này KHÔNG import gì từ dự án, để `clue.py`, `game_state.py`, `cnf_encoder.py`, ...
cùng import mà không gây vòng lặp import.
"""

CRIMINAL = "CRIMINAL"
INNOCENT = "INNOCENT"
STATUSES = (CRIMINAL, INNOCENT)
UNKNOWN = "UNKNOWN"
INCONSISTENT = "INCONSISTENT"
