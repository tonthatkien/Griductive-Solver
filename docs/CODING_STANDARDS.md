# Quy ước viết code

Mục tiêu: code của 5 người đọc như của một người, dễ review, dễ giải thích khi vấn đáp.

> **Ba điều quan trọng nhất của dự án này**
> 1. **Agent chỉ thấy `PublicKB`**, không bao giờ đọc nhãn ẩn hay clue chưa lật.
> 2. **Tự cài đặt DPLL và CNF encoder**, không dùng thư viện SAT/logic có sẵn.
> 3. **Không viết tay CNF cho từng puzzle**: mọi clue đều được encode tự động.

## 1. Chung

- Python **3.10+**. Theo **PEP 8**; dòng **tối đa 100 ký tự**; thụt lề 4 dấu cách; file UTF-8.
- **Tên (biến, hàm, lớp, file) viết bằng tiếng Anh**: `snake_case` cho hàm/biến/file, `PascalCase` cho lớp,
  `UPPER_CASE` cho hằng số. Tên phải nói lên ý nghĩa (`num_aux_vars`, không phải `n2` hay `x`).
- **Comment và docstring** viết tiếng Việt hoặc tiếng Anh, nhưng trong **một file** dùng một ngôn ngữ cho nhất quán.
  Comment giải thích *vì sao*, không lặp lại *cái gì* mà code đã nói rõ.
- **Type hint** cho tham số và kết quả của mọi hàm công khai; **docstring** cho mọi lớp và hàm công khai
  (hàm nhỏ chỉ cần một dòng tóm tắt).
- Mỗi hàm làm một việc, **ngắn (< ~40 dòng)**. Dài hơn thì tách.
- Không để **code chết**, không comment-out cả khối code, không `print` gỡ lỗi sót lại (dùng `logging` hoặc xóa trước khi commit).
- Không dùng "số ma thuật": trạng thái dùng hằng số có tên (`CRIMINAL`, `INNOCENT`, `UNKNOWN`, `INCONSISTENT`),
  không rải chuỗi `"CRIMINAL"` khắp nơi và không dùng `0/1` thay cho trạng thái.
- Không dùng `from module import *`.
- Dùng `.editorconfig` (đã có ở gốc repo) để editor tự thụt lề đúng. Khuyến khích chạy `ruff check` hoặc `black` trước khi commit (không bắt buộc).

## 2. Kiến trúc: ai được gọi ai

```
main.py ──► gui/ ──► logic/agent.py ──► logic/cnf_encoder.py ──► logic/dpll.py
              │            │                     │
              │            └─ chỉ nhận PublicKB ─┘
              ▼
           engine/  (board.py, clue.py, game_state.py)

experiments/, tests/ ──► engine/, logic/   (không cần gui/)
```

| Module | Được import | KHÔNG được |
|---|---|---|
| `engine/` | chỉ `engine/` | import `logic/` hoặc `gui/` |
| `logic/` | `engine.board`, `engine.clue`, kiểu `PublicKB` | import `gui/`; đọc `GameEngine._solution`, `GameEngine._clues`, `Character.is_criminal` |
| `gui/` | `engine/`, `logic/agent` | chứa luật chơi hay logic suy luận |
| `experiments/`, `tests/` | mọi thứ (trừ `gui/` nếu không cần) | |

- `GameEngine` nói chuyện với agent qua đúng một đường: `get_public_kb()` và callback `classify_fn` trong `submit_verdict`.
- Ranh giới này phải **chứng minh được khi vấn đáp**: có test kiểm tra `PublicKB` không chứa dữ liệu ẩn (việc A6).

## 3. Quy ước cho `engine/`

- `Clue` và `PublicKB` nên **bất biến hoặc chỉ đọc** phía agent: agent không sửa `PublicKB`, `GameEngine` mới là nơi cập nhật.
- Nhãn Criminal/Innocent và clue chưa lật là **private** trong `GameEngine`. Không trả chúng ra qua bất kỳ getter nào
  mà agent/GUI gọi được trong lúc chơi (GUI chỉ cần hiển thị thẻ đã lật).
