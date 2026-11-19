# Kết quả 5 mã đề ẩn

Nhóm reviewer chạy bài trên 5 lô đề ẩn (01, 02, 03, 04, 05) để dựng bài mẫu. Mỗi lô là một đề riêng:
lớp bị đổi quy tắc khác nhau, cảnh team AI nêu khác nhau, số lỗi gài khác nhau.

Lô đề ẩn không kèm `_private`, nên không tự chấm được: không có F1 cho phần này, chỉ có kết quả chạy
và kết luận sau khi xem ảnh.

| Lô | Release | Lỗi luật | Ứng viên | Confirmed | `errors.json` | tier_a / tier_b / notify |
|---|---|---:|---:|---:|---:|---|
| 01 | `lab250_48ae39e45901` | 10 | 22 | 7 | 17 | 2 / 5 / 5 |
| 02 | `lab250_262995d8ee10` | 10 | 17 | 8 | 18 | 2 / 4 / 3 |
| 03 | `lab250_b2eb0db92936` | 11 | 15 | 8 | 19 | 3 / 3 / 5 |
| 04 | `lab250_8306733d9189` | 11 | 16 | 8 | 19 | 3 / 5 / 6 |
| 05 | `lab250_58c8a9125ce0` | 8 | 8 | 4 | 12 | 2 / 4 / 5 |

78 ứng viên được mở ảnh xem, chốt 35 confirmed và 43 rejected. `check_trace.py` PASS cả 5 lô. Bài của
từng lô nằm ở `submission/de_an/` (lô 03) và `submission/de_an_01`, `_02`, `_04`, `_05`.

## Cách phân biệt instance_merge thật với chồng lấn tự nhiên

Đây là thứ rút ra được nhờ làm nhiều lô, và nó đổi hẳn cách đọc hàng đợi.

Một ứng viên `instance_merge` chỉ đáng tin khi có đủ hai dấu hiệu:

1. Số segment của lớp đó ít hơn số box đúng một đơn vị. Gộp hai vật thành một segment thì
   `segments_info` mất đi một mục, còn số box giữ nguyên.
2. Hai box mà segment phủ lên gần như không chồng nhau, IoU giữa hai box xấp xỉ 0. Hai box chồng nhau
   nhiều là một vật bị khoanh hai lần chứ không phải hai vật bị gộp.

Thiếu một trong hai thì gần như chắc chắn là lệch tự nhiên. Đếm riêng số box và số segment không đủ:
cảnh đông vật thường có nhiều segment hơn box, và hai box chồng nhau 0,4-0,6 trên cùng một con vật là
chuyện bình thường của COCO.

Năm ca gộp thật bắt được bằng tiêu chí này, ca nào cũng là hai vật tách hẳn nhau:

| Lô | Ảnh | Vật bị gộp |
|---|---|---|
| 02 | `img_0193` | hai con ngựa đi trên đường, IoU giữa hai box bằng 0 |
| 03 | `img_0061` | xe SUV mép phải và xe bán tải mép trái |
| 04 | `img_0009` | hai người nằm ngủ trên cùng một giường |
| 04 | `img_0108` | hai người lướt sóng đứng cách nhau trên bãi biển |
| 05 | `img_0050` | hai nhánh bông cải ở hai góc đối diện của tô mì |

## Validator xếp sai loại hai lần

Trên `03/img_0061` validator xếp `bbox_drift`, trên `04/img_0108` xếp `missing_box`, nhưng mở ảnh ra
thì cả hai đều là `instance_merge`. Nguyên nhân giống nhau: ngưỡng `MERGE_CONT = 0.25` đòi mỗi box
phải ôm được một phần tư số pixel của segment, mà khi một trong hai vật bị gộp nhỏ hơn hẳn thì box của
nó chỉ ôm khoảng 10% và nhánh kiểm gộp không chạy.

Chưa sửa ngưỡng này, vì sửa validator sau khi đã chạy xong 5 lô thì mọi con số ở bảng trên không còn
tái lập được. Nếu sửa, hướng đúng là xét thêm điều kiện số segment ít hơn số box thay vì chỉ hạ
`MERGE_CONT`, kẻo hàng đợi phình ra toàn ứng viên giả.

## Ba ca người kiểm sửa lại kết luận của công cụ

`03/img_0217`: detection ghi `orange` cho đĩa lát táo. `03/img_0124`: detection ghi `kite` cho con
mòng biển đang bay. Cả hai đều do người xem ảnh chốt, công cụ chỉ đưa ra ứng viên kèm hai khả năng
`class_swap` và `category_swap`.

`01/img_0056` thì ngược lại: công cụ báo `bbox_drift`, người xem ảnh bác bỏ. Cabin xanh lớn được cả
hai nguồn ghi là `bus`, box và segment trùng nhau IoU 1,00, nên không có bất đồng nào để báo; vật bị
đánh dấu thật ra là chiếc xe nhỏ bị cắt ở mép trái khung hình. Báo ca này chỉ làm tụt precision.
