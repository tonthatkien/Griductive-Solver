# Phân công làm việc và review

> Bản chụp từ file Excel `Griductive_Todolist.xlsx` (ngày chụp: 07/11/2026). **Nguồn chính thức là file Excel**: nếu hai bên khác nhau thì theo Excel và cập nhật lại file này.
> Ngày dự kiến giả định hạn cuối **29/11/2026**; sửa theo deadline thật. Ngày **Review = End − 1**.

## 1. Tổng quan theo người

| Người | Số việc làm | Điểm độ khó (làm) | Số việc review | Điểm độ khó (review) |
|---|---|---|---|---|
| Kiên | 10 | 25 | 9 | 24 |
| Gia Hân | 10 | 25 | 8 | 24 |
| Thảo Vy | 9 | 24 | 10 | 25 |
| Hữu Duy | 8 | 25 | 11 | 26 |
| Bảo Bảo | 10 | 24 | 9 | 24 |

Độ khó chấm từ 1 đến 4 điểm (xem sheet *Tổng quan* trong Excel); mục tiêu mỗi người khoảng 24–25 điểm.

## 2. Theo từng người

### Kiên

**Việc phụ trách**

| ID | Việc | Reviewer | Start | End | Review | Phụ thuộc |
|---|---|---|---|---|---|---|
| A1 | Lưới N×N, tọa độ & ánh xạ ô -> biến SAT | Thảo Vy | 09/11 | 10/11 | 09/11 | - |
| A2 | Clue & Region: clue_cells, validate_clue | Thảo Vy | 10/11 | 13/11 | 12/11 | A1 |
| A3 | Character & GameEngine: load_puzzle, restart | Gia Hân | 11/11 | 14/11 | 13/11 | A1, B1 |
| A4 | PublicKB & get_public_kb | Hữu Duy | 14/11 | 15/11 | 14/11 | A3 |
| A5 | submit_verdict: ACCEPTED / NOT_PROVABLE / CONTRADICTED | Bảo Bảo | 16/11 | 19/11 | 18/11 | A4 |
| E1 | classify: CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT | Thảo Vy | 17/11 | 19/11 | 18/11 | C6, D3 |
| E2 | next_forced & vòng lặp auto_solve | Gia Hân | 19/11 | 21/11 | 20/11 | E1, A5 |
| E3 | Deduction trace | Thảo Vy | 20/11 | 22/11 | 21/11 | E2 |
| E5 | Hint (không đọc hidden solution) | Hữu Duy | 21/11 | 23/11 | 22/11 | E1 |
| H4 | Report: Entailment, uniqueness, deduction loop | Hữu Duy | 24/11 | 27/11 | 26/11 | E5 |

**Việc cần review**

| ID | Việc | Tác giả | Hạn review |
|---|---|---|---|
| A6 | Test Game Engine | Gia Hân | 20/11 |
| B1 | Chốt format JSON puzzle + docs/INTERFACES.md | Gia Hân | 10/11 |
| B6 | Puzzle lỗi để demo + xác nhận duy nhất toàn bộ | Gia Hân | 24/11 |
| C4 | Extension 1: PARITY (số Criminal chẵn/lẻ) | Hữu Duy | 16/11 |
| D3 | DPLL: assumptions & trả SAT/UNSAT kèm model | Bảo Bảo | 15/11 |
| F1 | Khung GUI & vẽ lưới, tọa độ, thẻ úp/ngửa | Thảo Vy | 13/11 |
| F2 | Click đoán verdict & thông báo NOT_PROVABLE / CONTRADICTED | Thảo Vy | 19/11 |
| G1 | Script chạy tự động toàn bộ puzzle | Bảo Bảo | 24/11 |
| H7 | README.md & requirements.txt, thử trên máy sạch | Thảo Vy | 26/11 |

### Gia Hân

**Việc phụ trách**

| ID | Việc | Reviewer | Start | End | Review | Phụ thuộc |
|---|---|---|---|---|---|---|
| A6 | Test Game Engine | Kiên | 19/11 | 21/11 | 20/11 | A5 |
| B1 | Chốt format JSON puzzle + docs/INTERFACES.md | Kiên | 09/11 | 11/11 | 10/11 | - |
| B2 | Brute-force checker (3×3, 4×4) để kiểm tra puzzle sớm | Bảo Bảo | 11/11 | 14/11 | 13/11 | D5 |
| B3 | Puzzle 3×3 (≥ 3 bài) | Hữu Duy | 12/11 | 16/11 | 15/11 | B1, B2 |
| B4 | Puzzle 4×4 (≥ 3 bài) | Thảo Vy | 15/11 | 19/11 | 18/11 | B2 |
| B5 | Puzzle 5×5 (≥ 1 bài, stress case) | Bảo Bảo | 18/11 | 22/11 | 21/11 | B2 |
| B6 | Puzzle lỗi để demo + xác nhận duy nhất toàn bộ | Kiên | 22/11 | 25/11 | 24/11 | E4, B3, B4, B5 |
| G3 | Bảng & biểu đồ thực nghiệm | Bảo Bảo | 26/11 | 28/11 | 27/11 | G2 |
| H1 | Report: Problem formulation & reveal protocol | Thảo Vy | 22/11 | 26/11 | 25/11 | B1 |
| H5 | Report: Experiments | Bảo Bảo | 27/11 | 28/11 | 27/11 | G3 |

