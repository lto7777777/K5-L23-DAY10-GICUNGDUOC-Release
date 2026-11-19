#!/usr/bin/env python3
"""Đo từng cặp (segment, box) của một lô để chọn ngưỡng đối chiếu.

  python tools/probe_pairs.py runs/clean/delivery

Chạy trên LÔ SẠCH trước: mọi cặp in ra ở đó đều là lệch tự nhiên của COCO chứ không phải lỗi.
Nhìn cột contain / cover / IoU của các cặp đó rồi mới chốt ngưỡng trong validator, thay vì đoán.
Đây là cách nhóm thấy bản ghép đầu tiên bắt nhầm 18 ca trên 50 ảnh sạch: vật nhỏ nằm trong box
của vật to (tie trong person, keyboard trong laptop) cũng đạt contain 1.00.

Người phụ trách: Phạm Thị Lương (đối chiếu detection ↔ panoptic, chọn ngưỡng).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validator"))
import validate as V  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="In đặc trưng của từng cặp segment-box")
    ap.add_argument("delivery")
    ap.add_argument("--min-px", type=int, default=400, help="bỏ qua segment nhỏ hơn (mặc định 400)")
    ap.add_argument("--ghep-tho", action="store_true",
                    help="ghép theo số pixel chứa được (cách cũ), thay vì contain × bbox IoU. "
                         "Dùng để thấy lại vì sao cách cũ đẻ ra ứng viên giả")
    args = ap.parse_args()
    diem = (lambda f: f[0]) if args.ghep_tho else (lambda f: f[0] * f[2])
    print("Cách ghép:", "chỉ theo contain (thô)" if args.ghep_tho else "contain × bbox IoU")
    d = V.Delivery(Path(args.delivery))

    rows = []
    for name in sorted(d.manifest):
        if not (d.root / d.manifest[name]["image"]).is_file():
            continue
        got = V.mask_runs(d, name)
        ann = d.ann.get(name)
        if got is None or not ann:
            continue
        width, height, runs = got
        boxes = []
        for idx, (cid, x, y, w, h) in enumerate(d.boxes(name)):
            if 0 <= cid < len(d.class_names):
                px = ((x - w / 2) * width, (y - h / 2) * height, (x + w / 2) * width, (y + h / 2) * height)
                boxes.append({"i": idx, "name": d.class_names[cid], "px": px,
                              "area": max(1.0, (px[2] - px[0]) * (px[3] - px[1]))})
        for seg in ann["segments_info"]:
            cat = d.categories.get(seg["category_id"])
            if not cat or not cat.get("isthing") or seg.get("iscrowd"):
                continue
            rs = runs.get(seg["id"])
            if not rs:
                continue
            seg_px = sum(x1 - x0 for _y, x0, x1 in rs)
            if seg_px < args.min_px:
                continue
            sb = V.seg_bbox(rs)
            best_any = best_same = None
            for b in boxes:
                n = V.inside(rs, b["px"])
                if not n:
                    continue
                feat = (n / seg_px, n / b["area"], V.bbox_iou(sb, b["px"]), b["name"], b["i"])
                if best_any is None or diem(feat) > diem(best_any):
                    best_any = feat
                if b["name"] == cat["name"] and (best_same is None or diem(feat) > diem(best_same)):
                    best_same = feat
            rows.append((name, cat["name"], seg_px, best_same, best_any))

    print(f"Số segment xét: {len(rows)} (bỏ qua segment < {args.min_px} px)")

    mismatch = [r for r in rows if r[4] and r[4][3] != r[1]]
    print(f"\n-- cặp khác lớp: ghép tốt nhất lại là box của lớp khác ({len(mismatch)} ca) --")
    for name, cls, px, same, any_ in sorted(mismatch, key=lambda r: -r[4][2]):
        note = f"có box cùng lớp: contain {same[0]:.2f} IoU {same[2]:.2f}" if same else "KHÔNG có box cùng lớp"
        print(f"   {name} seg={cls:<14} px={px:<7} box={any_[3]:<14} "
              f"contain={any_[0]:.2f} cover={any_[1]:.2f} IoU={any_[2]:.2f}  | {note}")

    print("\n-- vật không có box cùng lớp nào chứa >= 50% pixel (ứng viên thiếu box) --")
    for name, cls, px, same, _any in sorted(rows, key=lambda r: -r[2]):
        if same is None or same[0] < 0.5:
            print(f"   {name} seg={cls:<14} px={px:<7} "
                  + (f"box cùng lớp gần nhất: contain {same[0]:.2f} IoU {same[2]:.2f}" if same else "không có box cùng lớp"))

    print("\n-- cặp cùng lớp có pixel rơi ra ngoài box (ứng viên box lệch) --")
    for name, cls, px, same, _any in sorted(rows, key=lambda r: (r[3][0] if r[3] else 9)):
        if same and 0.3 <= same[0] < 0.95:
            print(f"   {name} seg={cls:<14} px={px:<7} contain={same[0]:.2f} cover={same[1]:.2f} IoU={same[2]:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
