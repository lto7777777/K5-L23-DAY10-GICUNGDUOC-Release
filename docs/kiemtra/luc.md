# Kiểm truy vết — Lực

Lệnh: python tools/check_trace.py --run runs/r3007

``lớp đổi quy tắc: bottle (v1.2 -> v1.3)
cảnh ticket nêu: scene_197, scene_309
job theo guideline cũ: J01, J02, J03, J04
  [PASS] tier_a  2 mục
  [PASS] tier_b  4 mục
  [PASS] notify  5 mục
=> trace.json khớp dữ liệu lô.``

Thử file sai: bớt một ảnh trong tier_a và thêm A99 vào notify thì công cụ báo 2 dòng FAIL,
nêu đúng tên ảnh thiếu và người thừa, nghĩa là nó có kiểm thật.

Tiêu chí: lấy guideline theo job trong jobs.csv, không theo guideline_version ghi ở từng ảnh.