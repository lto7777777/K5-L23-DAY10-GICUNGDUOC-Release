# Dùng AI

Nhóm dùng AI để viết code và để soát lại lập luận. Phần xem ảnh ở Pha 2 do người trong nhóm
mở từng ảnh và kết luận; AI chỉ dựng công cụ cắt ảnh, vẽ box và viền segment.

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Minh | Claude | "Viết `validator/validate.py` bắt 9 loại lỗi luật của lô, chỉ thư viện chuẩn, chỉ đọc thư mục delivery" | Bản đầu ghép mỗi segment với box chứa nhiều pixel của nó nhất. Box to bao vật nhỏ cũng đạt contain 1.00, nên `tie` nằm trong box `person` bị báo là lệch lớp | Chạy trên lô sạch `runs/clean` (50 ảnh, không gài lỗi): ra 18 ứng viên sai. In bảng contain / cover / bbox IoU của từng cặp, thấy cả 18 ca đều có box cùng lớp khớp IoU 0,96–1,00. Đổi sang xếp hạng theo contain × bbox IoU rồi chạy lại: còn 0 ứng viên |
| 2 | Minh | Claude | "Cách phân biệt `bbox_drift` với vật bị che, chỉ dựa vào mask và box" | AI đề xuất lấy bbox IoU thấp làm dấu hiệu box lệch. Cách đó bắt nhầm ca cái giường bị che ở lô sạch: segment chỉ còn một mảnh nên IoU 0,10 dù box đúng | Đối chiếu trên lô sạch: vật bị che làm segment nhỏ đi nhưng pixel vẫn nằm trong box (contain 1.00), còn box lệch mới đẩy pixel ra ngoài. Chốt ngưỡng theo contain và bỏ điều kiện IoU |
| 3 | Minh | Claude | "Viết công cụ cắt ảnh quanh ứng viên, vẽ box detection và pixel segment để người xem" | Không sai, nhưng bản đầu chỉ xuất ảnh đã đánh dấu nên khó nhìn ra vật thật là gì | Thêm nửa ảnh gốc bên trái để so sánh; `tools/view_candidate.py` nay xuất ảnh đôi gốc / đã đánh dấu |
| 4 | Minh | Claude | "Ảnh này detection ghi laptop, panoptic ghi tv, bên nào đúng?" | AI trả lời được, nhưng nhóm không lấy câu trả lời của AI làm kết luận | Người trong nhóm mở ảnh, thấy màn hình rời đặt trên thùng máy và có bàn phím rời phía dưới nên kết luận `class_swap`, rồi ghi đúng điều nhìn thấy vào `review_log.csv`. Ảnh COCO là dữ liệu công khai nên được phép dán lên công cụ AI (RULES.md), với dữ liệu dự án thật thì không |
| 5 | Minh | Claude | "Vì sao `run_lab.py` dừng giữa chừng trên Windows?" | Đoán đầu tiên của AI là thiếu dữ liệu nguồn, sai | Đọc traceback thật: `UnicodeEncodeError` ở dòng `print` cuối của tiến trình con. Chạy lại với `PYTHONUTF8=1` thì qua, và lineage mới được ghi. Ghi vào `REPORT.md` mục 6 |

**Ca nhóm ít chắc chắn nhất.** `000000001818` (hai con ngựa vằn chồng nhau, chỉ còn một box zebra).
AI đề xuất `confirmed missing_box`; nhóm để `rejected` sau khi đo thấy box hiện có đã trùm 50% pixel
con còn lại và khớp khung tới IoU 0,72, và sau khi đọc `inject_release.py` thấy hàm `dedupe()` bỏ bớt
box cùng lớp có IoU > 0.7. Ca này được ghi rõ trong `REPORT.md` mục 6 vì nhóm có thể sai.
