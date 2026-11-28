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
- `--data`: thư mục chứa `puzzles_*/*.json`, `demo_*/*.json` và `not_found/*.json` (mặc định `data`).
- `--out`: đường dẫn file CSV kết quả (mặc định `experiments/results.csv`).
- `--timeout`: giới hạn giây cho từng truy vấn DPLL, kể cả trong `uniqueness_check` (mặc định `30`); mỗi puzzle có thể gọi DPLL nhiều lần. Giá trị `0` dừng với `TIMEOUT` ở truy vấn đầu; truyền `--timeout inf` để bỏ giới hạn.
- `--include-demo`: chạy thêm các file trong `demo_*/*.json` và `not_found/*.json` sau bộ puzzle chính (mặc định bỏ qua). `not_found/` chứa các bài thiếu manh mối, agent dừng ở `STUCK`.
- Cột `status` ghi `SOLVED`, `STUCK`, `INCONSISTENT`, `TIMEOUT` hoặc `ERROR`. Cột `unique` ghi `UNIQUE`, `MULTIPLE`, `UNSAT`, `TIMEOUT` hoặc `ERROR`. Script ghi mọi dòng lỗi và hết giờ vào CSV rồi chạy tiếp các bài sau.

File `experiments/results.csv` gồm 15 cột: `puzzle`, `size`, `status`, `unique`, `primary_vars`, `aux_vars`, `clauses`, `sat_calls`, `trace_sat_calls`, `untraced_sat_calls`, `decisions`, `propagations`, `backtracks`, `deduction_steps`, `runtime_sec`. Ba cột `primary_vars`, `aux_vars`, `clauses` là kích thước KB của cả puzzle (mọi clue kèm `FACT` cho ô lật sẵn, cùng tập clue với `uniqueness_check`), nên dòng `STUCK`/`TIMEOUT` có cùng số với dòng `SOLVED` của bài đó. `decisions`, `propagations`, `backtracks` cộng từ `SolverStats` qua mọi truy vấn trong `sat_calls`. `deduction_steps` là số bước `ACCEPTED`; mỗi bước lật một clue nên cột này cũng là số lượt lật thẻ. Lượt kiểm tra `unique` chạy riêng nên không tính vào `sat_calls`, các bộ đếm DPLL hay `runtime_sec`.

Tổng hợp bảng và biểu đồ từ 5 lần chạy lặp và file demo (chạy trong `Source/`):

    1..5 | ForEach-Object { python experiments/run_tests.py --out "experiments/runs/run_$_.csv" }
    # bash: for i in 1 2 3 4 5; do python experiments/run_tests.py --out "experiments/runs/run_$i.csv"; done
    python experiments/run_tests.py --include-demo --out experiments/results_demo.csv
    python experiments/plots.py

- `plots.py` đọc `experiments/runs/run_1..5.csv` và `experiments/results_demo.csv`. Bảng failure lấy các dòng không `SOLVED` trong file demo, trừ `demo_cases/ambiguous.json` (đã có 3 bài `not_found` cùng loại). Chạy không cờ sẽ in 3 bảng Markdown và lưu 3 hình PNG vào `docs/image/` ở gốc repo.
- `--tables`: chỉ in 3 bảng Markdown, không cần `matplotlib`.
- `--figures`: chỉ vẽ 3 hình PNG.
- `--image-dir`: đổi thư mục lưu hình khi chỉ có `Source/` (ví dụ `python experiments/plots.py --figures --image-dir experiments/images`).

## Chạy test (chạy trong thư mục Source/)
    python -m unittest discover -s tests -t .

TODO(Lead): bổ sung ảnh GUI, cấu trúc thư mục, cách load puzzle.

Quy định làm việc nhóm: xem `CONTRIBUTING.md` và thư mục `docs/` ở gốc repo.
