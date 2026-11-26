# B6 — Kiểm chứng bộ puzzle và demo lỗi

Ngày kiểm chứng: 26/11/2026. Baseline: main 2822e12.
Dependency: B3/B4/B5 đã merge ở PR #16; E4 đã merge ở PR #24.
Dữ liệu gốc của chín puzzle chuẩn được giữ nguyên.

## Tái lập

Chạy từ Source/ (Python 3.10+, không cần thư viện SAT ngoài):
```bash
python -m tools.puzzle_check --out ../docs/puzzle_check_results.json
python -m unittest tests.test_puzzle_check -v
python -m unittest discover -s tests -t .
```

Trên Linux/macOS có thể dùng python3 thay python. --out ghi trực tiếp UTF-8 không BOM,
xuống dòng LF, không phụ thuộc encoding chuyển hướng của PowerShell. Khi chỉ có
Source/ trong gói nộp bài, có thể dùng --out puzzle_check_results.json; unit test
không cần thư mục docs/.

Lệnh audit trả exit code 0 chỉ khi đủ 9 puzzle chuẩn, 2 demo và mọi kết quả
khớp kỳ vọng. Timeout DPLL hoặc lỗi evaluator được truyền thành lỗi; không coi là UNSAT.
JSON đi kèm ghi SHA-256 từng puzzle sau khi chuẩn hóa CRLF thành LF,
số nghiệm chính xác của oracle, kết quả DPLL
và tiến độ agent. Không ghi thời gian vào artifact để kết quả tái lập ổn định.

## Kết quả thực tế

| Puzzle | Nghiệm từ toàn bộ clue | Thêm FACT face-up ban đầu | Agent | Bước ACCEPTED |
|---|---:|---:|---|---:|
| puzzles_3x3/p01.json | 1 | 1 | SOLVED | 7 |
| puzzles_3x3/p02.json | 1 | 1 | SOLVED | 7 |
| puzzles_3x3/p03.json | 1 | 1 | SOLVED | 8 |
| puzzles_4x4/p01.json | 1 | 1 | SOLVED | 14 |
| puzzles_4x4/p02.json | 1 | 1 | SOLVED | 14 |
| puzzles_4x4/p03.json | 1 | 1 | SOLVED | 15 |
| puzzles_5x5/p01.json | 1 | 1 | SOLVED | 24 |
| puzzles_5x5/p02.json | 1 | 1 | SOLVED | 24 |
| puzzles_5x5/p03.json | 1 | 1 | SOLVED | 23 |
| demo_cases/ambiguous.json | 256 | 256 | STUCK | 0 |
| demo_cases/inconsistent.json | 0 | 0 | INCONSISTENT | 0 |

Cả chín puzzle chuẩn đều có đúng một nghiệm với cả hai tập ràng buộc,
các nhãn lưu trong JSON thỏa mọi clue, và agent giải toàn bộ bảng.
DPLL và phép duyệt semantic độc lập khớp tất cả 11 trường hợp.

## Phương pháp và giới hạn

- E4 uniqueness_check giải một model, chặn assignment primary rồi giải lần hai.
  Kết quả 0/1/2 là count capped tại 2; 2 nghĩa là ít nhất hai nghiệm.
- Với 3×3/4×4: B2 count_solutions duyệt đầy đủ mọi assignment bằng semantic.evaluate,
  không dùng encoder/DPLL, cho số đếm chính xác.
- Với 5×5: tools.puzzle_check.semantic_count duyệt Boolean theo row-major,
  chỉ cắt nhánh khi một clue đã được gán đủ mọi ô liên quan và evaluate trả False.
  Mọi phần mở rộng của nhánh đó đều vô nghiệm, nên số đếm vẫn chính xác;
  không dừng ở nghiệm thứ hai, không dùng SAT/encoder/nhãn ẩn để cắt nhánh.
  Đây là vét cạn có cắt nhánh, không phải duyệt đủ 2^25 bảng hoàn chỉnh;
  độ phức tạp xấu nhất vẫn exponential. Bộ kiểm tra này dành cho dataset hiện tại.
- Kiểm riêng toàn bộ clue và toàn bộ clue + FACT của thẻ face-up;
  không đồng nhất tính duy nhất của toàn puzzle với lượng thông tin ban đầu.
- Việc đọc toàn bộ clue/nhãn chỉ nằm trong tooling offline. Trong gameplay,
  auto_solve chỉ nhận engine qua API công khai và suy luận từ PublicKB.
  Nhãn lưu trong JSON chỉ dùng để kiểm chứng sau, không ép nghiệm oracle.
- Tests đối chiếu pruner với B2 trên cả 8 loại clue, kiểm số model 5×5 có ô tự do,
  và xác nhận evaluator exception không trở thành số nghiệm 0.

## Demo cho báo cáo

Hai file nằm ở data/demo_cases/, tách khỏi puzzles_3x3/4x4/5x5 để không bị
nhầm là puzzle chuẩn phải UNIQUE/SOLVED. Chúng hợp lệ về schema nhưng cố ý lỗi logic.

