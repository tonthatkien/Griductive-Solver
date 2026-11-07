"""Semantic evaluator: kiểm tra clue đúng/sai trên MỘT assignment đầy đủ,
KHÔNG gọi CNF encoder. (Scope D, D5-D6)

TODO(D5, D6):
  evaluate(clue, assignment, n) -> bool
    assignment: dict cell -> bool (True = Criminal), đủ N*N ô
  Cần hỗ trợ đủ 6 core + 2 extension.

Dùng để TEST encoder (tests/test_encoder_vs_semantic.py):
  với mỗi clue và mọi assignment của các ô liên quan, so
  evaluate(...) == (assignment thỏa CNF của clue).
"""
from typing import Dict


def evaluate(clue, assignment: Dict[str, bool], n: int) -> bool:
    raise NotImplementedError
