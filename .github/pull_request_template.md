## Việc (ID trong Excel)
`[ID]` Tên việc:

## Làm gì
<!-- 2–4 gạch đầu dòng: đã thêm/sửa gì, vì sao -->
-

## Cách kiểm tra
<!-- Lệnh để người review chạy lại. Chạy trong thư mục Source/ -->
```bash
python -m unittest discover -s tests -t .
```
<!-- Thêm lệnh khác nếu có (python main.py, chạy puzzle nào...) -->

## Checklist (tác giả tick trước khi nhờ review)
- [ ] PR chỉ làm **một việc**, tiêu đề đúng dạng `[ID] Tên việc`
- [ ] Test **xanh** trên máy mình, có test mới cho logic mới
- [ ] Không còn `TODO(<ID>)` của việc này, không còn `print` gỡ lỗi, không có file rác
- [ ] Tuân thủ `docs/CODING_STANDARDS.md` (type hint, docstring, tên tiếng Anh)
- [ ] Không đổi "hợp đồng" (`docs/INTERFACES.md`) — hoặc đã được cả nhóm đồng ý (nêu rõ ở dưới)
- [ ] Đã `git merge origin/main` vào nhánh và chạy lại test
- [ ] Nếu dùng AI / nguồn ngoài: đã ghi `docs/AI_USAGE_LOG.md` / `docs/REFERENCES.md`
- [ ] Đã cập nhật trạng thái trong Excel thành **Chờ review**

## Ghi chú cho người review
<!-- Chỗ nào cần xem kỹ, chỗ nào chưa chắc, các quyết định thiết kế -->
