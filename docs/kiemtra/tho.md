# Kiểm tra máy — Nguyễn Văn Thọ

Lệnh:

```text
py -3 -X utf8 tools/run_checks.py runs/clean runs/r3007 runs/r4242 --chi-tiet
```

Máy in ra:

```text
lô                   ảnh  lỗi luật  ứng viên    giây
----------------------------------------------------
clean                 50         0         0     3.6
r3007                250        11        13    17.3
r4242                250        13        11    14.1

clean

r3007
  luật      bbox_out_of_bounds    1
  luật      duplicate_box         2
  luật      guideline_mismatch    2
  luật      invalid_class         1
  luật      scene_leak            1
  luật      thing_overlap         2
  luật      wrong_hash            2
  ứng viên  bbox_drift            1
  ứng viên  class_swap            4
  ứng viên  instance_merge        4
  ứng viên  missing_box           4

r4242
  luật      bbox_out_of_bounds    2
  luật      duplicate_box         1
  luật      guideline_mismatch    2
  luật      invalid_category_id   1
  luật      invalid_class         2
  luật      missing_image         2
  luật      scene_leak            1
  luật      thing_overlap         1
  luật      wrong_hash            1
  ứng viên  bbox_drift            2
  ứng viên  class_swap            3
  ứng viên  instance_merge        3
  ứng viên  missing_box           3

Lô sạch clean: 0 lỗi luật (ĐẠT: lô sạch phải ra 0), 0 ứng viên là nhiễu tự nhiên.
```

Ba lô ra đúng số Minh đã đo: clean 0/0, r3007 11/13, r4242 13/11. Lô sạch ra 0 lỗi luật, nên validator không báo thừa trên luật. Lô có lỗi gài chỉ cho biết máy có bắt được một số lỗi; lô sạch mới cho biết những gì bắt được không phải do validator tự bịa.
