# Hợp đồng giao tiếp giữa các module (CẢ NHÓM ĐỌC TRƯỚC KHI CODE)

## 1. Quy ước chung

- **Cell ID:** `<cột><hàng>`, ví dụ `C2` (cột C, hàng 2). Hàng đếm từ trên xuống.
- **Biến SAT primary:** `board.var_of(cell, n)` = index row-major + 1 (1..N*N).
- **Biến phụ:** Bắt đầu từ `N*N+1`.
- **True:** Criminal.
- **False:** Innocent.
- **CNF:** `list[list[int]]` (literal âm = phủ định).
- **Verdict string:** `CRIMINAL`, `INNOCENT`, `UNKNOWN`, `INCONSISTENT`.
- **Kết quả submit:** `ACCEPTED`, `NOT_PROVABLE`, `CONTRADICTED`.

## 2. Format file puzzle (JSON)

Ví dụ dưới đây **đã rút gọn** (chỉ 1 character, chỉ để minh họa cú pháp, **không phải puzzle hợp lệ**). Puzzle đầy đủ xem `data/puzzles_3x3/p01.json`.

```json
{
  "n": 3,
  "characters": [
    {
      "cell": "A1",
      "name": "Abel",
      "profession": "Astronaut",
      "criminal": false,
      "clue": {
        "type": "EXACTLY",
        "region": {
          "type": "neighbors",
          "cell": "A1"
        },
        "k": 1,
        "status": "CRIMINAL"
      }
    }
  ],
  "initially_revealed": ["B2"]
}
```

- Mỗi nhân vật có đúng **1 clue** (lộ ra khi thẻ được lật).
- `criminal` là nhãn **ẨN**, chỉ `GameEngine` được đọc.
- Mỗi puzzle **PHẢI có nghiệm duy nhất** (kiểm tra bằng `uniqueness_check` trước khi đưa vào `data/`).
- Tên khóa tham chiếu ô khác nhau theo từng loại clue (`target`, `cell1`/`cell2`, `cell`); mỗi loại được định nghĩa cố định ở mục 2.2, không tự đặt tên khác.

### 2.1. Cú pháp 4 loại Region (Vùng)

Tham số `region` trong các clue đếm số lượng phải tuân theo một trong 4 format sau:

**1. Hàng (Row)**

```json
{
  "type": "row",
  "number": 1
}
```

`number`: int, đánh số từ 1.

**2. Cột (Col)**

```json
{
  "type": "col",
  "letter": "B"
}
```

`letter`: string, chữ cái **viết hoa**.

**3. Xung quanh (Neighbors)**

```json
{
  "type": "neighbors",
  "cell": "A1"
}
```

`cell`: string. Gồm tối đa 8 ô kề (kể cả chéo), **không** gồm chính ô `cell`.

**4. Danh sách chọn (List)**

```json
{
  "type": "list",
  "cells": ["A1", "B2", "C3"]
}
```

`cells`: list[string], các ô không trùng nhau.

### 2.2. Cú pháp 8 loại Clue (6 core + 2 extension)

**1. FACT**

```json
{
  "type": "FACT",
  "target": "C3",
  "status": "INNOCENT"
}
```

**2. SAME_STATUS**

```json
{
  "type": "SAME_STATUS",
  "cell1": "A1",
  "cell2": "B2"
}
```

**3. DIFFERENT_STATUS**

```json
{
  "type": "DIFFERENT_STATUS",
  "cell1": "A1",
  "cell2": "B2"
}
```

**4. EXACTLY**

```json
{
  "type": "EXACTLY",
  "region": {
    "type": "row",
    "number": 1
  },
  "k": 1,
  "status": "CRIMINAL"
}
```

**5. AT_LEAST**

```json
{
  "type": "AT_LEAST",
  "region": {
    "type": "row",
    "number": 1
  },
  "k": 1,
  "status": "CRIMINAL"
}
```

**6. AT_MOST**

```json
{
  "type": "AT_MOST",
  "region": {
    "type": "row",
    "number": 1
  },
  "k": 2,
  "status": "CRIMINAL"
}
```

**7. PARITY (Extension Clue)**

Kiểm tra tính chẵn/lẻ. `parity` nhận một trong hai giá trị `EVEN` hoặc `ODD`.

```json
{
  "type": "PARITY",
  "parity": "EVEN",
  "region": {
    "type": "neighbors",
    "cell": "A1"
  },
  "status": "CRIMINAL"
}
```

**8. COMPARE (Extension Clue)**

So sánh số lượng giữa hai vùng. `op` nhận một trong năm giá trị:

| `op` | Ý nghĩa |
|---|---|
| `GT` | `region1` > `region2` |
| `GE` | `region1` >= `region2` |
| `EQ` | `region1` = `region2` |
| `LE` | `region1` <= `region2` |
| `LT` | `region1` < `region2` |