- `validate_clue` phải bắt: ô ngoài lưới, vùng rỗng, ô trùng trong `cells`, `k` ngoài `[0, |R|]`, kiểu clue lạ.
- `submit_verdict` không đổi state khi từ chối (`NOT_PROVABLE`, `CONTRADICTED`) và **không lộ clue** của thẻ đó.
- Sau mỗi verdict được chấp nhận, engine `assert` nó khớp nghiệm ẩn (để bắt bug của agent, không để lộ ra ngoài).
- Quy ước tọa độ: cell id `C2` = cột C, hàng 2; hàng đếm từ trên xuống; thứ tự duyệt luôn là **row-major** (`board.all_cells`).

## 4. Quy ước cho `logic/cnf_encoder.py` và `logic/semantic.py`

- Biểu diễn: literal là số nguyên khác 0, clause là `list[int]`, CNF là `list[list[int]]`.
  Biến primary = `board.var_of(cell, n)` (`1..N*N`); **biến phụ bắt đầu từ `N*N + 1`**, cấp qua `Encoder.new_aux()`.
- Encoding sinh clause theo **thứ tự xác định** (dùng `itertools.combinations` trên danh sách ô đã sắp row-major),
  để cùng một clue luôn ra cùng một CNF (dễ debug, dễ so số clause).
- Không có hàm nào chứa CNF viết tay cho puzzle cụ thể. Biên phải được xử lý: `k = 0`, `k = |R|`, `|R| = 1`, vùng 1 ô.
- `build_kb(public_kb)` chỉ dùng clue đã lật và verdict đã chứng minh. Báo `num_primary`, `num_aux`, số clause.
- `semantic.evaluate(...)` **không import và không gọi** `cnf_encoder`. Nó tính trực tiếp từ assignment đầy đủ.
  Hai module này kiểm chứng lẫn nhau, nên phải được viết độc lập (tốt nhất bởi hai người khác nhau, đúng như phân công).
- Extension (PARITY, COMPARE hoặc loại nhóm chọn): ghi rõ encoding đã dùng trong docstring (có/không dùng biến phụ, số clause sinh ra).

## 5. Quy ước cho `logic/dpll.py`

- Chữ ký cố định: `DPLLSolver().solve(clauses, num_vars, assumptions=(), timeout=None) -> SolveResult`.
- **Tự cài đặt**: unit propagation, phát hiện conflict, chọn biến, đệ quy + quay lui. Cấm `pysat`, `z3`, `sympy.logic.inference.satisfiable`...
- **Không sửa danh sách clause truyền vào** (assumptions xử lý như unit clause tạm thời trên bản sao hoặc trên bảng gán).
- Chọn biến **xác định** (không `random`, không phụ thuộc thứ tự `set`/`dict` không ổn định).
- Đếm đúng và nhất quán: `decisions` (mỗi lần chọn biến để rẽ nhánh), `propagations` (mỗi literal được suy ra từ unit clause),
  `backtracks` (mỗi lần quay lui sau conflict), `runtime` (`time.perf_counter`). Ghi định nghĩa này vào docstring để báo cáo dùng lại.
- SAT phải trả **model đầy đủ** (mọi biến `1..num_vars` có giá trị). UNSAT trả `model=None`.
- Có `timeout` để thực nghiệm ghi nhận TIMEOUT, không để chương trình treo.

## 6. Quy ước cho `logic/agent.py`

- Agent chỉ nhận `PublicKB`, không nhận `GameEngine`.
- `classify` gọi DPLL đúng theo định nghĩa: `KB ∧ ¬Ci` UNSAT ⇒ `CRIMINAL`; `KB ∧ Ci` UNSAT ⇒ `INNOCENT`;
  cả hai SAT ⇒ `UNKNOWN`; bản thân `KB` UNSAT ⇒ `INCONSISTENT`.
