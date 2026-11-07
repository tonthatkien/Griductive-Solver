# Hướng dẫn review

Review không phải để "bắt lỗi" mà để: (1) **code đúng**, (2) **cả hai người cùng hiểu code**, (3) **sẵn sàng cho vấn đáp**.
Người review cũng phải giải thích được phần mình đã duyệt.

## 1. Ai review ai, khi nào

- Xem cột **Reviewer 1** trong file Excel, hoặc [`REVIEW_ASSIGNMENTS.md`](REVIEW_ASSIGNMENTS.md).
- Không ai review việc của chính mình. Cần đổi người review thì sửa trong Excel và báo nhóm.
- Thời hạn: review **trong 24 giờ** kể từ khi được báo, và **không muộn hơn ngày Review** (= End − 1) trong Excel.
  Bận thì báo sớm để đổi người.

## 2. Quy trình của người review

1. Đọc **mô tả PR** (làm gì, cách kiểm tra). Đọc lại mô tả việc trong Excel (cột *Task*, *Detail*, *Dependency*).
2. **Chạy thật**:
   ```bash
   git fetch origin
   git checkout feature/duy-C3
   cd MSSV1_MSSV2_MSSV3_MSSV4/Source
   pip install -r requirements.txt
   python -m unittest discover -s tests -t .
   python main.py            # hoặc cách kiểm tra ghi trong PR
   ```
3. Đọc code theo checklist ở mục 3 và 4. Đọc **cả test**: test có thật sự kiểm tra điều quan trọng không?
4. Viết nhận xét trên GitHub (*Files changed* → dấu `+` cạnh dòng code, hoặc *Review changes* ở góc trên):
   - **Approve**: đủ điều kiện ở mục 5, ghi ít nhất một câu nói đã kiểm tra gì.
   - **Request changes**: có `[must]` cần sửa.
   - **Comment**: mới chỉ hỏi/góp ý, chưa quyết định.
5. Tác giả sửa xong thì **xem lại đúng những chỗ đã yêu cầu sửa**, rồi Approve.

## 3. Checklist chung (mọi PR)

- [ ] PR chỉ làm **một việc** và đúng với việc có ID trong Excel; không lẫn thay đổi không liên quan.
- [ ] Tuân thủ `CONTRIBUTING.md` (nhánh, commit message, mô tả PR) và `docs/CODING_STANDARDS.md`.
- [ ] Chạy được. Test **xanh** trên máy mình (không chỉ tin CI).
- [ ] Có **test mới** cho logic mới; test kiểm tra hành vi thật, không chỉ "chạy qua".
- [ ] Không đụng "hợp đồng" (`docs/INTERFACES.md`) trừ khi cả nhóm đã đồng ý.
- [ ] Không có code chết, `print` gỡ lỗi, file rác, bí mật.
- [ ] Nếu có code từ AI/nguồn ngoài: đã ghi `docs/AI_USAGE_LOG.md` / `docs/REFERENCES.md`.
- [ ] Mình **hiểu** đoạn code này và có thể giải thích lại. Chưa hiểu → hỏi (`[question]`), đừng Approve.

## 4. Checklist theo loại việc

**Game Engine (Scope A: `engine/`)**
- [ ] Cell id, hàng/cột, neighbors đúng (góc 3 ô, biên 5 ô, giữa 8 ô; không gồm chính ô đó).
- [ ] `validate_clue` bắt đủ: ô ngoài lưới, vùng rỗng, `k` ngoài `[0, |R|]`, kiểu clue lạ.
- [ ] `PublicKB` **không chứa** nhãn ẩn và clue chưa lật; agent không có đường nào đọc `_solution` / `_clues`.
- [ ] `submit_verdict`: `ACCEPTED` thì lật thẻ + lộ clue; `NOT_PROVABLE` / `CONTRADICTED` thì **không đổi state, không lộ clue**.
- [ ] Thẻ face-up ban đầu được tính vào KB đúng cách; `restart()` trả đúng trạng thái đầu.

