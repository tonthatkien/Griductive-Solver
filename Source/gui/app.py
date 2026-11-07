"""Vòng lặp GUI chính. (Scope F)

TODO(Scope F):
  [ ] Vẽ lưới, tọa độ (A,B,C... / 1,2,3...), tên, nghề, thẻ úp/ngửa, màu Criminal/Innocent
  [ ] Click ô chưa giải -> chọn CRIMINAL / INNOCENT -> engine.submit_verdict(...)
  [ ] Hiển thị NOT_PROVABLE / CONTRADICTED (thông báo, KHÔNG lật thẻ)
  [ ] Click clue đã mở -> highlight các ô clue nhắc đến (engine.clue.clue_cells)
  [ ] Nút: Load (chọn file puzzle), Restart, Hint, Auto Solve (từng bước có delay, có thể Pause)
  [ ] Panel trace: hiển thị bước suy luận (agent.auto_solve trả TraceEntry)
  [ ] Hiển thị clue dạng text tự nhiên (format_clue_text)
"""


def run(puzzle_path=None):
    raise NotImplementedError
