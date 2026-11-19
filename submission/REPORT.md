# Báo cáo nhóm GICUNGDUOC

Seed luyện tập: **3007**. Lô v1: `lab250_95697c6d4612` (250 ảnh). Mọi số dưới đây lấy từ file thật
trong `runs/r3007/`, đo bằng `scripts/score_findings.py` (chế độ học viên, chỉ in F1 làm tròn).

## 1. Số liệu luyện tập

| Lô | Lỗi luật | Ứng viên | F1 lỗi luật | F1 lỗi gán nhãn | F1 tổng |
|---|---:|---:|---:|---:|---:|
| `runs/clean` (50 ảnh, `--no-faults`) | 0 | 0 | không có lỗi để bắt | | |
| `runs/r3007` (250 ảnh, seed luyện tập) | 11 | 13 | 1.0 | 0.9 | 0.9 |
| `runs/r4242` (250 ảnh, seed thử thêm) | 13 | 11 | 1.0 | chưa review | 0.8 |

Hàng đợi xem ảnh trên seed luyện tập: 13 ảnh. Sau khi xem, 8 ứng viên được `confirmed`, 5 bị
`rejected`; danh sách nộp cuối cùng là 11 lỗi luật + 8 lỗi gán nhãn = 19 lỗi.

**Ngưỡng đã chọn và cách chọn.** Nhóm đo trên lô sạch trước, không đụng `_private`. Bản ghép đầu tiên
chọn box chứa nhiều pixel segment nhất, và trên 50 ảnh sạch nó đẻ ra 18 ứng viên lệch lớp, quy ra
250 ảnh là khoảng 90 ứng viên, nhiều hơn số lỗi thật cả chục lần. Đọc bảng đo thì thấy cả 18 ca đều có
một box cùng lớp khớp gần như hoàn hảo (contain 1.00, bbox IoU 0.96–1.00), còn box bị chấm sai là
một box to bao bên ngoài: `tie` nằm trong box `person`, `keyboard` nằm trong box `laptop`, `bowl` nằm
trong box `dining table`. Nguyên nhân là ghép chỉ theo số pixel chứa được: box to bao trọn vật nhỏ cũng
đạt contain 1.00.

Nhóm sửa cách ghép thay vì nới ngưỡng: xếp hạng cặp theo contain × bbox IoU, và chỉ coi là lệch lớp
khi vật không có box nào cùng lớp chứa từ 50% pixel của nó. Các ngưỡng cuối cùng (`validator/validate.py`):

| Ngưỡng | Giá trị | Vì sao |
|---|---:|---|
| `MISS_CONT` | 0.50 | box cùng lớp phải ôm được quá nửa pixel của vật mới tính là "vật này đã có box" |
| `SWAP_CONT` / `SWAP_IOU` | 0.85 / 0.45 | box khác lớp phải vừa trùm gần hết pixel vừa khớp khung thì mới là cùng một vật bị ghi lệch lớp |
| `DRIFT_CONT` | 0.92 | box để trên 8% pixel của vật rơi ra ngoài; vật bị che chỉ làm segment nhỏ đi chứ không đẩy pixel ra ngoài box, nên ngưỡng này không bắt nhầm ca bị che |
| `MIN_SEG_PX` / `MIN_SEG_FRAC` | 600 px / 0.3% | dưới mức đó segment quá nhỏ để kết luận bằng mắt |

Sau khi sửa, lô sạch còn 0 ứng viên và 0 lỗi luật, còn lô luyện tập ra 13 ứng viên. Nghĩa là hàng
đợi đủ nhỏ để xem hết mà vẫn giữ được các ca thật.

## 2. Vì sao báo hết ứng viên làm F1 giảm?

Điểm là F1 của cặp `(type, target)`, nên một dòng báo thừa trừ đúng bằng một lỗi bỏ sót.