```json
{
  "type": "COMPARE",
  "region1": {
    "type": "row",
    "number": 1
  },
  "op": "GT",
  "region2": {
    "type": "col",
    "letter": "B"
  },
  "status": "CRIMINAL"
}
```

### 2.3. Ngữ nghĩa Clue

Mọi clue đều **đúng** (là sự thật về lưới) khi được lật. Các quy ước chung:

- `status` ∈ {`CRIMINAL`, `INNOCENT`}. Nếu bỏ qua thì **mặc định `CRIMINAL`**.
- Một ô "có trạng thái `status`" nghĩa là: `True` nếu `status = CRIMINAL`, `False` nếu `status = INNOCENT`.

| Clue | Điều kiện đúng |
|---|---|
| `FACT` | `target` có trạng thái `status` |
| `SAME_STATUS` | `cell1` và `cell2` cùng trạng thái (cùng True hoặc cùng False) |
| `DIFFERENT_STATUS` | `cell1` và `cell2` khác trạng thái |
| `EXACTLY` | số ô trong `region` có trạng thái `status` **= k** |
| `AT_LEAST` | số ô trong `region` có trạng thái `status` **>= k** |
| `AT_MOST` | số ô trong `region` có trạng thái `status` **<= k** |
| `PARITY` | số ô trong `region` có trạng thái `status` là chẵn (`EVEN`) hoặc lẻ (`ODD`) |
| `COMPARE` | đếm số ô có trạng thái `status` ở **cả `region1` và `region2`**, rồi so sánh `count(region1) op count(region2)` |

Hệ quả cho từng module:

- **Encoder (`cnf_encoder`):** khi `status = INNOCENT`, đảo cực literal của các ô trong vùng (đếm literal âm thay vì dương).
- **Semantic (`semantic.evaluate`):** khi `status = INNOCENT`, đếm các ô có giá trị `False` trong `assignment`.
- `FACT`, `SAME_STATUS`, `DIFFERENT_STATUS` không có `k` và không có `region`.

`initially_revealed`: các ô này công khai **cả trạng thái thật lẫn clue** ngay từ đầu, nên được đưa vào `proved` và `revealed_clues` của `PublicKB` ngay khi load puzzle.

### 2.4. Quy tắc hợp lệ của file puzzle

`validate_clue` và loader phải kiểm tra:

1. Có đúng N×N character; mỗi `cell` nằm trong lưới và **không trùng**.
2. Tên character xếp theo **alphabet theo thứ tự row-major** (A1, B1, C1, A2, ...).
3. `initially_revealed` **không rỗng**, không trùng, và mọi phần tử là cell hợp lệ.
4. `0 <= k <= |R|` với `|R|` là số ô của vùng (và `k` là int).
5. `status` ∈ {`CRIMINAL`, `INNOCENT`}; `parity` ∈ {`EVEN`, `ODD`}; `op` ∈ {`GT`, `GE`, `EQ`, `LE`, `LT`}.
6. `letter` viết hoa; `number` >= 1; các `cells` trong region `list` không trùng nhau.
7. Mọi cell được tham chiếu trong clue (`target`, `cell1`, `cell2`, `region.cell`, `region.cells`) nằm trong lưới.
8. Puzzle có **nghiệm duy nhất** (`uniqueness_check`).

## 3. Ranh giới Engine / Agent

```text
GameEngine --get_public_kb()--> PublicKB --> Encoder.build_kb --> DPLL
  ^                                                  |
  +---- submit_verdict(cell, verdict, classify) <----+
                       (classify = LogicAgent.classify)
```

- Agent chỉ thấy `PublicKB(n, revealed_clues, proved)`.
- `classify` là callback; engine tự quyết định kết quả:
  - `ACCEPTED`
  - `NOT_PROVABLE`
  - `CONTRADICTED`

## 4. Chữ ký hàm chính (đừng đổi nếu chưa báo nhóm)

| Module | Chữ ký hàm | Mô tả kết quả |
|---|---|---|
| `engine.clue` | `resolve_region(region, n) -> list[str]` | Chuyển region thành danh sách cell |
| `engine.clue` | `clue_cells(clue, n) -> list[str]` | Lấy danh sách cell liên quan đến clue |
| `logic.cnf_encoder` | `Encoder(n).build_kb(public_kb) -> KB(clauses, num_primary, num_aux)` | Chuyển PublicKB thành KB dạng CNF |
| `logic.semantic` | `evaluate(clue, assignment, n) -> bool` | Đánh giá clue theo assignment |
| `logic.dpll` | `DPLLSolver().solve(clauses, num_vars, assumptions=(), timeout=None) -> SolveResult` | Giải bài toán SAT |
| `logic.agent` | `LogicAgent().classify(public_kb, cell) -> str` | Phân loại trạng thái nhân vật |
| `logic.agent` | `LogicAgent().auto_solve(engine) -> list[TraceEntry]` | Tự động giải puzzle |
| `logic.agent` | `uniqueness_check(all_clues, n)` | Kiểm tra puzzle có nghiệm duy nhất |