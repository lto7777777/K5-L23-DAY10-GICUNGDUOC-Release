#!/usr/bin/env python3
"""Gộp các file review của từng người thành một review_log.csv.

  python tools/gop_review.py --thu-muc submission/de_an

Mỗi người ghi file riêng (review_tho.csv, review_hau.csv, ...) để không ai đụng file của ai trong
40 phút làm đề ẩn. Lệnh này nối chúng lại thành review_log.csv rồi mới chạy merge_review.py.

Đọc bằng utf-8-sig: Excel và PowerShell hay để lại BOM ở đầu file, mà BOM biến tên cột image thành
một tên khác và merge_review.py sẽ không tìm thấy cột nữa.

Kiểm luôn hai thứ hay mất điểm: verdict phải là confirmed hoặc rejected, và ghi chú phải dài ít nhất
20 ký tự, vì bộ kiểm loại những dòng ngắn hơn.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

COT = ["image", "type", "verdict", "note"]
SEMANTIC = {"class_swap", "bbox_drift", "missing_box", "category_swap", "instance_merge"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Gộp review của từng người thành review_log.csv")
    ap.add_argument("--thu-muc", default="submission/de_an", help="thư mục chứa review_*.csv")
    ap.add_argument("--out", help="mặc định <thư mục>/review_log.csv")
    args = ap.parse_args()
    folder = Path(args.thu_muc)
    out = Path(args.out) if args.out else folder / "review_log.csv"

    files = sorted(p for p in folder.glob("review_*.csv") if p.name != out.name)
    if not files:
        raise SystemExit(f"Không thấy file review_*.csv nào trong {folder}")

    rows, canh_bao = [], []
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as f:
            doc = list(csv.DictReader(f))
        for i, row in enumerate(doc, start=2):
            thieu = [c for c in COT if not (row.get(c) or "").strip()]
            if thieu:
                canh_bao.append(f"{path.name} dòng {i}: thiếu cột {thieu}")
                continue
            verdict = row["verdict"].strip()
            note = row["note"].strip()
            if verdict not in ("confirmed", "rejected"):
                canh_bao.append(f"{path.name} dòng {i}: verdict '{verdict}' không hợp lệ")
            if row["type"].strip() not in SEMANTIC:
                canh_bao.append(f"{path.name} dòng {i}: type '{row['type'].strip()}' không phải lỗi gán nhãn")
            if len(note) < 20:
                canh_bao.append(f"{path.name} dòng {i}: ghi chú chỉ {len(note)} ký tự, cần >= 20")
            rows.append({c: row[c].strip() for c in COT})
        print(f"  {path.name:<28}{len(doc)} dòng")

    dem: dict[str, int] = {}
    for r in rows:
        dem[r["image"]] = dem.get(r["image"], 0) + 1
    trung = sorted(k for k, v in dem.items() if v > 1)
    if trung:
        canh_bao.append(f"ảnh bị hai người cùng xem: {trung[:5]}")

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COT)
        w.writeheader()
        w.writerows(rows)

    print(f"\n{len(files)} file -> {out}: {len(rows)} dòng "
          f"({sum(1 for r in rows if r['verdict'] == 'confirmed')} confirmed, "
          f"{sum(1 for r in rows if r['verdict'] == 'rejected')} rejected)")
    if canh_bao:
        print(f"\n{len(canh_bao)} cảnh báo, sửa trước khi nộp:")
        for dong in canh_bao:
            print(f"  - {dong}")
        return 1
    print("Không có cảnh báo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
