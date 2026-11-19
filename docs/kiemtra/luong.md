# Đo nhiễu tự nhiên trên lô sạch — Lương

Lệnh 1: python tools/probe_pairs.py runs/clean/delivery --ghep-tho
Cách ghép: chỉ theo contain (thô)
Số segment xét: 305 (bỏ qua segment < 400 px)

-- cặp khác lớp: ghép tốt nhất lại là box của lớp khác (22 ca) --
   000000057597 seg=car            px=520     box=truck          contain=1.00 cover=0.41 IoU=0.65  | có box cùng lớp: contain 0.95 IoU 0.97
   000000062554 seg=broccoli       px=78160   box=dining table   contain=1.00 cover=0.30 IoU=0.42  | có box cùng lớp: contain 1.00 IoU 1.00
   000000059598 seg=keyboard       px=6108    box=laptop         contain=1.00 cover=0.09 IoU=0.12  | có box cùng lớp: contain 1.00 IoU 0.99
   000000057672 seg=person         px=2912    box=boat           contain=1.00 cover=0.04 IoU=0.09  | có box cùng lớp: contain 1.00 IoU 0.99
   000000058350 seg=pizza          px=7650    box=couch          contain=1.00 cover=0.05 IoU=0.08  | có box cùng lớp: contain 1.00 IoU 0.99
   000000057672 seg=person         px=2896    box=boat           contain=1.00 cover=0.04 IoU=0.08  | có box cùng lớp: contain 1.00 IoU 0.98
   000000057672 seg=person         px=2352    box=boat           contain=1.00 cover=0.03 IoU=0.08  | có box cùng lớp: contain 1.00 IoU 0.99
   000000061960 seg=bed            px=4838    box=person         contain=1.00 cover=0.02 IoU=0.07  | có box cùng lớp: contain 1.00 IoU 0.10
   000000062554 seg=bowl           px=12386   box=dining table   contain=1.00 cover=0.05 IoU=0.07  | có box cùng lớp: contain 1.00 IoU 0.99
   000000057672 seg=person         px=2521    box=boat           contain=1.00 cover=0.04 IoU=0.07  | có box cùng lớp: contain 1.00 IoU 0.98
   000000057672 seg=person         px=1386    box=boat           contain=1.00 cover=0.02 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 0.96
   000000062808 seg=knife          px=1997    box=person         contain=1.00 cover=0.02 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 1.00
   000000058705 seg=banana         px=2615    box=person         contain=1.00 cover=0.02 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 0.99
   000000057672 seg=person         px=1408    box=boat           contain=1.00 cover=0.02 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 0.98
   000000063047 seg=cup            px=1890    box=person         contain=1.00 cover=0.02 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 0.98
   000000061471 seg=bottle         px=1443    box=toilet         contain=1.00 cover=0.03 IoU=0.04  | có box cùng lớp: contain 0.99 IoU 0.97
   000000058350 seg=knife          px=1075    box=person         contain=1.00 cover=0.01 IoU=0.04  | có box cùng lớp: contain 1.00 IoU 0.98
   000000057672 seg=person         px=1308    box=boat           contain=1.00 cover=0.02 IoU=0.03  | có box cùng lớp: contain 0.99 IoU 0.97
   000000060932 seg=tie            px=1982    box=person         contain=1.00 cover=0.02 IoU=0.03  | có box cùng lớp: contain 1.00 IoU 0.99
   000000058350 seg=knife          px=651     box=person         contain=1.00 cover=0.01 IoU=0.03  | có box cùng lớp: contain 0.98 IoU 0.97
   000000062554 seg=fork           px=1144    box=dining table   contain=1.00 cover=0.00 IoU=0.02  | có box cùng lớp: contain 1.00 IoU 0.98
   000000062353 seg=person         px=417     box=giraffe        contain=1.00 cover=0.01 IoU=0.02  | có box cùng lớp: contain 1.00 IoU 0.96

-- vật không có box cùng lớp nào chứa >= 50% pixel (ứng viên thiếu box) --

-- cặp cùng lớp có pixel rơi ra ngoài box (ứng viên box lệch) --
   000000061333 seg=book           px=531     contain=0.94 cover=0.52 IoU=0.98

Lệnh 2: python tools/probe_pairs.py runs/clean/delivery
Cách ghép: contain × bbox IoU
Số segment xét: 305 (bỏ qua segment < 400 px)

-- cặp khác lớp: ghép tốt nhất lại là box của lớp khác (0 ca) --

-- vật không có box cùng lớp nào chứa >= 50% pixel (ứng viên thiếu box) --

-- cặp cùng lớp có pixel rơi ra ngoài box (ứng viên box lệch) --
   000000061333 seg=book           px=531     contain=0.94 cover=0.52 IoU=0.98

Nhận xét: cùng 50 ảnh không có lỗi nào, cách ghép thô ra 22 ứng viên giả, cách contain × IoU
ra 0. Quy ra 250 ảnh thì cách thô đẻ khoảng 90 ứng viên, xem không xuể mà cũng không phải lỗi.