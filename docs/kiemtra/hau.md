# Bộ test validator — Hậu

## Lệnh chạy

```powershell
python tests/test_validator.py
```

## Thử đột biến `BOX_TOL = 10`

Khi đổi `BOX_TOL` từ `0.01` thành `10`, kết quả chạy là:

```text
Ran 12 tests in 0.586s
FAILED (failures=1)
```

Trong đó, `test_bbox_out_of_bounds` thất bại. Test tạo một bounding box vượt ra ngoài phạm vi ảnh và mong validator trả về lỗi `bbox_out_of_bounds` cho ảnh `anh01`. Nhưng với `BOX_TOL = 10`, validator không trả về lỗi này, nên kết quả thực tế không khớp với điều test mong đợi. 11 test còn lại đạt.

Kết quả này cho thấy thay đổi ngưỡng `BOX_TOL` đã làm ảnh hưởng đến việc phát hiện bounding box vượt biên; test `test_bbox_out_of_bounds` bắt được thay đổi đó thay vì vẫn đạt như cũ.

## Chạy lại sau khi khôi phục giá trị

Sau khi trả `BOX_TOL` về `0.01`, chạy lại cùng lệnh:

```text
Ran 12 tests in 0.569s
OK
```

Cả 12 test đều đạt. Đây là kết quả chạy sau khi khôi phục `BOX_TOL` về giá trị ban đầu.

## Giới hạn

Bộ test này chỉ kiểm tra các lỗi theo luật validator; chưa kiểm tra phần đối chiếu detection với panoptic.
