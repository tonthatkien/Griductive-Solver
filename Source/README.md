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

## Chạy test (chạy trong thư mục Source/)
    python -m unittest discover -s tests -t .

TODO(Lead): bổ sung ảnh GUI, cấu trúc thư mục, cách load puzzle.

Quy định làm việc nhóm: xem `CONTRIBUTING.md` và thư mục `docs/` ở gốc repo.
