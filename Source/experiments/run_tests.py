"""Chạy tự động mọi puzzle trong data/ và ghi results.csv. (Scope G)

Cột CSV bắt buộc (theo đề 4.5):
  puzzle, size, status(SOLVED|STUCK|INCONSISTENT|TIMEOUT|ERROR), unique,
  primary_vars, aux_vars, clauses, sat_calls, decisions, propagations, backtracks,
  deduction_steps, reveal_waves, runtime_sec

TODO(Scope G):
  [ ] duyệt data/puzzles_*/*.json (cùng một bộ puzzle cho mọi so sánh)
  [ ] mỗi puzzle: load engine, chạy LogicAgent.auto_solve, thu thống kê
  [ ] có timeout; GHI cả failure/timeout, KHÔNG loại khỏi bảng
  [ ] chạy uniqueness_check cho từng puzzle
  [ ] (tùy chọn) vẽ biểu đồ bằng matplotlib cho report
"""


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
