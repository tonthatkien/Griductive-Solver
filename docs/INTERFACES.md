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

`letter`: string.

**3. Xung quanh (Neighbors)**

```json
{
  "type": "neighbors",
  "cell": "A1"
}
```

`cell`: string.

**4. Danh sách chọn (List)**

```json
{
  "type": "list",
  "cells": ["A1", "B2", "C3"]
}
```

`cells`: list[string].

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

So sánh số lượng giữa hai vùng. `op` nhận một trong ba giá trị `>`, `<` hoặc `=`.

```json
{
  "type": "COMPARE",
  "region1": {
    "type": "row",
    "number": 1
  },
  "op": ">",
  "region2": {
    "type": "col",
    "letter": "B"
  },
  "status": "CRIMINAL"
}
```

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
| `logic.dpll` | `DPLLSolver().solve(clauses, num_vars, assumptions=()) -> SolveResult` | Giải bài toán SAT |
| `logic.agent` | `LogicAgent().classify(public_kb, cell) -> str` | Phân loại trạng thái nhân vật |
| `logic.agent` | `LogicAgent().auto_solve(engine) -> list[TraceEntry]` | Tự động giải puzzle |