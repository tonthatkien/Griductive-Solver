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
| 07/11/2026 | Kiên | Setup | Claude (Anthropic) | Dựng khung repo, bảng Todolist Excel và bộ tài liệu quy định cho Project 2 | "Đọc đề Griductive Solver, review cây thư mục và todolist, sinh khung code kèm hướng dẫn từng file, tạo Todolist Excel chia đều độ khó cho 5 người, chuyển các file .md của đồ án 1 sang Griductive" | Dùng làm khung: `engine/board.py` và `resolve_region` (đã có code thật), các file còn lại là stub có docstring; Todolist Excel; các file `docs/*.md` và `CONTRIBUTING.md`. Cả nhóm cần đọc lại, sửa theo ý và chốt các điểm còn mở (2 extension, thư viện GUI, deadline thật) | Chạy `python -m unittest discover -s tests -t .` (4 test của `board.py` xanh); kiểm tra các module import được; kiểm tra phụ thuộc và ngày trong Excel khớp nhau; link/DOI trong `REFERENCES.md` **chưa** kiểm (xem ghi chú trong file đó) |
| | | | | | | | |
