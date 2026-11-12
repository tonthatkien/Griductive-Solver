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
| 10/11/2026 | Hửu Duy | D1 | Gemini | Phân loại trạng thái mệnh đề, rà soát logic lan truyền unit clause và các trường hợp biên | "Cơ chế phân loại trạng thái mệnh đề (SATISFIED, CONFLICT, UNIT, UNRESOLVED) và giải thuật Unit Propagation trong DPLL thuần; gợi ý các trường hợp biên để viết test case" | Định nghĩa các trạng thái mệnh đề và logic kiểm tra conflict. Thiết kế và cài đặt các hàm trong `Source/logic/dpll.py` (`get_clause_status`, `is_conflict`, `unit_propagate`), xây dựng các test case bao quát các trường hợp biên trong `Source/tests/test_dpll.py` | Chạy toàn bộ test suite dự án `python -m unittest discover -s tests -t .` xanh 100%; tính tay các ví dụ suy diễn logic và kiểm tra tính bất biến của danh sách clauses |
| 12/11/2026 | Hửu Duy | D2 | Clause | Nguyên lý chọn biến deterministic (heuristic clause ngắn nhất) và cấu trúc đệ quy rẽ nhánh/quay lui trong DPLL | "Nguyên lý chọn biến phân nhánh tất định (biến nhỏ nhất trong mệnh đề ngắn nhất) và mô hình đệ quy 2 nhánh True/False kèm cơ chế quay lui an toàn trong DPLL thuần Python" | Ý tưởng thiết kế giải thuật cho `choose_variable` và khung rẽ nhánh `_dpll`. Tự cài đặt chi tiết trong `Source/logic/dpll.py`, cô lập trạng thái phép gán độc lập khi backtrack, đếm stats, quét deadline định kỳ và xây dựng bộ unit test trong `Source/tests/test_dpll.py` | Chạy test suite dự án `python -m unittest discover -s tests -t .` xanh 100%; tính tay các ca rẽ |