**Việc cần review**

| ID | Việc | Tác giả | Hạn review |
|---|---|---|---|
| A3 | Character & GameEngine: load_puzzle, restart | Kiên | 13/11 |
| C1 | Khung Encoder: ánh xạ biến, biến phụ, thống kê | Hữu Duy | 10/11 |
| C2 | Encode FACT, SAME, DIFFERENT | Hữu Duy | 12/11 |
| C5 | Extension 2: COMPARE (so sánh số lượng 2 vùng) | Hữu Duy | 17/11 |
| E2 | next_forced & vòng lặp auto_solve | Kiên | 20/11 |
| E4 | uniqueness_check cho toàn bộ clue | Bảo Bảo | 19/11 |
| F5 | Auto Solve & panel trace | Thảo Vy | 24/11 |
| H6 | Report: phân công + tỷ lệ %, References, Appendix GenAI, gộp PDF | Thảo Vy | 28/11 |

### Thảo Vy

**Việc phụ trách**

| ID | Việc | Reviewer | Start | End | Review | Phụ thuộc |
|---|---|---|---|---|---|---|
| F1 | Khung GUI & vẽ lưới, tọa độ, thẻ úp/ngửa | Kiên | 09/11 | 14/11 | 13/11 | A1 |
| F2 | Click đoán verdict & thông báo NOT_PROVABLE / CONTRADICTED | Kiên | 16/11 | 20/11 | 19/11 | A5, E1 |
| F3 | Highlight clue & hiển thị clue dạng văn bản | Bảo Bảo | 17/11 | 20/11 | 19/11 | A2, F1 |
| F4 | Nút Load, Restart, Hint | Hữu Duy | 21/11 | 24/11 | 23/11 | E5, F2 |
| F5 | Auto Solve & panel trace | Gia Hân | 22/11 | 25/11 | 24/11 | E2, E3, F1 |
| H6 | Report: phân công + tỷ lệ %, References, Appendix GenAI, gộp PDF | Gia Hân | 26/11 | 29/11 | 28/11 | H1, H2, H3, H4, H5 |
| H7 | README.md & requirements.txt, thử trên máy sạch | Kiên | 25/11 | 27/11 | 26/11 | F5 |
| H8 | Quay video demo 5–10 phút có phụ đề/thuyết minh | Hữu Duy | 26/11 | 29/11 | 28/11 | F5, H7 |
| H9 | Upload Drive, test link ẩn danh, đóng gói zip | Bảo Bảo | 29/11 | 29/11 | 28/11 | H6, H8 |

**Việc cần review**

| ID | Việc | Tác giả | Hạn review |
|---|---|---|---|
| A1 | Lưới N×N, tọa độ & ánh xạ ô -> biến SAT | Kiên | 09/11 |
| A2 | Clue & Region: clue_cells, validate_clue | Kiên | 12/11 |
| B4 | Puzzle 4×4 (≥ 3 bài) | Gia Hân | 18/11 |
| C3 | Encode EXACTLY, AT_LEAST, AT_MOST | Hữu Duy | 14/11 |
| D4 | DPLL: thống kê, timeout & test | Bảo Bảo | 17/11 |
| E1 | classify: CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT | Kiên | 18/11 |
| E3 | Deduction trace | Kiên | 21/11 |
| G2 | results.csv đủ cột theo đề | Bảo Bảo | 25/11 |
| H1 | Report: Problem formulation & reveal protocol | Gia Hân | 25/11 |
| H2 | Report: CNF encoding & derivation | Hữu Duy | 25/11 |

### Hữu Duy

**Việc phụ trách**

| ID | Việc | Reviewer | Start | End | Review | Phụ thuộc |
|---|---|---|---|---|---|---|
| C1 | Khung Encoder: ánh xạ biến, biến phụ, thống kê | Gia Hân | 09/11 | 11/11 | 10/11 | B1 |
| C2 | Encode FACT, SAME, DIFFERENT | Gia Hân | 11/11 | 13/11 | 12/11 | C1 |
| C3 | Encode EXACTLY, AT_LEAST, AT_MOST | Thảo Vy | 12/11 | 15/11 | 14/11 | C1 |
| C4 | Extension 1: PARITY (số Criminal chẵn/lẻ) | Kiên | 15/11 | 17/11 | 16/11 | C1 |
| C5 | Extension 2: COMPARE (so sánh số lượng 2 vùng) | Gia Hân | 16/11 | 18/11 | 17/11 | C1 |
| C6 | build_kb: clue đã lật + unit clause verdict | Bảo Bảo | 15/11 | 17/11 | 16/11 | C2, C3, A4 |
| C7 | Test encoder đối chiếu semantic evaluator | Bảo Bảo | 17/11 | 19/11 | 18/11 | C3, D5, D6 |
| H2 | Report: CNF encoding & derivation | Thảo Vy | 22/11 | 26/11 | 25/11 | C3, C5 |

