# Hướng dẫn Git từng bước

Dành cho cả nhóm (kể cả người mới dùng Git). Làm đúng thứ tự là không sợ hỏng `main`.

> **Nhớ 3 điều:** (1) luôn làm trên **nhánh riêng**; (2) **pull trước khi bắt đầu**, **merge `main` vào nhánh trước khi mở PR**;
> (3) lỡ tay thì **đừng hoảng, đừng `--force`**, nhắn nhóm.

## Mục lục
1. [Cài đặt lần đầu](#1-cài-đặt-lần-đầu)
2. [Bắt đầu một việc](#2-bắt-đầu-một-việc)
3. [Commit](#3-commit)
4. [Push và mở Pull Request](#4-push-và-mở-pull-request)
5. [Cập nhật `main` vào nhánh của mình](#5-cập-nhật-main-vào-nhánh-của-mình)
6. [Giải quyết conflict](#6-giải-quyết-conflict)
7. [Sửa theo review](#7-sửa-theo-review)
8. [Sau khi merge](#8-sau-khi-merge)
9. [Lỡ tay thì làm sao](#9-lỡ-tay-thì-làm-sao)
10. [Lệnh cấm](#10-lệnh-cấm)

---

## 1. Cài đặt lần đầu

```bash
git config --global user.name  "Tên của bạn"
git config --global user.email "email-dung-cho-github@example.com"

git clone <link-repo>
cd <thư-mục-repo>
cd MSSV1_MSSV2_MSSV3_MSSV4/Source          # thư mục chứa code (đổi tên theo MSSV thật)
python -m venv venv
source venv/bin/activate                    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -t .   # phải xanh ngay từ đầu
```

## 2. Bắt đầu một việc

```bash
git checkout main
git pull                                    # lấy bản mới nhất
git checkout -b feature/duy-C3              # feature/<tên>-<ID việc>
```

Nhớ đổi trạng thái việc trong Excel thành **Đang làm**.

## 3. Commit

```bash
git status                                  # xem mình đã sửa gì
git add logic/cnf_encoder.py tests/test_encoder_vs_semantic.py
git commit -m "[C3] Add AT_MOST combinatorial encoding"
```

- Chỉ `git add` đúng file mình sửa (tránh `git add .` khi chưa kiểm tra `git status`, dễ dính file rác).
- Commit **nhỏ, một ý một commit**. Message theo dạng `[ID] Động từ + nội dung`.
- Chạy test trước khi commit: `python -m unittest discover -s tests -t .`

## 4. Push và mở Pull Request

```bash
git push -u origin feature/duy-C3           # lần đầu; các lần sau chỉ cần: git push
```

Sau đó vào GitHub, bấm **Compare & pull request**:
- Tiêu đề: `[C3] Encode EXACTLY / AT_LEAST / AT_MOST`
- Điền mẫu PR, chọn **Reviewer** đúng người trong cột *Reviewer 1* của Excel.
- Nhắn người review trong nhóm chat, đổi trạng thái việc thành **Chờ review**.

## 5. Cập nhật `main` vào nhánh của mình

Làm **trước khi mở PR** và bất cứ khi nào `main` có thay đổi mà bạn cần:

```bash
git fetch origin
git merge origin/main
python -m unittest discover -s tests -t .   # chạy lại test sau khi merge
```

## 6. Giải quyết conflict

Conflict xảy ra khi hai người cùng sửa một chỗ. Git sẽ báo `CONFLICT` và đánh dấu trong file:

```
<<<<<<< HEAD
code của bạn
=======
code của người khác (từ main)
>>>>>>> origin/main
```

Cách xử lý:

1. Mở file, **đọc cả hai phía**, quyết định giữ gì (có thể giữ cả hai). Xóa ba dòng đánh dấu `<<<<<<<`, `=======`, `>>>>>>>`.
2. Không hiểu phần của người kia → **gọi người vừa sửa file đó** (xem `git log -- <file>`), đừng đoán.
3. Chạy lại test cho xanh.
4. Hoàn tất:
   ```bash
   git add <file-đã-sửa>
   git commit                                # để nguyên message merge Git gợi ý
   git push
   ```
5. Muốn hủy cuộc merge để làm lại: `git merge --abort`.

> Hay conflict ở các file dùng chung (`engine/clue.py`, `logic/agent.py`, `docs/INTERFACES.md`).
> Trước khi sửa các file này, **nhắn nhóm** để tránh hai người sửa cùng lúc.

## 7. Sửa theo review

```bash
git checkout feature/duy-C3
# sửa code theo nhận xét
git add <file>
git commit -m "[C3] Fix edge case k = |R| per review"
git push                                    # PR tự cập nhật
```

Trả lời từng nhận xét trên GitHub (đã sửa ở commit nào, hoặc vì sao không sửa), rồi báo người review.

## 8. Sau khi merge

```bash
git checkout main
git pull
git branch -d feature/duy-C3                # xóa nhánh local (GitHub xóa nhánh remote khi merge)
```

Đổi trạng thái việc thành **Hoàn thành** trong Excel.

## 9. Lỡ tay thì làm sao

| Tình huống | Cách xử lý |
|---|---|
| Sửa file sai, chưa commit, muốn bỏ | `git restore <file>` |
| Commit nhầm message, chưa push | `git commit --amend -m "[ID] message đúng"` |
| Commit nhầm vào `main` local, chưa push | `git branch feature/ten-ID` (giữ lại công việc) rồi `git reset --hard origin/main` |
| Đang làm dở mà cần chuyển nhánh | `git stash` ... `git stash pop` |
| Đã push một commit sai lên nhánh của mình | Sửa rồi commit thêm; **không** rewrite lịch sử |
| `main` bị hỏng sau khi merge | Báo nhóm ngay; người merge chạy `git revert <commit>` rồi mở PR |
| Lỡ commit file rác / bí mật | Báo nhóm trước khi làm gì tiếp (bí mật đã push cần đổi key/token) |

## 10. Lệnh cấm

- `git push --force` (đặc biệt lên `main`)
- Xóa nhánh của người khác
- `git reset --hard` / `git rebase` trên nhánh đã push, khi chưa hiểu rõ hậu quả
- Commit trực tiếp vào `main`
