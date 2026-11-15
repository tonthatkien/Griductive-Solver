# Brute-force checker B2

Công cụ kiểm tra puzzle 3×3 và 4×4 bằng `logic.semantic.evaluate`, độc lập với DPLL
và CNF encoder. Cần Python 3.10+; không cần thư viện bổ sung. Clue dùng schema và
validator chung trong `engine.clue`.

## Cách chạy

Chạy trong `Source/` (dùng `python3` nếu máy không có lệnh `python`):

```bash
python -m tools.brute_force data/puzzles_3x3/p01.json
python -m tools.brute_force data/puzzles_3x3/p01.json --stop-after-two
python -m unittest -v tests.test_brute_force
python -m unittest discover -s tests -t .
```

CLI in kết quả JSON. Mã thoát `0`: kiểm tra hoàn tất; `1`: tìm được nghiệm duy nhất
nhưng nhãn lưu sẵn không khớp nghiệm; `2`: dữ liệu sai hoặc evaluator lỗi. Với mã
`1`, JSON vẫn chứa nghiệm tìm được và `labels_match_solution=false`; không đổi
kết luận về số nghiệm thành UNSAT. Mã `0` tự nó không khẳng định puzzle UNIQUE:
cần đọc trường `status`.

## API và phạm vi dữ liệu

```python
from tools.brute_force import check_puzzle, check_public_kb, count_solutions

full = check_puzzle(puzzle)  # dict đọc từ JSON; toàn bộ clue + trạng thái face-up ban đầu
public = check_public_kb(engine.get_public_kb())  # chỉ clue đã lật + verdict đã chứng minh
subset = count_solutions(clues, 3, known_statuses={"A1": False})
```

`True` là Criminal, `False` là Innocent. `count_solutions` nhận các đối tượng `Clue`
và tập public fact Boolean, cho phép tập clue rỗng. `check_public_kb` chuyển các
verdict CRIMINAL/INNOCENT của `PublicKB` sang Boolean, từ chối verdict sai hoặc
UNKNOWN/INCONSISTENT. Không nhận hoặc truy cập dữ liệu ẩn của engine.

`check_puzzle` dành cho kiểm tra toàn bộ puzzle, sử dụng cả clue của thẻ úp. Chỉ
nhãn của các ô `initially_revealed` làm ràng buộc khi tìm nghiệm. Sau khi tìm xong,
các nhãn lưu sẵn mới được so với nghiệm duy nhất để phát hiện lỗi dữ liệu; chúng
không lọc assignment. Puzzle, clue và PublicKB đầu vào không bị thay đổi.

Puzzle phải có đúng N² character, một clue hợp lệ cho mỗi ô, các tên tăng nghiêm
ngặt theo `casefold()` ở thứ tự row-major và danh sách face-up không rỗng/không
trùng. Sai schema ném `ValueError`; UNSAT/MULTIPLE là kết quả kiểm tra hợp lệ.

## Kết quả và dừng sớm

`CheckResult` có các trường:

| Trường | Ý nghĩa |
|---|---|
| `assignments_checked` | Số assignment đã duyệt, gồm cả assignment bị public fact loại |
| `satisfying_assignments` | Số nghiệm tìm được; là cận dưới khi chưa duyệt hết |
| `status` | UNSAT, UNIQUE hoặc MULTIPLE |
| `unique_solution` | Nghiệm duy nhất sau duyệt hết, hoặc `None` |
| `exhaustive`, `count_is_exact` | Đã duyệt hết không gian và có số đếm chính xác |
| `classifications` | CRIMINAL/INNOCENT/UNKNOWN cho từng ô qua tất cả nghiệm; UNSAT thì mọi ô INCONSISTENT; tìm kiếm chưa đầy đủ thì `None` |
| `labels_match_solution` | So nhãn sau giải: True/False khi full puzzle có nghiệm duy nhất; trường hợp khác là `None` |
| `runtime` | Thời gian chạy tính bằng giây |

Mặc định duyệt đủ 512 hoặc 65.536 assignment. `stop_after_two=True` dừng khi gặp
nghiệm thứ hai: đủ chứng minh MULTIPLE nhưng số nghiệm chỉ là cận dưới nếu
`exhaustive=False`. Khi dừng ở assignment cuối thì số đếm và phân loại vẫn chính
xác. UNIQUE và UNSAT luôn cần duyệt hết. Không suy ra ô forced từ một phần nghiệm.

Trước khi duyệt, mỗi clue được evaluate riêng một lần trên assignment mẫu đầy đủ
để lộ lỗi evaluator hoặc kết quả không phải Boolean. Các lượt này không được
tính vào `assignments_checked`. Khi tìm nghiệm, dừng đánh giá assignment ngay khi
một clue sai. Lỗi evaluator được truyền ra, không biến thành UNSAT.

## Tính đúng đắn và độ phức tạp

Với v=N², Cartesian product của `(False, True)` lặp v lần sinh đúng 2^v tuple
khác nhau. Ánh xạ theo `board.all_cells(n)` là song ánh với assignment đầy đủ.
Một assignment được đếm khi và chỉ khi mọi public fact và mọi clue đều đúng.
Hai nghiệm chứng minh MULTIPLE; duyệt hết mới chứng minh được UNIQUE hoặc UNSAT.

Mỗi ô giữ hai bit ghi nhận đã xuất hiện False/True trong các nghiệm. Sau duyệt
hết, một giá trị duy nhất cho biết trạng thái forced; có cả hai thì UNKNOWN.
Không có model thì KB INCONSISTENT. Không lưu danh sách toàn bộ nghiệm.

Với m clue và chi phí c cho một lần evaluate, thời gian xấu nhất
O(2^v × (v + m×c)), bộ nhớ O(v + kích thước clue). Dừng đánh giá một assignment
không làm bỏ qua assignment khác. Chỉ dùng dừng sau hai nghiệm khi không cần số
đếm hay phân loại đầy đủ. 5×5 bị từ chối vì có 33.554.432 assignment; dùng công cụ
DPLL phù hợp cho ca stress.
