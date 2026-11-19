#!/usr/bin/env python3
"""Công cụ xem ảnh của nhóm: vẽ box detection và viền segment panoptic lên ảnh, cắt quanh vật.

  python tools/view_candidate.py runs/r3007/delivery --candidates runs/r3007/candidates.json --out crops

Đây KHÔNG phải validator: file này được dùng Pillow (RULES.md cho phép với công cụ xem ảnh).
Mỗi ứng viên ra một PNG: bên trái ảnh gốc đã cắt, bên phải cùng vùng đó có box (đỏ) và
pixel segment (xanh). Người xem tự kết luận rồi ghi review_log.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validator"))
import validate as V  # noqa: E402

PAD = 0.35          # nới vùng cắt theo kích thước vật
MIN_CROP = 140      # vùng cắt nhỏ nhất (pixel ảnh gốc)
TARGET = 520        # chiều rộng mỗi nửa sau khi phóng to


def crop_box(seg_runs, box_px, width, height):
    xs = [min(x0 for _y, x0, _x1 in seg_runs), max(x1 for _y, _x0, x1 in seg_runs)]
    ys = [min(y for y, _x0, _x1 in seg_runs), max(y for y, _x0, _x1 in seg_runs) + 1]
    if box_px:
        xs += [box_px[0], box_px[2]]
        ys += [box_px[1], box_px[3]]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    pad_x = max((x1 - x0) * PAD, (MIN_CROP - (x1 - x0)) / 2, 8)
    pad_y = max((y1 - y0) * PAD, (MIN_CROP - (y1 - y0)) / 2, 8)
    return (max(0, int(x0 - pad_x)), max(0, int(y0 - pad_y)),
            min(width, int(x1 + pad_x)), min(height, int(y1 + pad_y)))


def render(d: V.Delivery, cand: dict, out_dir: Path, index: int) -> Path:
    name = cand["image"]
    width, height, runs = V.mask_runs(d, name)
    seg_runs = runs[cand["segment"]]
    focus_ids = [cand["box"]] if "box" in cand else cand.get("boxes", [])
    boxes = []
    for idx, (cid, x, y, w, h) in enumerate(d.boxes(name)):
        if 0 <= cid < len(d.class_names):
            boxes.append((idx, d.class_names[cid],
                          ((x - w / 2) * width, (y - h / 2) * height, (x + w / 2) * width, (y + h / 2) * height)))
    focus = [b for b in boxes if b[0] in focus_ids]
    region = crop_box(seg_runs, focus[0][2] if focus else None, width, height)

    img = Image.open(d.root / d.manifest[name]["image"]).convert("RGB")
    raw = img.crop(region)
    overlay = Image.new("RGBA", raw.size, (0, 0, 0, 0))
    pen = ImageDraw.Draw(overlay)
    for y, x0, x1 in seg_runs:
        if region[1] <= y < region[3]:
            pen.line([(x0 - region[0], y - region[1]), (x1 - region[0], y - region[1])], fill=(0, 220, 120, 90))
    marked = Image.alpha_composite(raw.convert("RGBA"), overlay).convert("RGB")
    pen = ImageDraw.Draw(marked)
    for idx, cls, px in boxes:
        shifted = [px[0] - region[0], px[1] - region[1], px[2] - region[0], px[3] - region[1]]
        if shifted[2] < 0 or shifted[3] < 0 or shifted[0] > raw.width or shifted[1] > raw.height:
            continue
        hot = idx in focus_ids
        pen.rectangle(shifted, outline=(255, 40, 40) if hot else (255, 190, 0), width=2 if hot else 1)
        pen.text((max(2, shifted[0] + 3), max(2, shifted[1] + 2)), f"{idx} {cls}",
                 fill=(255, 40, 40) if hot else (255, 190, 0))

    scale = TARGET / max(1, raw.width)
    size = (int(raw.width * scale), int(raw.height * scale))
    raw, marked = raw.resize(size, Image.LANCZOS), marked.resize(size, Image.LANCZOS)
    sheet = Image.new("RGB", (size[0] * 2 + 12, size[1]), (20, 20, 20))
    sheet.paste(raw, (0, 0))
    sheet.paste(marked, (size[0] + 12, 0))
    out = out_dir / f"{index:02d}_{name}_{'-'.join(cand['types'])}.png"
    sheet.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Vẽ box và segment lên ảnh để xem bằng mắt")
    ap.add_argument("delivery")
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="chỉ ảnh này")
    args = ap.parse_args()
    d = V.Delivery(Path(args.delivery))
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))["candidates"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, cand in enumerate(cands, start=1):
        if args.only and cand["image"] != args.only:
            continue
        path = render(d, cand, out_dir, index)
        print(f"{index:02d} {cand['image']} {'/'.join(cand['types'])}: {cand['why']}")
        print(f"   {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