**Việc cần review**

| ID | Việc | Tác giả | Hạn review |
|---|---|---|---|
| A4 | PublicKB & get_public_kb | Kiên | 14/11 |
| B3 | Puzzle 3×3 (≥ 3 bài) | Gia Hân | 15/11 |
| D1 | DPLL: unit propagation & conflict detection | Bảo Bảo | 11/11 |
| D2 | DPLL: chọn biến deterministic, branching, backtracking | Bảo Bảo | 13/11 |
| D5 | Semantic evaluator cho 6 clue core | Bảo Bảo | 11/11 |
| D6 | Semantic evaluator cho 2 extension | Bảo Bảo | 15/11 |
| E5 | Hint (không đọc hidden solution) | Kiên | 22/11 |
| F4 | Nút Load, Restart, Hint | Thảo Vy | 23/11 |
| H3 | Report: Thuật toán DPLL | Bảo Bảo | 25/11 |
| H4 | Report: Entailment, uniqueness, deduction loop | Kiên | 26/11 |
| H8 | Quay video demo 5–10 phút có phụ đề/thuyết minh | Thảo Vy | 28/11 |

### Bảo Bảo

**Việc phụ trách**

| ID | Việc | Reviewer | Start | End | Review | Phụ thuộc |
|---|---|---|---|---|---|---|
| D1 | DPLL: unit propagation & conflict detection | Hữu Duy | 09/11 | 12/11 | 11/11 | - |
| D2 | DPLL: chọn biến deterministic, branching, backtracking | Hữu Duy | 12/11 | 14/11 | 13/11 | D1 |
| D3 | DPLL: assumptions & trả SAT/UNSAT kèm model | Kiên | 14/11 | 16/11 | 15/11 | D2 |
| D4 | DPLL: thống kê, timeout & test | Thảo Vy | 16/11 | 18/11 | 17/11 | D3 |
| D5 | Semantic evaluator cho 6 clue core | Hữu Duy | 09/11 | 12/11 | 11/11 | - |
| D6 | Semantic evaluator cho 2 extension | Hữu Duy | 13/11 | 16/11 | 15/11 | D5 |
| E4 | uniqueness_check cho toàn bộ clue | Gia Hân | 17/11 | 20/11 | 19/11 | D3, C6 |
| G1 | Script chạy tự động toàn bộ puzzle | Kiên | 23/11 | 25/11 | 24/11 | E2, B5 |
| G2 | results.csv đủ cột theo đề | Thảo Vy | 25/11 | 26/11 | 25/11 | G1, D4 |
| H3 | Report: Thuật toán DPLL | Hữu Duy | 22/11 | 26/11 | 25/11 | D4 |

**Việc cần review**

| ID | Việc | Tác giả | Hạn review |
|---|---|---|---|
| A5 | submit_verdict: ACCEPTED / NOT_PROVABLE / CONTRADICTED | Kiên | 18/11 |
| B2 | Brute-force checker (3×3, 4×4) để kiểm tra puzzle sớm | Gia Hân | 13/11 |
| B5 | Puzzle 5×5 (≥ 1 bài, stress case) | Gia Hân | 21/11 |
| C6 | build_kb: clue đã lật + unit clause verdict | Hữu Duy | 16/11 |
| C7 | Test encoder đối chiếu semantic evaluator | Hữu Duy | 18/11 |
| F3 | Highlight clue & hiển thị clue dạng văn bản | Thảo Vy | 19/11 |
| G3 | Bảng & biểu đồ thực nghiệm | Gia Hân | 27/11 |
| H5 | Report: Experiments | Gia Hân | 27/11 |
| H9 | Upload Drive, test link ẩn danh, đóng gói zip | Thảo Vy | 28/11 |

## 3. Ai sở hữu file nào (tham khảo khi sửa file người khác)

| Vùng | Người chính | Ghi chú |
|---|---|---|
| `engine/` (A) | Kiên | `A6` (test engine) do Thảo Vy làm |
| `data/`, `tools/brute_force.py` (B) | Gia Hân | cần `semantic.evaluate` của Bảo Bảo (D5) |
| `logic/cnf_encoder.py` (C) | Hữu Duy | |
| `logic/dpll.py`, `logic/semantic.py` (D) | Bảo Bảo | |
| `logic/agent.py` (E) | Kiên (E1, E2, E3, E5), Bảo Bảo (E4 `uniqueness_check`) | hai người cùng sửa file này, nhắn nhau trước khi sửa |
| `gui/` (F) | Thảo Vy | |
| `experiments/` (G) | Bảo Bảo (G1, G2), Gia Hân (G3) | script chạy và CSV do Bảo Bảo, bảng/biểu đồ do Gia Hân |
| `Report.pdf`, README, video (H) | chia theo Excel | |