Con số của nhóm: với cách ghép thô ban đầu, lô sạch 50 ảnh đã ra 18 ứng viên dù **không có lỗi nào**
được gài, tức khoảng 90 ứng viên trên 250 ảnh. Báo hết số đó cộng với 11 lỗi luật thì precision rơi
xuống khoảng 19/109 ≈ 0,17 trong khi recall không tăng thêm chút nào, vì 90 ứng viên kia không phải lỗi.
Ngay cả với bản ghép đã sửa, nếu nhóm nộp cả 13 ứng viên thay vì 8 ca đã xem ảnh thì precision tụt từ
19/19 = 1,00 xuống 19/24 ≈ 0,79, vì 5 ca còn lại không phải lỗi gán nhãn: hai ca là box lặp và lỗi
`thing_overlap` đã bắt ở phần luật, ba ca còn lại là vật xếp sát nhau nên box chồng nhau tự nhiên.

Chỗ này là lý do lab không cho nhãn gốc: detection và panoptic của COCO vốn lệch nhau, nên "ứng viên"
không đồng nghĩa với "lỗi", và chỉ có mở ảnh ra xem mới phân biệt được.

## 3. Quyết định và lineage

QC v1: **19/250 = 7,6%** ảnh lỗi, trên ngưỡng 2% của Day 7, nên lô v1 là **Hold**, không phát hành
để train. Quyết định đã ghi vào `runs/lineage.jsonl`:

```
decision  lab250_95697c6d4612  HOLD
release   lab250_95697c6d4612_v2  parent lab250_95697c6d4612
```

`python scripts/lineage.py impact --release-id lab250_95697c6d4612` trả về
`R-021: affected=True action=review_or_retrain`.

Run `R-021` đã train trên đúng lô v1 này. Sửa dataset không sửa được model đã học: trọng số của R-021
được tạo ra từ 19 ảnh lỗi kia, trong đó có 2 ảnh thiếu box và 2 ảnh ghi sai lớp, nên model đã học rằng
những vật đó không tồn tại hoặc thuộc lớp khác. Phát hành v2 chỉ làm sạch dữ liệu cho lần train sau.
R-021 phải được đánh giá lại trên tập val sạch, và nếu sai số còn đọng ở đúng các lớp bị ảnh hưởng thì
train lại từ v2. Ngược lại, nếu không ghi lineage thì không ai biết run nào đã ăn phải lô này.

## 4. Hash chứng minh gì, không chứng minh gì?

sha256 trong `manifest.csv` chứng minh file còn đúng từng byte như lúc đóng gói: ai tải lô v2 về
cũng tính lại được và biết ảnh hay nhãn có bị đổi, bị cắt, bị nén lại hay không trên đường truyền.
Nó cũng cho phép `pack_release.py` tạo ra một mã duy nhất cho cả lô, nên hai bên nói chuyện với nhau
bằng một con số thay vì bằng tên thư mục.

Nó không chứng minh nhãn đúng. Hai ảnh `000000006723` và `000000020247` trong lô này có hash ghi
trong `manifest.json` không khớp file; nhóm mở ảnh ra xem, ảnh còn nguyên và đúng nội dung, nên đây là
hash chép sai chứ không phải ảnh hỏng; bản thân con hash không nói được điều đó, chỉ con mắt nói được.
Ngược lại, một box ghi `bus` cho chiếc sedan ở `000000023272` vẫn cho ra hash hợp lệ. `check_handover.py`
PASS cũng chỉ có nghĩa lô đúng định dạng và nhất quán, không có nghĩa nhãn đúng.

## 5. Truy vết

Ticket của team AI nói model hay bỏ sót `bottle` bị che, và nêu `scene_197`, `scene_309`.
Changelog cho biết v1.3 đổi quy tắc đúng lớp `bottle`: vật bị che trên 50% hoặc cắt mép ảnh vẫn phải
gán box, còn v1.2 cho phép bỏ qua.

- `tier_a` (2 ảnh): ảnh nằm trong hai cảnh team AI nêu, thuộc job guideline cũ v1.2, và trong
  `labels/` có ít nhất một box `bottle`.
- `tier_b` (4 ảnh): cùng hai điều kiện sau (job v1.2, có box `bottle`) nhưng ở cảnh chưa ai báo.
- `notify` (5 người): A02, A04, A05, Q01, Q03, tức người gán và người kiểm của các job chứa ảnh tầng a
  và b, lấy từ `jobs.csv`.

