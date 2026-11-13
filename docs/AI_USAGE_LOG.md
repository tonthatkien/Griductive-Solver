# Nhật ký sử dụng AI (dùng cho Phụ lục của báo cáo)

Đề yêu cầu phụ lục nêu **đã dùng AI tạo sinh (LLM) thế nào và dùng prompt nào**. Ghi ngay khi dùng, đừng đợi cuối kỳ mới nhớ lại.

## Quy tắc

- Mỗi lần dùng AI cho việc đáng kể (sinh code, giải thích thuật toán, viết/sửa báo cáo, tìm lỗi, dịch, thiết kế puzzle...) thì thêm **một dòng** ở bảng bên dưới.
- Ghi **prompt** (đủ để người khác hiểu, có thể rút gọn nếu quá dài) và **cách bạn kiểm chứng** kết quả.
- Code do AI sinh ra phải được đọc hiểu, chạy thử và có test **trước khi commit**. Không commit thứ mình không giải thích được.
- **Phần lõi (DPLL, CNF encoder) phải do nhóm tự cài đặt.** Dùng AI để hiểu khái niệm hoặc rà soát là được; ghi rõ AI giúp gì.
- Không cần ghi: tra từ, sửa lỗi chính tả vặt.
- Mỗi người tự ghi dòng của mình. Người review nên nhắc nếu thấy PR có dấu hiệu dùng AI mà chưa ghi.

## Cách ghi từng cột

| Cột | Ghi gì |
|---|---|
| Ngày | `dd/mm/yyyy` |
| Người | Tên người dùng AI |
| ID việc | ID trong Excel (vd `C3`), hoặc `Setup` / `Report` nếu không thuộc việc nào |
| Công cụ | Tên + phiên bản nếu biết (Claude, ChatGPT, Copilot, Gemini...) |
| Mục đích | Dùng AI để làm gì (1 câu) |
| Prompt | Nội dung đã hỏi (tóm tắt hoặc đầy đủ) |
| Kết quả dùng thế nào | Lấy gì, sửa gì, bỏ gì; file nào bị ảnh hưởng |
| Đã kiểm chứng bằng | Test nào, tự tính tay thế nào, đối chiếu với đâu |

## Nhật ký

