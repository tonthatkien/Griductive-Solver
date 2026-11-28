# Tài liệu tham khảo (dùng cho báo cáo)

> **Quy tắc:** bất cứ thứ gì tham khảo (bài báo, sách, bài hướng dẫn, repo GitHub, câu trả lời StackOverflow, video) đều ghi vào đây
> **và** để comment link ngay trên đoạn code liên quan (nếu dùng ý tưởng/đoạn code). Không copy nguyên repo hay bài của người khác.
> DPLL và CNF encoder phải tự cài đặt.

> ⚠ **Cần kiểm tra:** các DOI và link ở dòng 5, 6, 9, 10 được điền từ trí nhớ khi soạn khung, **chưa mở thử**. Người ghi phải mở từng link xác nhận đúng bài/đúng tác giả trước khi đưa vào báo cáo; link nào sai thì sửa hoặc xóa.

Cột *Người ghi* điền tên người đưa nguồn này vào. Cột *Dùng cho* nên ghi rõ **việc nào (ID Excel)** dùng nguồn này.

## Nguồn dùng chung

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 1 | Đề bài | *Project 2 – Griductive Solver*, CSC14003 Introduction to AI, HCMUS | (file đề của lớp) | Yêu cầu, luật chơi, định nghĩa KB và entailment | cả nhóm | cả nhóm |
| 2 | Trò chơi gốc | Griductive (trang chơi và hướng dẫn chính thức) | (lấy link ở chú thích 1 của đề, trang 1) | Tham khảo luật chơi và giao diện | A, F | |
| 3 | Bài viết | *What is Griductive and how the puzzles are made* (DEV Community) | https://dev.to/_a80b26c075279295b18e9/what-is-griductive-and-how-the-puzzles-are-made-24f5 | Hiểu cách puzzle được sinh, các loại clue, đảm bảo nghiệm duy nhất | B | |

## Logic mệnh đề, SAT, DPLL

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 4 | Sách | Russell & Norvig, *Artificial Intelligence: A Modern Approach* (Chương 7: Logical Agents, phần DPLL) | https://aima.cs.berkeley.edu/ | Lý thuyết logic mệnh đề, CNF, entailment, thuật toán DPLL | C, D, E | |
| 5 | Bài báo | Davis, Logemann, Loveland (1962), *A machine program for theorem-proving*, Communications of the ACM 5(7), 394–397 | https://doi.org/10.1145/368273.368557 | Nguồn gốc thuật toán DPLL | D | |
| 6 | Bài báo | Davis, Putnam (1960), *A Computing Procedure for Quantification Theory*, Journal of the ACM 7(3), 201–215 | https://doi.org/10.1145/321033.321034 | Tiền thân của DPLL | D | |
| 7 | Bài viết | DPLL algorithm (Wikipedia) | https://en.wikipedia.org/wiki/DPLL_algorithm | Pseudo-code tham khảo cho unit propagation, branching | D | |
| 8 | Bài viết | Conjunctive normal form (Wikipedia) | https://en.wikipedia.org/wiki/Conjunctive_normal_form | Định nghĩa CNF, chuyển đổi | C | |
| 9 | Sách | Biere, Heule, van Maaren, Walsh (eds.), *Handbook of Satisfiability* (2nd ed.), IOS Press | https://www.iospress.com/catalog/books/handbook-of-satisfiability-2 | Tổng quan SAT, cardinality constraints, mở rộng của DPLL | C, D | |

## Cardinality constraint (nếu tham khảo thêm cho encoding)

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 10 | Bài báo | Sinz (2005), *Towards an Optimal CNF Encoding of Boolean Cardinality Constraints*, CP 2005, LNCS 3709 | https://doi.org/10.1007/11564751_73 | So sánh với encoding combinatorial trực tiếp; mở rộng cho vùng lớn (chỉ nêu trong báo cáo nếu có dùng) | C, H2 | |

## Công cụ và thư viện

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 11 | Tài liệu thư viện | Pygame Documentation | https://www.pygame.org/docs/ | Xây dựng GUI (nếu nhóm chọn Pygame) | F | |

## Fonts (GUI)

