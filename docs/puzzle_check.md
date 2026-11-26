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
