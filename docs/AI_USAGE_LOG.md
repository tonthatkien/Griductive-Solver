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

| 2026-11-09 | Tôn Thất Kiên | A1 | Gemini | Vá lỗi ẩn board.py và sinh test case biên | "Task A1 trong Excel ghi 'đã có, review & bổ sung', nên việc của bạn là tự review board.py..." | Sửa lại logic các hàm bắt ngoại lệ ValueError và bổ sung test vào test_board.py | Chạy `python -m unittest discover -s tests -t .` xanh toàn bộ |

| 2026-11-09 | Tôn Thất Kiên | B1 | Gemini | Thiết kế cấu trúc JSON cho puzzle, clues và tạo puzzle mẫu p01 | "Hướng dẫn tui làm p01 hoàn thiện đi đừng tạo mẫu" | Sử dụng file p01.json và format clues trong INTERFACES.md | Chờ cả nhóm review |

| 08/11/2026 | Bảo | F1, F2, F3, F4, F5 | Claude (Anthropic) | Dựng khung GUI theo chủ đề Conan bằng PySide6 (lưới, thẻ úp/ngửa, radial menu, 4 nút Load/Restart/Hint/Auto Solve, sổ tay trace, highlight clue) | Đóng vai lập trình viên GUI game ; chủ đề Conan thám tử lừng danh; chốt PyQt6/PySide6 với QSS dark mode và animation; mô tả chi tiết thẻ hồ sơ, radial menu còng tay/huy hiệu, popup Conan lắc đầu khi `NOT_PROVABLE`, sét + bóng đen khi `CONTRADICTED`, laser khi chọn clue, 4 bảo bối, sổ tay phá án; yêu cầu tích hợp với Game Engine và Logic Agent | Lấy: `gui/app.py`, `components.py`, `icons.py`, `theme.py`, `clue_text.py` (câu mô tả clue, không phụ thuộc Qt), `solver_driver.py` (chạy từng bước Auto Solve), `main.py` (thêm `--demo`), `requirements.txt` (đổi pygame sang PySide6), `tests/test_gui_helpers.py`. **Chỉ để xem thử giao diện:** `gui/demo_backend.py` + `gui/demo_puzzle.json` (engine/agent giả suy luận bằng vét cạn, **phải xóa trước khi nộp**, không phải DPLL của nhóm). Tác giả tự đọc, sửa theo ý. Đã báo nhóm 2 điểm cần thống nhất (đổi thư viện GUI, đề xuất `LogicAgent.step`) | AI: `py_compile` các file, kiểm tra tên chưa định nghĩa, 4 unit test của phần không dùng Qt xanh, puzzle demo 3×3 kiểm tra có đúng một nghiệm bằng vét cạn. AI **chưa chạy được GUI** (không có PySide6). Người dùng tự chạy `python main.py --demo` |
| 10/11/2026 | Bảo | F (icon) | Claude (Anthropic) | Review `icons.py` sau khi tự sửa để nhận ảnh PNG thay icon vector | Gửi `icons.py` đã sửa (hàm `load_icon`, `_draw_image_or`), nhờ đánh giá | Tác giả tự viết phần nhận ảnh. AI chỉ ra 2 điểm: ảnh ghi đè độ mờ của painter (nút disabled, radial menu mờ dần), và scale ảnh mỗi lần vẽ gây giật. Đã sửa: `setOpacity(p.opacity() * opacity)`, thêm cache `_SCALED_CACHE`, tách các dòng `if ...: return` theo PEP8 | `py_compile`; người dùng chạy thử với ảnh thật |
| 10/11/2026 | Bảo | F (âm thanh) | Claude (Anthropic) | Thêm âm thanh hiệu ứng và nhạc nền cho game | "Mình muốn thêm âm thanh cho game"; sau đó tự thêm `bgm.ogg` rồi nhờ review | AI viết `gui/sound.py` (`SoundManager`, phát WAV theo tên, im lặng nếu thiếu file/QtMultimedia), `tools/make_sounds.py` (tự tổng hợp 10 file WAV bằng thư viện chuẩn) và bảng chỗ gọi `sound.play(...)` trong `app.py`. Tác giả tự ghép vào `app.py`, thêm fade-in và `bgm.ogg`. AI rà soát, gợi ý hạ âm lượng nhạc nền và hàm `duck()`. | Chạy `python tools/make_sounds.py` ra 10 file đúng độ dài; `py_compile`. AI chưa nghe được âm thanh. Người dùng nghe thử |
| 10/11/2026 | Bảo | F (typography) | Claude (Anthropic) | Làm kiểu chữ theo phong cách gaming trinh thám, chuẩn 4 lớp font | Dán bản thiết kế "System Typography & Text Effects" (Cinzel, Orbitron, Courier Prime, Share Tech Mono; neon glow, gõ chữ từng ký tự, dấu mộc) và nhờ làm theo | AI sửa lại bản thiết kế vì code gốc chạy không đúng: QSS không hỗ trợ `letter-spacing` nên viết `NeonTitle` tự vẽ; chọn font lúc chạy (`init_fonts`, `build_qss`) thay vì danh sách trong QSS; viết `draw_typed` để gõ chữ không nhảy dòng; `Typer`, `TerminalMessage`; `tools/check_fonts.py`; thêm `type.wav`. Cập nhật `theme.py`, `components.py`, `app.py`. Font cần tải riêng (Google Fonts, SIL OFL) | `py_compile`, kiểm tra tên chưa định nghĩa. Chưa chạy GUI ở phía AI. Người dùng chạy `python tools/check_fonts.py` và xem giao diện: [điền kết quả, font có đủ dấu tiếng Việt không] |
| 12/11/2026 | Bảo | F1 | Claude (Anthropic) | Tăng cỡ chữ trên thẻ | "Tăng cỡ chữ trên những tấm thẻ giúp mình; chỉ gửi file đã thay đổi" | Sửa `components.py`: tăng cỡ chữ tên, nghề, manh mối, mã ô, dấu CRIMINAL/INNOCENT; nới khung chứa chữ; thu nhỏ ảnh chân dung để nhường chỗ | `py_compile`; người dùng xem trên lưới 3×3, 4×4, 5×5 |
| 12/11/2026 | Bảo | F5 | Claude (Anthropic) | Đơn giản hóa sổ tay phá án cho dễ đọc, bỏ thông tin đề không yêu cầu | "Bảng sổ tay đang rối, sửa cho đơn giản dễ đọc hơn hoặc lược bỏ thông tin đề không yêu cầu" | Sửa `NotebookPanel`: còn 3 ô thống kê (bước, SAT calls, DPLL ms), mỗi bước tối đa 4 dòng (bước, kết luận, SAT query, clue mới lộ). Decisions/propagations/backtracks chỉ còn ở `experiments/results.csv`. Nhắc lại: trace của đề cần "định danh clue đang dùng", hiện không hiển thị trên GUI | `py_compile`; người dùng đối chiếu với yêu cầu trace trong đề 4.4 |
| 12/11/2026 | Bảo | F1 | Claude (Anthropic) | Đổi mặt ngửa của thẻ sang phong cách phòng thí nghiệm Tiến sĩ Agasa | "Muốn tấm thẻ sau khi lật theo phong cách công nghệ hiện đại như phòng thí nghiệm của tiến sĩ Agasa" | Viết lại `_paint_front` và `_paint_stamp` trong `components.py`: nền tối có lưới và scanline, viền neon đỏ cho CRIMINAL và xanh dương cho INNOCENT, khung góc ngắm, khung kết luận hologram, manh mối kiểu terminal. Bỏ độ nghiêng -5° của dấu mộc | `py_compile`; người dùng xem thẻ lật thực tế |
| 12/11/2026 | Bảo | F3 | Claude (Anthropic) | Đổi màu hiệu ứng kính laser khi chọn clue | "Hiệu ứng kính laser hiển thị clue không nên là màu đỏ nữa, đổi màu nổi bật hơn" | Sửa `_paint_highlight` trong `components.py`: vệt quét, viền và góc ngắm sang xanh lá neon (`#39ff14`), vì thẻ giờ có viền đỏ hoặc xanh dương | `py_compile`; người dùng bấm chọn clue trên thẻ CRIMINAL và INNOCENT |
| 12/11/2026 | Bảo | F (chuyển động) | Claude (Anthropic) | Thêm animation nền và phản hồi tương tác | Dán danh sách ý tưởng: dấu `?` nhịp thở, scanline cuộn, hạt sáng khi lật thẻ, icon nút chuyển động, vòng năng lượng Auto Solve, tia laser nối clue, số đếm lướt, vệt sáng clue mới, LED thông báo | Thêm vào `components.py`: `Clock` dùng chung 20 khung/giây, cache lớp tĩnh của thẻ, cache cỡ chữ, `BeamOverlay`, delegate vệt sáng `ClueListView`, LED `TerminalMessage`, số đếm lướt `NotebookPanel`; `icons.draw_watch(second=...)`. Tác giả thêm 6 dòng vào `app.py` (`BeamOverlay`, `_cell_center`, `beams.show_links/clear`, `btn_auto.set_working`) | `py_compile`, kiểm tra tên chưa định nghĩa, áp thử 6 dòng vào bản `app.py` thì không lỗi. AI chưa chạy GUI nên chưa đo hiệu năng. Người dùng chạy trên lưới 5×5, xem có giật không |
| | | | | | | | |