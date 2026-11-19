# Bảo mật khi làm việc

Trả lời gắn với lô `lab250_95697c6d4612` (250 ảnh, 10 job, người gán A01–A05, người kiểm Q01–Q03).

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp

Không chép. Lô nằm trên máy và tài khoản được cấp cho công việc này, chép ra USB là đưa dữ liệu
ra khỏi vùng mà công ty còn kiểm soát được: USB rơi mất thì không ai biết lô đã đi đâu, và trong
nhật ký cũng không còn dấu vết ai cầm bản nào. Gửi qua email cá nhân hay nhờ người khác làm hộ
cũng sai vì lý do y hệt: một bản sao nữa xuất hiện ở chỗ không ai quản, và phần việc lại do người
không có tên trong `jobs.csv` làm, nên lúc truy vết sẽ không biết quy cho ai. Cách đúng là xin gia
hạn hoặc xin quyền truy cập từ xa vào đúng máy đó, hoặc bàn giao phần còn lại cho người trong nhóm
có quyền, ghi lại việc bàn giao để `truyvet.csv` vẫn đúng người.

## 2. Năm việc: được hay không

- Mở job được giao trên máy công ty: được. Đây là việc đúng người, đúng máy, có ghi nhận.
- Chụp màn hình gửi người quen: không. Ảnh chụp cũng là dữ liệu của lô, gửi ra ngoài là rò rỉ,
  dù chỉ để hỏi cho vui.
- Chép lô ra USB: không, như mục 1.
- Dán nhãn thật lên chatbot: không. Với lô lab này ảnh COCO là dữ liệu công khai nên được phép
  hỏi AI (và nhóm đã ghi lại trong `prompts.md`), nhưng nhãn và ảnh của dự án thật thì không: nội
  dung dán lên dịch vụ ngoài coi như đã rời khỏi tay mình.
- Đưa tài khoản CVAT cho đồng nghiệp: không. Dùng chung tài khoản thì mọi thao tác đều mang tên
  một người, `annotator` và `reviewer` trong `jobs.csv` hết ý nghĩa, và không còn tách được ai làm gì.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ

Lô này có ảnh chụp người ở cự ly gần, mặt nhận ra được: `000000016598` (một người cầm điện thoại
chụp gương, khuôn mặt chiếm gần hết nửa trên khung hình) và `000000004395` (một người mặc áo sơ mi
thắt cà vạt, mặt nhìn nghiêng rõ nét). Việc phải làm là Hold lô lại và báo người phụ trách dữ liệu
cùng người kiểm của job chứa ảnh đó, kèm danh sách ảnh cụ thể, rồi chờ quyết định.

Không tự làm mờ, vì làm mờ là sửa ảnh gốc: lô v1 đã bàn giao và đã có `release_id` cùng sha256, sửa
ảnh là đổi hash và phá mất bản gốc mà mọi bản sau đối chiếu vào. Cũng không tự xoá ảnh, vì xoá là
mất bằng chứng và mất luôn khả năng kiểm tra xem còn ảnh nào tương tự. Quyết định làm mờ, xoá, hay
xin lại thoả thuận của người trong ảnh thuộc về người phụ trách dữ liệu, không phải người kiểm.
Nếu được chấp thuận thì bản đã làm mờ ra thành một lô mới có lô cha là v1, đúng cách lô v2 trong
bài này được dựng.
