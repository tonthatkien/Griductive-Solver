# Quy định làm việc nhóm

> **Tóm tắt 1 phút**
> - Không push thẳng `main`. Mọi thay đổi đi qua **nhánh → Pull Request → review → Squash and merge**.
> - Mỗi việc trong file Excel (ID như `C3`) có **1 người làm + 1 người review**. Không ai tự duyệt việc của mình.
> - Test phải **xanh**, `python main.py` phải chạy được trước khi mở PR.
> - Ngày **Review** trong Excel = ngày **End − 1**: PR phải mở sớm để người review kịp xem trước hạn.
> - Dùng AI hay chép code từ nguồn ngoài thì **ghi lại ngay** (`docs/AI_USAGE_LOG.md`, `docs/REFERENCES.md`).
> - Ai cũng phải **giải thích được code mình viết và code mình đã duyệt** (có vấn đáp, đạo văn = 0 điểm môn).

Có **5 người** cùng sửa một repo, nên các quy định dưới đây để **không ai làm hỏng việc của ai** và để **ai cũng
giải thích được code của mình khi bị vấn đáp**.

## Bộ tài liệu đi kèm

| Cần gì | Đọc file nào |
|---|---|
| Dùng Git từng bước (clone, nhánh, PR, conflict) | [`docs/GIT_GUIDE.md`](docs/GIT_GUIDE.md) |
| Quy ước viết code, kiến trúc, ai được gọi ai | [`docs/CODING_STANDARDS.md`](docs/CODING_STANDARDS.md) |
| Cách review, checklist theo từng loại việc | [`docs/REVIEW_GUIDE.md`](docs/REVIEW_GUIDE.md) |
| Ai làm việc gì, ai review ai | [`docs/REVIEW_ASSIGNMENTS.md`](docs/REVIEW_ASSIGNMENTS.md) và file Excel `Griductive_Todolist.xlsx` |
| Hợp đồng giữa các module (biến SAT, JSON puzzle, chữ ký hàm) | [`docs/INTERFACES.md`](docs/INTERFACES.md) |
| Ghi nhận AI và nguồn tham khảo cho báo cáo | [`docs/AI_USAGE_LOG.md`](docs/AI_USAGE_LOG.md), [`docs/REFERENCES.md`](docs/REFERENCES.md) |

> **Nguồn sự thật về tiến độ là file Excel.** `docs/REVIEW_ASSIGNMENTS.md` chỉ là bản chụp để tra cứu nhanh.

---

## 1. Năm quy tắc không được vi phạm

1. **Không push thẳng lên `main`.** Mọi thay đổi đi qua nhánh + Pull Request (PR).
2. **Không tự merge PR của mình** khi người review (cột *Reviewer 1* trong Excel) chưa bấm *Approve*.
3. **Không tự ý đổi "hợp đồng"** giữa các module (danh sách ở mục 7). Muốn đổi → làm theo mục 7.
4. **Không push code không chạy được** vào `main`: test phải xanh, `python main.py` phải chạy.
5. **Không commit file rác / bí mật**: `venv/`, `__pycache__/`, `results.csv` lớn, token, file cá nhân.

---

## 2. Quy trình cho một việc (từ lúc nhận đến lúc xong)

```
Chưa làm ──► Đang làm ──► Chờ review ──► Hoàn thành
   (1)          (2–4)        (5–7)           (8)
```

| Bước | Ai | Làm gì |
|---|---|---|
| 1 | Người làm | Kiểm tra cột *Dependency*: việc phụ thuộc đã **Hoàn thành** chưa? Chưa thì báo nhóm, đừng làm chồng lên. |
| 2 | Người làm | Đổi trạng thái thành **Đang làm**. `git checkout main && git pull`. |
| 3 | Người làm | Tạo nhánh `feature/<tên>-<ID>` (vd `feature/duy-C3`). |
| 4 | Người làm | Code + viết test + chạy `python -m unittest discover -s tests -t .` đến khi xanh. Commit nhỏ, rõ (mục 3). |
| 5 | Người làm | `git push`, mở **PR** vào `main`, điền đủ mẫu PR. Nhắn người review trong nhóm chat (kèm link PR). Đổi trạng thái thành **Chờ review**. |
| 6 | Người review | Review trong **24 giờ** và **không muộn hơn ngày Review** trong Excel (xem `docs/REVIEW_GUIDE.md`). |
| 7 | Người làm | Có `[must]` thì sửa trong **24 giờ**, push thêm commit vào cùng nhánh, báo lại. |
| 8 | Người làm | Khi đã *Approve* + CI xanh: **Squash and merge**, xóa nhánh, đổi trạng thái thành **Hoàn thành**. |

**Một PR = một việc** (hoặc 2–3 việc rất nhỏ liền nhau). PR nên **dưới ~300 dòng thay đổi**; to hơn thì tách ra.

### Lịch của một việc

