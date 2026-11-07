# Hợp đồng giao tiếp giữa các module (CẢ NHÓM ĐỌC TRƯỚC KHI CODE)

## 1. Quy ước chung
- Cell id: `<cột><hàng>`, ví dụ `C2` (cột C, hàng 2). Hàng đếm từ trên xuống.
- Biến SAT primary: `board.var_of(cell, n)` = index row-major + 1 (1..N*N). Biến phụ: từ N*N+1.
- True = Criminal, False = Innocent.
- CNF = `list[list[int]]` (literal âm = phủ định).
- Verdict string: `CRIMINAL`, `INNOCENT`, `UNKNOWN`, `INCONSISTENT`.
- Kết quả submit: `ACCEPTED`, `NOT_PROVABLE`, `CONTRADICTED`.

## 2. Format file puzzle (JSON)
```json
{
  "n": 3,
  "characters": [
    {"cell": "A1", "name": "Abel", "profession": "Astronaut", "criminal": false,
     "clue": {"type": "EXACTLY", "region": {"type": "neighbors", "cell": "A1"}, "k": 1}}
  ],
  "initially_revealed": ["B2"]
}
```
- Mỗi nhân vật có đúng 1 clue (lộ ra khi thẻ được lật).
- `criminal` là nhãn ẨN, chỉ GameEngine được đọc.
- Chi tiết các loại clue/region: xem docstring `engine/clue.py`.
- Mỗi puzzle PHẢI có nghiệm duy nhất (kiểm tra bằng `uniqueness_check` trước khi đưa vào data/).

## 3. Ranh giới Engine / Agent
```
GameEngine --get_public_kb()--> PublicKB --> Encoder.build_kb --> DPLL
   ^                                                 |
   +---- submit_verdict(cell, verdict, classify) <---+   (classify = LogicAgent.classify)
```
- Agent chỉ thấy `PublicKB(n, revealed_clues, proved)`.
- `classify` là callback; engine tự quyết định ACCEPTED / NOT_PROVABLE / CONTRADICTED.

## 4. Chữ ký hàm chính (đừng đổi nếu chưa báo nhóm)
- `engine.clue.resolve_region(region, n) -> list[str]`
- `engine.clue.clue_cells(clue, n) -> list[str]`
- `logic.cnf_encoder.Encoder(n).build_kb(public_kb) -> KB(clauses, num_primary, num_aux)`
- `logic.semantic.evaluate(clue, assignment, n) -> bool`
- `logic.dpll.DPLLSolver().solve(clauses, num_vars, assumptions=()) -> SolveResult`
- `logic.agent.LogicAgent().classify(public_kb, cell) -> str`
- `logic.agent.LogicAgent().auto_solve(engine) -> list[TraceEntry]`