**Dữ liệu puzzle (Scope B: `data/`, brute-force checker)**
- [ ] Đúng format JSON ở `docs/INTERFACES.md`; nạp được bằng loader.
- [ ] Puzzle có **đúng một nghiệm** (kiểm bằng brute force và/hoặc `uniqueness_check`).
- [ ] Bộ puzzle dùng đủ 6 clue core + 2 extension; độ khó tăng dần; có bài cần nhiều reveal wave.
- [ ] Brute-force checker dùng `semantic.evaluate`, **không** dùng CNF encoder (để kiểm chứng độc lập).
- [ ] Puzzle lỗi (mơ hồ / mâu thuẫn) để demo được tách riêng, tên rõ ràng.

**CNF Encoder (Scope C: `logic/cnf_encoder.py`)**
- [ ] `SAME`, `DIFFERENT` đúng bảng chân trị (4 tổ hợp).
- [ ] `AT_MOST k` sinh `C(m, k+1)` clause, `AT_LEAST k` sinh `C(m, m-k+1)` clause; `EXACTLY = AT_MOST ∧ AT_LEAST`.
- [ ] Biên: `k = 0`, `k = |R|`, vùng 1 ô, `|R| = k`; không sinh clause rỗng sai chỗ.
- [ ] Biến phụ bắt đầu từ `N*N + 1` và được đếm đúng; biến phụ **tách riêng** khỏi biến primary.
- [ ] `build_kb` chỉ gồm clue đã lật + unit clause của verdict đã chứng minh.
- [ ] Không có CNF viết tay cho puzzle cụ thể. Extension được mô tả encoding trong docstring.
- [ ] Có test đối chiếu với semantic evaluator trên **mọi** assignment của vùng nhỏ.

**DPLL và Semantic Evaluator (Scope D: `logic/dpll.py`, `logic/semantic.py`)**
- [ ] DPLL **tự cài đặt**, không import thư viện SAT. Có unit propagation, phát hiện conflict, branching, backtracking.
- [ ] Không sửa danh sách clause đầu vào; `assumptions` hoạt động đúng như unit clause tạm thời.
- [ ] Chọn biến xác định; chạy hai lần cho cùng kết quả và cùng số liệu.
- [ ] SAT trả model đầy đủ **và model đó thật sự thỏa mọi clause** (có test tự kiểm); UNSAT trả `None`.
- [ ] `decisions` / `propagations` / `backtracks` đếm theo đúng định nghĩa trong docstring; có `timeout`.
- [ ] Test DPLL: ví dụ trong đề, random CNF nhỏ so với brute force (có seed).
- [ ] Semantic evaluator có đủ 6 core + 2 extension, **không gọi encoder**, kiểm cả biên (`k = 0`, `k = |R|`).

**Logic Agent (Scope E: `logic/agent.py`)**
- [ ] `classify` đúng 4 kết quả theo định nghĩa (UNSAT của `KB ∧ ¬Ci` ⇒ CRIMINAL, v.v.); `INCONSISTENT` khi bản thân KB UNSAT.
- [ ] **Không đoán**: không có nhánh trả verdict khi chưa được chứng minh; hết ô forced thì dừng (STUCK).
- [ ] Chọn ô forced theo **row-major**; kết quả lặp lại được.
- [ ] Mỗi bước accept xong, KB được cập nhật bằng clue mới lộ (KB_{t+1}) chứ không dựng lại từ dữ liệu ẩn.
- [ ] Trace đủ: step, clue active, SAT queries, verdict, clue mới.
- [ ] `uniqueness_check` đúng (blocking clause, dừng khi tìm được nghiệm thứ hai); chỉ dùng cho tooling.
- [ ] `hint` không đọc nghiệm ẩn.

**GUI (Scope F: `gui/`)**
- [ ] Hiển thị đủ: lưới, tọa độ (A, B, C… / 1, 2, 3…), tên, nghề, thẻ úp/ngửa, trạng thái Criminal/Innocent, clue đã mở.
- [ ] Click đoán CRIMINAL/INNOCENT; hiển thị **khác nhau** `NOT_PROVABLE` và `CONTRADICTED`; **không lật thẻ** khi bị từ chối.
- [ ] Click clue đã mở thì sáng đúng các ô clue nhắc tới.
- [ ] Có nút Load, Restart, Hint, Auto Solve; Auto Solve không làm đứng hình, có Pause/Step.
- [ ] GUI **không tự cài luật** hay suy luận; mọi thứ đi qua engine/agent.