```
Start ─────────────── (mở PR chậm nhất ở đây) ─── Review (= End − 1) ─── End
                                ▲                         ▲                ▲
                          PR đã mở, đã nhắn          người review       sửa xong,
                          người review               xong review        merge xong
```

Việc nào trễ so với lịch, **báo trước ít nhất 1 ngày** (mục 8).

---

## 3. Nhánh, commit, Pull Request

| Thứ | Quy ước | Ví dụ |
|---|---|---|
| Nhánh thêm tính năng | `feature/<tên>-<ID>` | `feature/duy-C3` |
| Nhánh sửa lỗi | `fix/<tên>-<mô-tả-ngắn>` | `fix/bao-dpll-backtrack-count` |
| Nhánh tài liệu / báo cáo | `docs/<tên>-<mô-tả>` | `docs/vy-report-experiments` |
| Commit | `[ID] Động từ + nội dung ngắn` | `[C3] Add AT_MOST combinatorial encoding` |
| Tiêu đề PR | `[ID] Tên việc` | `[C3] Encode EXACTLY / AT_LEAST / AT_MOST` |

- Commit nhỏ, mỗi commit một ý. **Không** commit kiểu `update`, `fix`, `abc`.
- PR điền theo mẫu có sẵn (`.github/pull_request_template.md`): làm gì, cách kiểm tra, checklist.
- Dùng **Squash and merge** để lịch sử `main` gọn (một việc = một commit).
- **Trước khi mở PR:** `git fetch && git merge origin/main` vào nhánh của mình, giải quyết conflict ở máy mình.

---

## 4. Review (tóm tắt, chi tiết ở `docs/REVIEW_GUIDE.md`)

- Người review của từng việc nằm ở cột *Reviewer 1* trong Excel. Không ai review việc của chính mình.
- Review phải **chạy code thật** (checkout nhánh, chạy test), không chỉ đọc lướt. Không "LGTM" suông:
  mỗi lần Approve ghi **ít nhất một câu** nói đã kiểm tra điều gì.
- Gắn nhãn nhận xét: `[must]` (bắt buộc sửa), `[suggest]` (nên sửa), `[question]` (hỏi để hiểu), `[nit]` (lặt vặt, không chặn).
- Ý kiến khác nhau mà không thống nhất được trong 24 giờ → hỏi **trưởng nhóm** (ghi tên ở `README.md`), trưởng nhóm quyết định.
- **Quan trọng cho vấn đáp:** người review cũng phải giải thích được đoạn code mình đã duyệt.
- Việc không phải code (báo cáo, video, bộ puzzle) cũng được review theo checklist trong `REVIEW_GUIDE.md`.

---

## 5. "Xong" nghĩa là gì (Definition of Done)

Một việc chỉ được đánh dấu **Hoàn thành** khi đủ tất cả:

- [ ] Code chạy được, không còn `TODO(<ID>)` của việc đó trong code.
- [ ] Có unit test cho logic mới và `python -m unittest discover -s tests -t .` **xanh**.
- [ ] Tuân thủ `docs/CODING_STANDARDS.md` (type hint, docstring cho hàm công khai, đặt tên đúng).
- [ ] PR đã được người review **Approve**, CI xanh, đã merge vào `main`.
- [ ] Đã cập nhật cột *Trạng thái* trong file Excel.
- [ ] Nếu dùng AI hoặc tài liệu ngoài: đã ghi vào `docs/AI_USAGE_LOG.md` / `docs/REFERENCES.md`.

---

## 6. Test

- Logic **bắt buộc có unit test** (thư mục `tests/`, tên file `test_*.py`, dùng `unittest`).
- Test không phụ thuộc GUI và không đọc file ngoài `data/` và `tests/`.
- Chạy trong thư mục `Source/`: `python -m unittest discover -s tests -t .`
- Các test **bắt buộc** của dự án này (đối chiếu chéo để bắt lỗi logic):

| Test | Việc | Mục đích |
|---|---|---|
| Encoder ↔ semantic evaluator | C7 | Với mọi assignment nhỏ, CNF của clue đúng ⇔ `evaluate()` đúng. Bắt lỗi cardinality encoding. |
| DPLL ↔ brute force | D4 | Random CNF nhỏ cho cùng kết quả SAT/UNSAT với duyệt toàn bộ. |
| Ví dụ trong đề | D4 | `KB = (A∨B) ∧ (¬A∨B)` ⇒ `B` là Criminal, `A` là UNKNOWN. |
| `PublicKB` không rò rỉ | A6 | Không chứa nhãn ẩn và clue chưa lật. |
| Puzzle duy nhất | B6 | Mọi puzzle trong `data/` có đúng 1 nghiệm (brute force và DPLL cùng kết luận). |
| Agent không đoán bừa | E2 | Mỗi verdict agent đưa ra đều khớp nghiệm ẩn; puzzle mơ hồ thì dừng ở STUCK. |

