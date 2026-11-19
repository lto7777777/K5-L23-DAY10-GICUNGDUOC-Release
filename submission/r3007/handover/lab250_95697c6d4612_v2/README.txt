Release: lab250_95697c6d4612_v2
Parent: lab250_95697c6d4612
Số ảnh: 241
Số nhãn: 1647
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: 19/250 = 7,6%
Kết luận v1: Hold — 7,6% ảnh lỗi, trên ngưỡng 2% của Day 7 nên không phát hành cho train
Kết luận v2: Release — đã tách 9 ảnh lỗi nhãn detection sang rework_queue, 241 ảnh còn lại giữ nguyên nhãn, có manifest + sha256 và truy vết theo job
Ghi chú: split: cảnh scene_214 bị rò train/val, đã đưa cả cảnh về một split trong truyvet.csv (1 ảnh đổi split, nhãn không đổi). hash: 000000006723, 000000020247 có sha256 trong manifest.json v1 không khớp file; đã mở ảnh kiểm, ảnh còn nguyên và đúng nội dung nên chỉ ghi lại hash thật trong manifest.csv của v2, không đưa vào rework. guideline: 000000002157, 000000003553 ghi khác job của nó, truyvet.csv lấy guideline theo job trong jobs.csv. rework: 9 ảnh tách khỏi v2, giao lại cho A02/Q01, A03/Q01, A04/Q01, A04/Q02, A05/Q01, A05/Q03 (người gán/người kiểm theo job). panoptic: 000000013291, 000000013659, 000000019742, 000000022192, 000000023781 chỉ sai ở mask nên nhãn detection vẫn dùng được, ảnh ở lại v2; đề nghị team panoptic sửa mask rồi phát hành lại phần panoptic.