**Thực nghiệm (Scope G: `experiments/`)**
- [ ] Dùng **cùng bộ puzzle** cho mọi so sánh; chạy lặp lại được.
- [ ] CSV đủ cột theo đề: primary/aux vars, clauses, SAT calls, decisions, propagations, backtracks, deduction steps/reveal waves, runtime.
- [ ] Ghi cả `STUCK` / `INCONSISTENT` / `TIMEOUT`, **không loại failure** khỏi bảng.
- [ ] Biểu đồ có tiêu đề, nhãn trục, đơn vị, chú thích; số liệu khớp CSV.

**Báo cáo (`Report.pdf` / bản nháp)**
- [ ] Đủ mục theo đề: phân công + % hoàn thành, hình thức hóa bài toán (biến, clue, KB, reveal protocol), CNF (1 clue nhị phân + 1 clue đếm), thuật toán (DPLL, entailment, uniqueness, deduction loop), thực nghiệm, tài liệu tham khảo, phụ lục AI.
- [ ] Công thức/ký hiệu **nhất quán với code** (cùng tên biến `Ci`, cùng định nghĩa decisions/propagations/backtracks).
- [ ] Số liệu trong bảng/biểu đồ **khớp** kết quả chạy thật; nhận xét có lập luận, không chỉ mô tả bảng; có failure cases và hạn chế.
- [ ] Trích dẫn đầy đủ, không có đoạn sao chép nguyên văn.

**Video**
- [ ] Đủ hai phần: giao diện, và tính năng (chơi tay có cố tình đoán sai ra `NOT_PROVABLE`, highlight clue, chạy Auto Solve và show nghiệm).
- [ ] Có thuyết minh hoặc phụ đề (Anh/Việt); hình và tiếng rõ; dài khoảng 5–10 phút.
- [ ] Link **Google Drive**, quyền *Anyone with the link can view*, đã thử bằng cửa sổ ẩn danh; **không dùng YouTube**; link đã ghi vào báo cáo.

## 5. Khi nào được Approve

Approve khi **tất cả** đúng:
1. Chạy được và test xanh trên máy người review.
2. Không còn `[must]` nào chưa được xử lý.
3. Người review **hiểu và giải thích được** những gì PR làm.

## 6. Cách viết nhận xét tốt

Dùng nhãn ở đầu mỗi nhận xét:

| Nhãn | Ý nghĩa |
|---|---|
| `[must]` | Bắt buộc sửa trước khi merge (sai logic, thiếu test quan trọng, vi phạm hợp đồng, rò nhãn ẩn…) |
| `[suggest]` | Nên sửa; tác giả có thể từ chối nếu có lý do |
| `[question]` | Hỏi để hiểu, chưa phải yêu cầu sửa |
| `[nit]` | Lặt vặt (đặt tên, định dạng), không chặn merge |

Nguyên tắc: **nói về code, không nói về người**; **cụ thể** (dòng nào, vì sao, gợi ý cách sửa); **lịch sự**; **một nhận xét một ý**.

| Nên | Không nên |
|---|---|
| `[must] Ở dòng 42, EXACTLY k=0 vẫn sinh clause rỗng nên KB luôn UNSAT. Test mẫu: vùng 3 ô, k=0 phải cho 3 unit clause ¬Ci.` | "Code này sai." |
| `[question] Vì sao đếm propagation cả khi literal đã có giá trị? Có ảnh hưởng số liệu thực nghiệm không?` | "Làm lại đi." |
| `[nit] Đổi tên biến n2 thành num_aux cho dễ đọc.` | "LGTM" mà chưa chạy thử. |

## 7. Dành cho tác giả khi nhận review

- Cảm ơn và **trả lời từng nhận xét**: đã sửa (kèm commit), hoặc giải thích vì sao không sửa.
- Đừng tranh luận nhiều vòng bằng chữ: không thống nhất sau 1–2 lượt thì **gọi nhau 5 phút** hoặc hỏi trưởng nhóm.
- Sau khi sửa xong, báo người review và cập nhật trạng thái trong Excel.

## 8. Ý kiến khác nhau

Không thống nhất được trong 24 giờ → hỏi **trưởng nhóm**. Trưởng nhóm quyết định và ghi lại ngắn gọn lý do trong PR.
Nếu vấn đề là về "hợp đồng" giữa các module thì áp dụng quy trình ở `CONTRIBUTING.md`, mục 7.
