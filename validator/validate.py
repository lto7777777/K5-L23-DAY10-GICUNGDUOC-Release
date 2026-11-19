#!/usr/bin/env python3
"""Validator của nhóm — Day 10.

  python validator/validate.py <thư_mục_delivery> --out rules.json [--candidates candidates.json]

Chỉ đọc thư mục delivery truyền vào. Chỉ thư viện chuẩn + scripts/pngutil.py.
Không đọc _private/, không đọc data_source/, không dùng mạng.

--out        : LỖI LUẬT (9 loại). Đây là file đưa vào merge_review.py.
--candidates : ỨNG VIÊN lỗi gán nhãn, để người xem ảnh rồi ghi review_log.csv.

Ý tưởng: lỗi gán nhãn không có nhãn gốc để so, nên nguồn đối chiếu duy nhất là
nguồn nhãn còn lại của cùng ảnh. Tín hiệu chính là PIXEL CỦA MASK (không phải IoU
của hai bbox): với một cặp ghép đúng, gần như toàn bộ pixel của segment nằm trong
box detection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pngutil  # noqa: E402

# ----------------------------------------------------------------- ngưỡng
BOX_TOL = 0.01          # mép ảnh: box tràn quá 1% mới tính là lỗi (giống bộ kiểm)
DUP_SIZE_PX = 1.0       # box lặp: chênh kích thước < 1 px
DUP_SHIFT_PX = 3.0      # box lặp: lệch tâm <= 3 px
MIN_SEG_PX = 600        # segment nhỏ hơn thì bỏ qua khi đối chiếu (nhiễu tự nhiên)
MIN_SEG_FRAC = 0.003    # ... và phải chiếm >= 0.3% diện tích ảnh
MISS_CONT = 0.50        # box cùng lớp phải chứa >= 50% pixel segment mới coi là có box
SWAP_CONT = 0.85        # box khác lớp chứa >= 85% pixel ...
SWAP_IOU = 0.45         # ... và bbox khớp >= 0.45          -> lệch lớp giữa hai nguồn
DRIFT_CONT = 0.92       # cùng lớp nhưng box để rơi > 8% pixel ra ngoài -> box lệch
MERGE_COVER = 0.45      # box bị segment phủ >= 45% diện tích -> box này thuộc segment
MERGE_CONT = 0.25       # và segment gộp >= 25% pixel vào box đó


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ----------------------------------------------------------------- đọc lô
class Delivery:
    def __init__(self, root: Path):
        self.root = root
        self.manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))["items"]
        self.meta = {m["image"]: m for m in json.loads((root / "metadata.json").read_text(encoding="utf-8"))["items"]}
        with (root / "jobs.csv").open(encoding="utf-8", newline="") as f:
            self.jobs = {row["job_id"]: row for row in csv.DictReader(f)}
        self.class_names = []
        for line in (root / "classes.txt").read_text(encoding="utf-8").splitlines():
            if line.strip():
                self.class_names.append(line.split(" ", 1)[1].strip())
        pan = json.loads((root / "panoptic.json").read_text(encoding="utf-8"))
        self.categories = {c["id"]: c for c in pan["categories"]}
        self.pan_by_file = {Path(im["file_name"]).stem: im for im in pan["images"]}
        self.ann = {Path(a["file_name"]).stem: a for a in pan["annotations"]}

    def boxes(self, name: str) -> list[tuple[int, float, float, float, float]]:
        """Đọc nhãn YOLO. Dòng hỏng (không đủ 5 số) bỏ qua ở đây."""
        out = []
        path = self.root / self.manifest[name]["label"]
        if not path.is_file():
            return out
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                out.append((int(float(parts[0])), *(float(v) for v in parts[1:5])))
            except ValueError:
                continue
        return out

    def size(self, name: str) -> tuple[int, int]:
        im = self.pan_by_file.get(name)
        return (im["width"], im["height"]) if im else (0, 0)


# ----------------------------------------------------------------- lỗi luật
def rule_faults(d: Delivery) -> tuple[list[dict], dict]:
    """Một ảnh mang nhiều nhất một lỗi: xét theo thứ tự file -> hash -> guideline -> nhãn."""
    faults: list[dict] = []
    notes: dict[str, list[str]] = defaultdict(list)
    scenes: dict[str, set] = defaultdict(set)

    for name, item in sorted(d.manifest.items()):
        m = d.meta.get(name, {})
        if m:
            scenes[m["scene_id"]].add(m["split"])
        if not (d.root / item["image"]).is_file():
            faults.append({"type": "missing_image", "target": name})
            continue
        bad_hash = []
        for key, field in (("image", "image_sha256"), ("label", "label_sha256"), ("mask", "mask_sha256")):
            p = d.root / item[key]
            if field in item and p.is_file() and sha256_file(p) != item[field]:
                bad_hash.append(key)
        if bad_hash:
            faults.append({"type": "wrong_hash", "target": name})
            notes[name].append("sha256 lệch ở: " + ",".join(bad_hash))
            continue
        job = d.jobs.get(m.get("job_id"), {})
        if job and m.get("guideline_version") != job.get("guideline"):
            faults.append({"type": "guideline_mismatch", "target": name})
            notes[name].append(f"ảnh ghi {m.get('guideline_version')}, job {m.get('job_id')} ghi {job.get('guideline')}")
            continue
        kind = label_fault(d, name)
        if kind:
            faults.append({"type": kind, "target": name})

    for scene, splits in sorted(scenes.items()):
        if len(splits) > 1:
            faults.append({"type": "scene_leak", "target": scene})

    for name in sorted(d.manifest):
        kind = panoptic_fault(d, name)
        if kind:
            faults.append({"type": kind, "target": name})
    return faults, notes


def label_fault(d: Delivery, name: str) -> str | None:
    rows = d.boxes(name)
    width, height = d.size(name)
    for cid, _x, _y, _w, _h in rows:
        if not 0 <= cid < len(d.class_names):
            return "invalid_class"
    for _cid, x, y, w, h in rows:
        if x - w / 2 < -BOX_TOL or y - h / 2 < -BOX_TOL or x + w / 2 > 1 + BOX_TOL or y + h / 2 > 1 + BOX_TOL:
            return "bbox_out_of_bounds"
    if width and height:
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                if a[0] != b[0]:
                    continue
                if abs(a[3] - b[3]) * width > DUP_SIZE_PX or abs(a[4] - b[4]) * height > DUP_SIZE_PX:
                    continue
                if abs(a[1] - b[1]) * width <= DUP_SHIFT_PX and abs(a[2] - b[2]) * height <= DUP_SHIFT_PX:
                    return "duplicate_box"
    return None


def panoptic_fault(d: Delivery, name: str) -> str | None:
    ann = d.ann.get(name)
    if not ann:
        return None
    for seg in ann["segments_info"]:
        if seg["category_id"] not in d.categories:
            return "invalid_category_id"
    counts = mask_counts(d, name)
    if counts is None:
        return None
    for seg in ann["segments_info"]:
        if seg.get("area") is not None and counts.get(seg["id"], 0) < seg["area"]:
            return "thing_overlap"
    return None


_MASK_CACHE: dict[str, tuple] = {}


def mask_runs(d: Delivery, name: str):
    """Trả về (width, height, {segment_id: [(y, x0, x1), ...]}) — đọc mask một lần."""
    if name in _MASK_CACHE:
        return _MASK_CACHE[name]
    path = d.root / d.manifest[name]["mask"]
    if not path.is_file():
        return None
    width, height, pixels = pngutil.read_rgb(path)
    stride = width * 3
    runs: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for y in range(height):
        row = pixels[y * stride:(y + 1) * stride]
        x = 0
        for key, group in groupby(struct.iter_unpack("3B", row)):
            n = len(list(group))
            sid = key[0] + key[1] * 256 + key[2] * 65536
            if sid:
                runs[sid].append((y, x, x + n))
            x += n
    if len(_MASK_CACHE) > 4:
        _MASK_CACHE.clear()
    _MASK_CACHE[name] = (width, height, runs)
    return _MASK_CACHE[name]


def mask_counts(d: Delivery, name: str) -> dict[int, int] | None:
    got = mask_runs(d, name)
    if got is None:
        return None
    _, _, runs = got
    return {sid: sum(x1 - x0 for _y, x0, x1 in rs) for sid, rs in runs.items()}


def seg_bbox(runs: list[tuple[int, int, int]]) -> tuple[float, float, float, float]:
    return (min(x0 for _y, x0, _x1 in runs), min(y for y, _x0, _x1 in runs),
            max(x1 for _y, _x0, x1 in runs), max(y for y, _x0, _x1 in runs) + 1)


def bbox_iou(a: tuple, b: tuple) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def inside(runs: list[tuple[int, int, int]], box: tuple[float, float, float, float]) -> int:
    """Số pixel của segment nằm trong box (toạ độ pixel)."""
    bx0, by0, bx1, by1 = box
    total = 0
    for y, x0, x1 in runs:
        if y + 1 <= by0 or y >= by1:
            continue
        left, right = max(x0, bx0), min(x1, bx1)
        if right > left:
            total += int(right - left)
    return total


# ----------------------------------------------------------------- ứng viên
def candidates(d: Delivery) -> list[dict]:
    out = []
    for name in sorted(d.manifest):
        if not (d.root / d.manifest[name]["image"]).is_file():
            continue
        got = mask_runs(d, name)
        ann = d.ann.get(name)
        if got is None or not ann:
            continue
        width, height, runs = got
        boxes = []
        for idx, (cid, x, y, w, h) in enumerate(d.boxes(name)):
            if not 0 <= cid < len(d.class_names):
                continue
            px = ((x - w / 2) * width, (y - h / 2) * height, (x + w / 2) * width, (y + h / 2) * height)
            area = max(1.0, (px[2] - px[0]) * (px[3] - px[1]))
            boxes.append({"i": idx, "name": d.class_names[cid], "px": px, "area": area})
        for seg in ann["segments_info"]:
            cat = d.categories.get(seg["category_id"])
            if not cat or not cat.get("isthing") or seg.get("iscrowd"):
                continue
            rs = runs.get(seg["id"])
            if not rs:
                continue
            seg_px = sum(x1 - x0 for _y, x0, x1 in rs)
            if seg_px < MIN_SEG_PX or seg_px < MIN_SEG_FRAC * width * height:
                continue
            seg_name = cat["name"]
            sb = seg_bbox(rs)
            # Ghép theo HÌNH HỌC, không chỉ theo số pixel chứa được: một box lớn (person,
            # dining table) chứa trọn segment nhỏ bên trong nó cũng có contain = 1.00, nên
            # phải nhân thêm độ khớp bbox mới chọn đúng box của chính vật đó.
            scored = []
            for b in boxes:
                n = inside(rs, b["px"])
                if n:
                    scored.append({"cont": n / seg_px, "cover": n / b["area"],
                                   "iou": bbox_iou(sb, b["px"]), "box": b})
            scored.sort(key=lambda t: -t["cont"] * t["iou"])
            same = [t for t in scored if t["box"]["name"] == seg_name]
            base = {"image": name, "segment": seg["id"], "segment_class": seg_name, "segment_px": seg_px}

            if not same or same[0]["cont"] < MISS_CONT:
                # Vật này không có box nào cùng lớp: hoặc một bên ghi sai lớp, hoặc thiếu box.
                other = [t for t in scored if t["cont"] >= SWAP_CONT and t["iou"] >= SWAP_IOU]
                if other:
                    t = other[0]
                    out.append({**base, "types": ["class_swap", "category_swap"], "box": t["box"]["i"],
                                "box_class": t["box"]["name"], "contain": round(t["cont"], 3),
                                "iou": round(t["iou"], 3),
                                "why": f"cùng vị trí nhưng khác lớp: detection ghi {t['box']['name']}, "
                                       f"panoptic ghi {seg_name} (contain {t['cont']:.2f}, bbox IoU {t['iou']:.2f})"})
                elif seg_name in d.class_names:
                    out.append({**base, "types": ["missing_box"],
                                "why": f"segment {seg_name} {seg_px} px, không box {seg_name} nào chứa "
                                       f">= {int(MISS_CONT * 100)}% pixel của nó"})
                continue

            merged = [t for t in same if t["cover"] >= MERGE_COVER and t["cont"] >= MERGE_CONT]
            if len(merged) >= 2:
                covers = ", ".join(f"{t['cover']:.2f}" for t in merged)
                out.append({**base, "types": ["instance_merge"], "boxes": [t["box"]["i"] for t in merged],
                            "why": f"một segment {seg_name} phủ {len(merged)} box cùng lớp (cover {covers}): "
                                   "hai vật có thể đã bị gộp thành một segment"})
                continue

            t = same[0]
            if t["cont"] < DRIFT_CONT:
                out.append({**base, "types": ["bbox_drift"], "box": t["box"]["i"], "contain": round(t["cont"], 3),
                            "iou": round(t["iou"], 3),
                            "why": f"box {seg_name} để {1 - t['cont']:.0%} pixel của segment cùng lớp rơi "
                                   f"ra ngoài box (bbox IoU {t['iou']:.2f})"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Bắt lỗi luật và sinh ứng viên lỗi gán nhãn")
    ap.add_argument("delivery")
    ap.add_argument("--out", required=True)
    ap.add_argument("--candidates")
    args = ap.parse_args()
    root = Path(args.delivery)
    if not (root / "manifest.json").is_file():
        raise SystemExit(f"Không thấy {root / 'manifest.json'}")
    d = Delivery(root)
    faults, notes = rule_faults(d)
    pairs = sorted({(f["type"], f["target"]) for f in faults})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"errors": [{"type": t, "target": g} for t, g in pairs]}, indent=1) + "\n",
                              encoding="utf-8")
    by_type = Counter(t for t, _ in pairs)
    print(f"lỗi luật: {len(pairs)}  " + "  ".join(f"{k}={v}" for k, v in sorted(by_type.items())))
    for name, lines in sorted(notes.items()):
        for line in lines:
            print(f"  - {name}: {line}")
    if args.candidates:
        cands = candidates(d)
        Path(args.candidates).parent.mkdir(parents=True, exist_ok=True)
        Path(args.candidates).write_text(json.dumps({"candidates": cands}, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8")
        kinds = Counter(c["types"][0] for c in cands)
        print(f"ứng viên: {len(cands)}  " + "  ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