> Cả 4 họ font đều tải từ Google Fonts và dùng giấy phép **SIL Open Font License 1.1** (được dùng, nhúng và phân phối trong sản phẩm, kể cả dùng cho đồ án). Chỉ nên đưa vào báo cáo họ font nào thực sự có trong giao diện. ⚠ Link chưa mở thử, người ghi cần kiểm tra lại như các nguồn ở trên.

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 12 | Font | Cinzel (Natanael Gama), file: Regular, Medium, SemiBold, Bold, ExtraBold, Black và bản VariableFont_wght. Giấy phép SIL OFL 1.1 | https://fonts.google.com/specimen/Cinzel | Font tiêu đề / chữ trang trí trong giao diện | F | |
| 13 | Font | Courier Prime (Alan Dague-Greene, Quote-Unquote Apps), file: Regular, Italic, Bold, BoldItalic. Giấy phép SIL OFL 1.1 | https://fonts.google.com/specimen/Courier+Prime | Font monospace cho nội dung clue, KB, log | F | |
| 14 | Font | Orbitron (Matt McInerney), file: Regular, Medium, SemiBold, Bold, ExtraBold, Black và bản VariableFont_wght. Giấy phép SIL OFL 1.1 | https://fonts.google.com/specimen/Orbitron | Font số / nhãn kiểu công nghệ trong giao diện | F | |
| 15 | Font | Share Tech Mono (Carrois Apostrophe), file: Regular. Giấy phép SIL OFL 1.1 | https://fonts.google.com/specimen/Share+Tech+Mono | Font monospace cho thông số, số liệu (thống kê solver) | F | |
| 16 | Font | Be Vietnam Pro (Lâm Bảo, Tony Le, ViệtAnh Nguyễn), file `BeVietnamPro-Regular.ttf`. Giấy phép SIL OFL 1.1 | https://fontsource.org/fonts/be-vietnam-pro/about (nguồn gốc: https://github.com/bettergui/BeVietnamPro) | Chữ nội dung manh mối và các dòng thông báo có dấu tiếng Việt (Cinzel, Orbitron không đủ glyph) | F | Bảo |
| 17 | Font | Tektur (Adam Jagosz), file `Tektur-Regular.ttf`. Giấy phép SIL OFL 1.1 | https://fontsource.org/fonts/tektur/about (nguồn gốc: https://github.com/hyvyys/Tektur) | Tiêu đề và nhãn có dấu tiếng Việt thay cho Orbitron/Cinzel (xem `theme.display()`) | F | Bảo |

## Hình ảnh (GUI)

> Hình nhân vật Detective Conan có bản quyền của chủ sở hữu (tác giả Gosho Aoyama và các đơn vị phát hành). Ghi rõ nguồn từng ảnh; nếu nộp hoặc công khai sản phẩm thì nêu mục đích học tập, phi thương mại.

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 18 | Hình ảnh | Ảnh chân dung 17 nhân vật `gui/assets/characters/*.png` (akai, amuro, chiba, conan, jodie, kaito, makoto, megure, ran, sato, shinichi, shiratori, sonoko, subaru, takagi, yukiko, yusaku) | Pinterest | Chân dung trên thẻ nghi phạm | F1 | Bảo |
| 19 | Hình ảnh | Ảnh Conan (`conan_happy`, `conan_neutral`, `conan_shake`, `conan_shock`, `conan_think`) và bóng đen hung thủ (`villain`) trong `gui/assets/icons/` | Pinterest | Avatar Conan trong bong bóng thoại và ảnh hung thủ trên trang chủ | F | Bảo |

## Âm thanh (GUI)

| STT | Loại | Tên / Tác giả | Link | Dùng để làm gì | Dùng cho (ID) | Người ghi |
|---|---|---|---|---|---|---|
| 20 | Âm thanh | `click.wav`, tải từ Mixkit (Mixkit Sound Effects Free License) | https://mixkit.co/free-sound-effects/ | Âm thanh khi click chuột | F | |
| 21 | Âm thanh | `clue.wav`, tải từ Mixkit (Mixkit Sound Effects Free License) | https://mixkit.co/free-sound-effects/ | Âm thanh khi chọn / hiện clue | F | |
| 22 | Âm thanh | `hint.wav`, tải từ Mixkit (Mixkit Sound Effects Free License) | https://mixkit.co/free-sound-effects/ | Âm thanh khi dùng gợi ý | F | |
| 23 | Âm thanh | `radial.wav`, tải từ Mixkit (Mixkit Sound Effects Free License) | https://mixkit.co/free-sound-effects/ | Âm thanh khi mở menu radial | F | |
| 24 | Âm thanh | `step.wav`, tải từ Mixkit (Mixkit Sound Effects Free License) | https://mixkit.co/free-sound-effects/ | Âm thanh khi solver chạy từng bước | F | |
| 25 | Nhạc nền |`bgm.ogg`, `level_01.ogg` … `level_09.ogg`  | https://archive.org/details/DetectiveConanOriginalSountrack1 | Nhạc nền theo màn chơi (`gui/sound.py`, `gui/levels.py`) | F | Bảo |