Tiêu chí lấy guideline **theo job**, không theo `guideline_version` ghi ở từng ảnh, vì chính trường đó
có thể sai: lô này có hai ảnh `guideline_mismatch` (`000000002157`, `000000003553`) ghi v1.3 trong khi
job J02 của chúng là v1.2. Nếu lọc theo ảnh thì hai ảnh đó bị loại khỏi danh sách cần mở lại, đúng vào
những ảnh đáng ngờ nhất. Guideline là thứ người gán được giao lúc làm job, nên nó thuộc về job.

Lọc theo job cũ cũng giữ cho `notify` không phình: chỉ những job v1.2 có ảnh chứa `bottle` mới bị gọi
tên, chứ không phải mọi người của mọi job cũ.

## 6. Bug hoặc điểm chưa rõ trong lab

**(1) `run_lab.py` chết trên Windows, và lineage không được ghi.** `run_lab.py` gọi `inject_release.py`
bằng `subprocess.run([sys.executable, ...])` mà không ép UTF-8, nên tiến trình con in dòng cuối
(`... validator KHÔNG đọc ...`) ra console cp1252 và chết với `UnicodeEncodeError`. Lô vẫn được ghi đầy
đủ vì lỗi rơi vào lệnh `print` cuối cùng, nhưng `run_lab.py` dừng ngay đó nên **hai sự kiện lineage
`inject` và `train R-021` không bao giờ được ghi**, trong khi CP3 và H14 đều cần chúng. Cách chạy được:

```
PYTHONUTF8=1 python scripts/run_lab.py --seeds 3007
```

`scripts/export_submission.py --import` gọi `inject_release.py` theo đúng kiểu đó, nên người chấm chạy
trên Windows gặp lại đúng lỗi này khi dựng lại lô của nhóm. Nhóm đã thử: clone repo ra chỗ khác rồi
chạy `python scripts/export_submission.py --import submission/r3007` thì chết với cùng traceback, thêm
`PYTHONUTF8=1` thì chạy xong và `check_handover.py` ra 17 PASS. Bộ test của chính repo cũng vậy:
`python tests/test_pipeline.py` ra 2 lỗi trên console mặc định, và `PYTHONUTF8=1 python tests/test_pipeline.py`
ra 6 test OK (1 skip vì chưa có pool đề ẩn).

**(4) Repo không có `.gitattributes`, nên hash của lô v2 hỏng sau khi clone trên Windows.**
Git mặc định bật `core.autocrlf=true` trên Windows. File nhãn được commit dạng LF, nhưng lúc clone ra
lại thành CRLF, nên byte đổi và sha256 trong `manifest.csv` sai hết. Nhóm đo trên bản clone sạch:
**241/482 file lệch hash**, đủ để H8 FAIL và H15 FAIL ở máy người chấm dù không ai sửa gì trong lô.
Nhóm thêm `.gitattributes` với `* -text` rồi clone lại: 0/482 lệch, mã zip khớp `.sha256`, và
`check_handover.py` trên bản clone ra 17 PASS. Đề nghị đưa `.gitattributes` vào repo đề, vì nhóm nào
cũng dính và sẽ mất điểm mục 3 mà không hiểu vì sao.

**(2) `dedupe()` có thể tạo ra một ảnh trông y như `missing_box` mà không phải lỗi gài.**
`inject_release.py` bỏ các box cùng lớp có IoU > 0.7 để `duplicate_box` chỉ còn lỗi gài. Ở
`000000001818` có hai con ngựa vằn đứng chồng nhau, chỉ còn một box zebra, nên con còn lại trông như
bị thiếu box. Nhóm xếp ca này vào `rejected` vì box hiện có đã trùm 50% pixel của nó và khớp khung tới
IoU 0,72, nhưng đây là ca nhóm ít chắc chắn nhất trong 13 ứng viên.

**(3) Một lỗi gài có thể hiện ra thành hai loại.** `thing_overlap` ở `000000013659` sơn pixel của segment
`laptop` đè lên tóc người ngồi, nên bản đối chiếu lại báo thêm `missing_box` cho chính cái laptop đó
(laptop vẫn có box 11 và 12). Không phải bug, nhưng nhóm nào chỉ nhìn danh sách ứng viên mà không mở
ảnh sẽ nộp thừa một dòng.