| Ngày | Người | ID việc | Công cụ | Mục đích | Prompt (tóm tắt hoặc đầy đủ) | Kết quả dùng thế nào | Đã kiểm chứng bằng |
|---|---|---|---|---|---|---|---|
| 07/11/2026 | Tôn Thất Kiên | Setup | Claude (Anthropic) | Dựng khung repo, bảng Todolist Excel và bộ tài liệu quy định cho Project 2 | "Đọc đề Griductive Solver, review cây thư mục và todolist, sinh khung code kèm hướng dẫn từng file, tạo Todolist Excel chia đều độ khó cho 5 người, chuyển các file .md của đồ án 1 sang Griductive" | Dùng làm khung: `engine/board.py` và `resolve_region` (đã có code thật), các file còn lại là stub có docstring; Todolist Excel; các file `docs/*.md` và `CONTRIBUTING.md`. Cả nhóm cần đọc lại, sửa theo ý và chốt các điểm còn mở (2 extension, thư viện GUI, deadline thật) | Chạy `python -m unittest discover -s tests -t .` (4 test của `board.py` xanh); kiểm tra các module import được; kiểm tra phụ thuộc và ngày trong Excel khớp nhau; link/DOI trong `REFERENCES.md` **chưa** kiểm (xem ghi chú trong file đó) |
| 09/11/2026 | Tôn Thất Kiên | A1 | Gemini | Vá lỗi ẩn board.py và sinh test case biên | "Task A1 trong Excel ghi 'đã có, review & bổ sung', nên việc của bạn là tự review board.py..." | Sửa lại logic các hàm bắt ngoại lệ ValueError và bổ sung test vào test_board.py | Chạy `python -m unittest discover -s tests -t .` xanh toàn bộ |
| 09/11/2026 | Tôn Thất Kiên | B1 | Gemini | Thiết kế cấu trúc JSON cho puzzle, clues và tạo puzzle mẫu p01 | "Hướng dẫn tui làm p01 hoàn thiện đi đừng tạo mẫu" | Sử dụng file p01.json và format clues trong INTERFACES.md | Chờ cả nhóm review |
| 10/11/2026 | Tôn Thất Kiên | A2 | Claude (Anthropic) | Cài clue_cells, validate_clue và test cho engine/clue.py | "Hướng dẫn tôi cài task A2: Clue & Region, cài clue_cells và validate_clue theo mô tả Excel, thêm test luôn" | Chỉnh sửa hai file clue.py và file test_clue.py; đã đọc lại logic từng nhánh. Tự quyết: SAME/DIFFERENT với a == b bị coi là lỗi | Chạy `python -m unittest discover -s tests -t .`, 32 test xanh; đối chiếu biên (góc 3 ô, giữa 8 ô, k = 0, k = &#124;R&#124;) với board.py |
| 10/11/2026 | Hữu Duy | D1 | Gemini | Phân loại trạng thái mệnh đề, rà soát logic lan truyền unit clause và các trường hợp biên | "Cơ chế phân loại trạng thái mệnh đề (SATISFIED, CONFLICT, UNIT, UNRESOLVED) và giải thuật Unit Propagation trong DPLL thuần; gợi ý các trường hợp biên để viết test case" | Định nghĩa các trạng thái mệnh đề và logic kiểm tra conflict. Thiết kế và cài đặt các hàm trong `Source/logic/dpll.py` (`get_clause_status`, `is_conflict`, `unit_propagate`), xây dựng các test case bao quát các trường hợp biên trong `Source/tests/test_dpll.py` | Chạy toàn bộ test suite dự án `python -m unittest discover -s tests -t .` xanh 100%; tính tay các ví dụ suy diễn logic và kiểm tra tính bất biến của danh sách clauses |
| 11/11/2026 | Mai Thảo Vy | C1 | Claude (Anthropic) | Hoàn thiện khung Encoder (C1) và viết unit test cho khung đó | "Hoàn thiện khung Encoder cho task C1 (biến phụ, KB, literal theo status) và viết unit test." | Lấy: `board.first_aux_var(n)` thay cho `n*n+1` viết tay; `KB.num_clauses`; `Encoder.num_primary`; `Encoder.literal_of(cell, status)` (CRIMINAL ra +var, INNOCENT ra -var); file `tests/test_cnf_encoder.py`. Giữ nguyên `new_aux()` và `KB` của khung gốc. Chưa có logic encode clue nào (để C2, C3) | Chạy `python -m unittest discover -s tests -t .` trong `Source/`, toàn bộ test xanh; tự đọc lại code, đối chiếu quy ước biến phụ (bắt đầu từ N*N+1) và quy ước `status` với `docs/INTERFACES.md` |
| 12/11/2026 | Hữu Duy | D5 | Gemini | Tham khảo danh sách ca biên và trường hợp dữ liệu sai cần phòng vệ khi đánh giá clue | "Gợi ý các ca kiểm thử biên và các kiểu dữ liệu sai dễ mắc phải khi viết hàm semantic evaluator kiểm tra assignment trên lưới logic" | Các trường hợp lỗi biên và lỗi ép kiểu ngầm định. Tự cài đặt các hàm kiểm tra hợp lệ (_validate_k, resolve_region_cells) và 6 hàm eval cho core clues trong Source/logic/semantic.py, viết các test case trong Source/tests/test_semantic.py| Chạy `python -m unittest discover -s tests -t .` xanh 100%; tự tính bảng chân trị của từng clue trên assignment mẫu. |
| 13/11/2026 | Hửu Duy | D6 | Gemini | Quy ước chẵn/lẻ cho trường hợp đếm bằng 0 và tập toán tử so sánh 2 vùng | "Trong bài toán logic trên lưới, khi kiểm tra clue PARITY nếu số lượng phần tử khớp bằng 0 thì quy ước toán học chuẩn là chẵn hay lẻ? Với clue COMPARE giữa 2 vùng, nên chuẩn hóa các toán tử so sánh (GT, GE, EQ, LE, LT) thế nào để tránh sót nhánh?" | Cách lập luận logic toán học. Viết code eval_parity, eval_compare trong Source/logic/semantic.py và viết bổ sung test cho đủ 5 toán tử so sánh | Chạy test suite `test_semantic.py` xanh; kiểm tra thực tế bằng cách đánh giá toàn bộ clue của puzzle thật data/puzzles_3x3/p01.json trên lời giải nghiệm đúng |
| 13/11/2026 | Hửu Duy | D5, D6 | Gemini | Rà soát tính độc lập của module logic và kiểm tra tuân thủ coding standards | "Kiểm tra xem module semantic evaluator có đang vô tình phụ thuộc hoặc import chéo module nào từ cnf_encoder không để đảm bảo làm oracle kiểm chứng độc lập; kiểm tra định dạng PEP 8 và độ dài dòng" | Tham khảo góp ý rà soát kiến trúc: xác nhận không import cnf_encoder | Kiểm tra danh sách import đầu file semantic.py; chạy unittest toàn bộ dự án bảo đảm không phát sinh lỗi hồi quy |
