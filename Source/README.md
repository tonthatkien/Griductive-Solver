# Griductive Solver (CSC14003 - Project 2)

## Cài đặt
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt

## Chạy GUI
    python main.py                  # mở GUI
    python main.py --puzzle data/puzzles_3x3/p01.json

## Chạy thực nghiệm
    python experiments/run_tests.py # ghi experiments/results.csv
    python experiments/run_tests.py --data data --out experiments/results.csv --timeout 30

Chạy từ thư mục `Source/`:
- `--data`: thư mục chứa `puzzles_*/*.json` (mặc định `data`).
- `--out`: đường dẫn file CSV kết quả (mặc định `experiments/results.csv`).
- `--timeout`: giới hạn giây cho từng truy vấn DPLL và `uniqueness_check` (mặc định `30`); mỗi puzzle có thể gọi DPLL nhiều lần. Giá trị `0` dừng với `TIMEOUT` ở truy vấn đầu; truyền `--timeout inf` để bỏ giới hạn.
- Cột `status` ghi `SOLVED`, `STUCK`, `INCONSISTENT`, `TIMEOUT` hoặc `ERROR`. Cột `unique` ghi `UNIQUE`, `MULTIPLE`, `UNSAT` hoặc `TIMEOUT`. Script ghi mọi dòng lỗi và hết giờ vào CSV rồi chạy tiếp các bài sau.

## Chạy test (chạy trong thư mục Source/)
    python -m unittest discover -s tests -t .

TODO(Lead): bổ sung ảnh GUI, cấu trúc thư mục, cách load puzzle.

Quy định làm việc nhóm: xem `CONTRIBUTING.md` và thư mục `docs/` ở gốc repo.