- CI (GitHub Actions) tự chạy test mỗi khi có PR. **PR đỏ thì không merge.**

---

## 7. Đổi "hợp đồng" giữa các module

Hợp đồng gồm: quy ước **cell id và đánh số biến SAT**, **định dạng JSON puzzle**, `Clue` (`engine/clue.py`),
`PublicKB` (`engine/game_state.py`), `KB` / `Encoder.build_kb` (`logic/cnf_encoder.py`),
`DPLLSolver.solve` / `SolveResult` (`logic/dpll.py`), `LogicAgent.classify` và các kết quả
`CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT`. Chi tiết ở `docs/INTERFACES.md`.

1. Người muốn đổi nhắn vào nhóm chat: *đổi gì, vì sao, ai bị ảnh hưởng*.
2. **Cả 5 người** phản hồi (✅ hoặc ý kiến) trong 24 giờ. Không phản hồi coi như chưa đồng ý, nhắc lại.
3. Tạo PR **riêng** chỉ chứa thay đổi này, cần **2 người duyệt** (người review + người dùng thay đổi nhiều nhất), và cập nhật `docs/INTERFACES.md` trong cùng PR.
4. Sau khi merge, thông báo cả nhóm để mọi người `git pull` và sửa phần của mình.

---

## 8. Giao tiếp và tiến độ

- **Cập nhật hàng ngày** (một tin ngắn trong nhóm chat): *hôm qua làm gì – hôm nay làm gì – đang vướng gì*.
- **Họp:** 1 buổi khởi động (chốt format JSON, 2 extension, thư viện GUI), sau đó 2 buổi mỗi tuần
  (đầu tuần và giữa tuần, 20–30 phút) để xem lịch trong file Excel.
- **Vướng việc → báo trong vòng 24 giờ.** Đừng im lặng rồi trễ hạn.
- **Sắp trễ hạn → báo trước ít nhất 1 ngày** để nhóm chia lại việc. Chia lại việc thì sửa cột *Owner* trong Excel
  và ghi chú lý do ở cột *Note*, để lúc báo cáo tính % đóng góp cho chính xác.
- Hỏi giúp là bình thường. Nhưng **mỗi người vẫn phải tự hiểu** code mình nộp.

---

## 9. AI, nguồn tham khảo và liêm chính học thuật

Đề cho phép dùng AI nhưng giảng viên có thể **phỏng vấn ngẫu nhiên**, và **đạo văn = 0 điểm môn**.

- Dùng AI (ChatGPT, Claude, Copilot...) cho việc đáng kể thì **ghi vào `docs/AI_USAGE_LOG.md`**
  (prompt, kết quả, cách kiểm chứng). Báo cáo bắt buộc có phụ lục này.
- Code lấy từ GitHub / StackOverflow / bài viết: **ghi nguồn vào `docs/REFERENCES.md` và để comment link ngay trên đoạn code**.
  Cấm copy nguyên repo/bài của người khác nộp như của mình.
- **Phải tự cài đặt** DPLL và CNF encoder. Không dùng thư viện SAT / logic có sẵn (`pysat`, `z3`, `sympy.logic`...) cho phần lõi.
- Code do AI sinh ra phải được **đọc hiểu, chạy thử, có test** trước khi commit. Không commit thứ mình không giải thích được.
- Trước hạn nộp, mỗi người tự hỏi: *"mình có giải thích được từng file mình viết và từng PR mình review không?"*

---

## 10. Xung đột, lỗi và khẩn cấp

- **Merge conflict:** tự giải quyết ở nhánh của mình (xem `docs/GIT_GUIDE.md`, mục 6). Không hiểu thì gọi người vừa sửa file đó.
- **`main` bị hỏng** (test đỏ / không chạy): báo ngay vào nhóm chat. Người merge PR gây lỗi ưu tiên sửa hoặc `git revert` trong vài giờ.
- **Không dùng** `git push --force` lên `main`, không xóa nhánh của người khác, không rewrite lịch sử đã merge.

---

## 11. Chốt code và nộp bài

- **Code freeze:** 1 ngày trước hạn nộp. Sau mốc này chỉ sửa lỗi nghiêm trọng, và vẫn qua PR + review.
- Người phụ trách đóng gói (việc `H9` trong Excel) tạo tag `v1.0-submission` trên commit cuối, rồi nén thư mục
  đúng định dạng đề: `StudentID1_StudentID2_...` gồm `Source/` và `Report.pdf`
  (không có `.git`, `venv`, `__pycache__`).
- Chạy thử `README.md` trên **máy sạch**: tạo venv mới, `pip install -r requirements.txt`, `python main.py`.
- **Video demo:** upload lên **Google Drive**, chia sẻ *Anyone with the link can view*, kiểm tra bằng cửa sổ ẩn danh.
  **KHÔNG dùng YouTube** (đề Project 2 cấm). Link video và bảng phân công %/đóng góp phải có trong `Report.pdf`.