- **Không bao giờ đoán.** Không có nhánh "chọn bừa" khi `UNKNOWN`; hết ô forced thì dừng ở trạng thái STUCK.
- Chọn ô tiếp theo **xác định** (row-major trong các ô forced).
- `auto_solve` trả về **trace**: step, clue đang active, các SAT query và kết quả, verdict, clue mới lộ.
- `uniqueness_check` dùng toàn bộ clue của puzzle nên **chỉ dành cho công cụ/kiểm tra puzzle**, không được gọi trong lúc agent chơi.

## 7. Quy ước cho `gui/`

- Tách **vẽ** (render), **xử lý sự kiện** và **logic**. Không viết một hàm 300 dòng.
- GUI **không chứa luật chơi hay suy luận**; mọi kiểm tra verdict đi qua `GameEngine.submit_verdict`.
- Không đứng hình khi Auto Solve: chạy từng bước theo timer hoặc luồng riêng, có nút Pause/Step.
- Màu, kích thước ô, phím tắt đặt thành hằng số ở đầu file hoặc file `settings`.
- Hiển thị rõ `NOT_PROVABLE` và `CONTRADICTED` (hai thông báo khác nhau) và **không lật thẻ** khi bị từ chối.

## 8. Quy ước cho `data/` (puzzle)

- Tên file: `p01.json`, `p02.json`... trong `puzzles_3x3/`, `puzzles_4x4/`, `puzzles_5x5/`.
- Mỗi puzzle phải có **đúng một nghiệm** (đề yêu cầu). Chỉ merge puzzle khi đã kiểm bằng brute force (3×3, 4×4) và/hoặc `uniqueness_check`.
- Puzzle cố ý lỗi (mơ hồ, mâu thuẫn) để demo thì đặt trong thư mục con hoặc tên có tiền tố `bad_`, để script thực nghiệm chính không lẫn vào.

## 9. Test

- Thư mục `tests/`, file `test_*.py`, dùng `unittest`. Tên test mô tả hành vi: `test_exactly_zero_forces_all_innocent`.
- Mỗi test kiểm **một ý**. Dữ liệu test nhỏ, dựng ngay trong test hoặc dùng file trong `data/`.
- Chạy: `python -m unittest discover -s tests -t .` (trong thư mục `Source/`).
- Danh sách test bắt buộc xem `CONTRIBUTING.md`, mục 6.

## 10. Hiệu năng (vì có đo thời gian và số clause)

- Encoding **combinatorial trực tiếp** sinh `C(m, k+1)` clause cho `AT_MOST` và `C(m, m-k+1)` cho `AT_LEAST`.
  Với vùng nhỏ của đề (tối đa 8 ô láng giềng, 5 ô hàng/cột) là chấp nhận được; vùng `cells` dài thì cân nhắc và ghi vào báo cáo.
- Tính trước những thứ không đổi (ví dụ danh sách ô của vùng) thay vì tính lại trong mỗi lần gọi DPLL.
- Tối ưu có đo đạc (ghi trước/sau), không đoán mò.
- Mọi so sánh trong thực nghiệm dùng **cùng bộ puzzle**; ghi cả timeout/failure, không loại khỏi bảng.

## 11. File và cấu trúc

- Một file một trách nhiệm; file > ~400 dòng thì cân nhắc tách.
- Không sửa file thuộc phần của người khác khi chưa báo (xem `docs/REVIEW_ASSIGNMENTS.md`). Cần sửa nhỏ thì nhắn họ hoặc để họ review.
- Đường dẫn dùng `pathlib` / đường dẫn tương đối từ `Source/`, không hardcode `C:\Users\...`.
- Ngẫu nhiên (nếu có, ví dụ test DPLL với random CNF): luôn đặt **seed** để kết quả lặp lại được.