1. ambiguous.json: cả chín clue chỉ nói A1 là Criminal; ban đầu chỉ A1 mở.
   Tám ô còn lại hoàn toàn tự do: 2^8 = 256 nghiệm. Agent không nộp verdict,
   không lật thêm thẻ và dừng STUCK.
2. inconsistent.json: A1 và B1 mở ban đầu. Clue A1 nói A1 Criminal,
   clue B1 nói A1 Innocent. Hai clue đã công khai mâu thuẫn trực tiếp,
   không có assignment thỏa: 0 nghiệm. Agent dừng INCONSISTENT trước khi submit.
   Nhãn lưu trong file không thể thỏa toàn bộ clue; đây là chủ ý demo,
   không phải nhãn nghiệm đúng để nộp verdict.

Có thể nạp JSON demo qua GUI sau khi luồng engine/GUI hoàn thiện:
```bash
python main.py --puzzle data/demo_cases/ambiguous.json
python main.py --puzzle data/demo_cases/inconsistent.json
```
Các lệnh GUI trên là hướng dẫn demo; kiểm chứng B6 đã chạy headless bằng engine thật.
Baseline GUI gọi GameEngine.unsolved_cells() nhưng engine chưa có phương thức này;
B6 không sửa luồng tích hợp đó, không khẳng định demo GUI đã chạy trực quan.

## Số liệu tham khảo cho thực nghiệm (26/11/2026)

Môi trường: Python 3.12.3, Linux-6.18.58.1-microsoft-standard-WSL2-x86_64-with-glibc2.39.
Đo một lượt mỗi file bằng perf_counter; không warm-up hoặc lấy trung bình.
Tập ràng buộc là toàn bộ clue, không thêm FACT face-up.
DPLL đo toàn bộ lời gọi uniqueness_check (gồm validation/encode và tối đa hai solve);
oracle đo count_solutions B2 cho 3×3/4×4 hoặc semantic_count cho 5×5.
Không tính đọc JSON hoặc khởi tạo engine; kích thước KB lấy từ Encoder.build_kb
trước blocking clause. Đây là số đo tham khảo trên máy chạy, không phải cam kết
hiệu năng hay so sánh thuật toán trong điều kiện chi phí giống nhau.
Thời gian không đưa vào JSON artifact để giữ kết quả audit tái lập ổn định.

| Puzzle | Primary | Auxiliary | Clauses | E4 DPLL (ms) | Oracle semantic (ms) |
|---|---:|---:|---:|---:|---:|
| puzzles_3x3/p01.json | 9 | 0 | 28 | 0.881 | 3.028 |
| puzzles_3x3/p02.json | 9 | 17 | 90 | 2.617 | 3.575 |
| puzzles_3x3/p03.json | 9 | 18 | 106 | 3.809 | 4.845 |
| puzzles_4x4/p01.json | 16 | 51 | 238 | 13.670 | 640.706 |
| puzzles_4x4/p02.json | 16 | 63 | 306 | 43.910 | 570.882 |
| puzzles_4x4/p03.json | 16 | 42 | 195 | 10.711 | 489.762 |
| puzzles_5x5/p01.json | 25 | 163 | 777 | 139.244 | 64.298 |
| puzzles_5x5/p02.json | 25 | 95 | 498 | 66.117 | 2.522 |
| puzzles_5x5/p03.json | 25 | 204 | 813 | 198.515 | 98.810 |
| demo_cases/ambiguous.json | 9 | 0 | 9 | 0.164 | 3.117 |
| demo_cases/inconsistent.json | 9 | 0 | 9 | 0.093 | 1.262 |

## Giới hạn demo và mở rộng dataset

inconsistent.json chỉ dành cho minh họa phát hiện INCONSISTENT bằng Auto Solve
(hoặc audit headless). Không dùng nó để demo nộp verdict thủ công:
GameEngine.submit_verdict cố ý ném AssertionError nếu callback classify trả
INCONSISTENT, vì engine yêu cầu mọi verdict nộp phải dựa trên KB nhất quán.
Giới hạn tích hợp GUI đã nêu ở trên vẫn áp dụng.

Hai fixture tối giản được giữ nguyên để có kết quả kiểm chứng rõ ràng.
Nâng cấp nhân vật Conan, clue đa dạng hoặc demo giải vài bước rồi STUCK là
công việc trình bày cho H5/H8; không thay đổi các fixture regression hiện tại.

Nếu thêm demo mới, đăng ký trạng thái và số nghiệm kỳ vọng trong
DEMO_EXPECTATIONS của tools/puzzle_check.py. File chưa đăng ký gây ValueError
nêu tên file trước khi audit chạy; thiếu demo bắt buộc làm all_passed=false.
semantic_count preflight mọi clue và yêu cầu evaluator trả đúng bool;
lỗi evaluator được truyền ra kể cả khi nhánh đầu đã vô nghiệm.
