#!/usr/bin/env python3
"""Test cho validator của nhóm: mỗi loại lỗi luật phải bắt được, lô sạch phải im lặng.

  python tests/test_validator.py

Lô dùng trong test là lô nhỏ tự dựng trong thư mục tạm (2 ảnh, mask 8x8), không đụng
data_source/ hay runs/. Nhờ vậy test chạy trong một giây và không phụ thuộc seed nào.

Người phụ trách: Đoàn Thị Ánh Hậu (luật phần panoptic).
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validator"))
sys.path.insert(0, str(ROOT / "scripts"))
import pngutil  # noqa: E402
import validate as V  # noqa: E402

SIZE = 8  # mask 8x8 cho nhanh


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_mask(path: Path, segments: list[tuple[int, int, int, int, int]]) -> dict[int, int]:
    """segments: (segment_id, x0, y0, x1, y1). Trả về số pixel thật của từng segment."""
    pixels = bytearray(SIZE * SIZE * 3)
    count: dict[int, int] = {}
    for sid, x0, y0, x1, y1 in segments:
        for y in range(y0, y1):
            for x in range(x0, x1):
                i = (y * SIZE + x) * 3
                pixels[i:i + 3] = bytes(pngutil.segment_rgb(sid))
        count[sid] = (x1 - x0) * (y1 - y0)
    pngutil.write_rgb(path, SIZE, SIZE, bytes(pixels))
    return count


def build(root: Path, images: list[dict]) -> Path:
    """Dựng một lô tối giản. Mỗi ảnh: name, boxes, segments, scene, split, job, guideline."""
    d = root / "delivery"
    for sub in ("images", "labels", "masks"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    names = [f"lop{i:02d}" for i in range(80)]
    categories = [{"id": i + 1, "name": names[i], "isthing": 1} for i in range(80)]
    (d / "classes.txt").write_text("".join(f"{i} {n}\n" for i, n in enumerate(names)), encoding="utf-8")

    manifest, meta, pan_images, pan_anns = {}, [], [], []
    for n, item in enumerate(images, start=1):
        name = item["name"]
        jpg = f"anh-gia-{name}".encode()          # validator chỉ băm ảnh, không giải mã
        (d / "images" / f"{name}.jpg").write_bytes(jpg)
        label = "".join(" ".join(str(v) for v in row) + "\n" for row in item.get("boxes", []))
        (d / "labels" / f"{name}.txt").write_bytes(label.encode())
        real = write_mask(d / "masks" / f"{name}.png", [(s["id"], *s["box"]) for s in item.get("segments", [])])
        manifest[name] = {
            "image": f"images/{name}.jpg", "label": f"labels/{name}.txt", "mask": f"masks/{name}.png",
            "image_sha256": item.get("fake_hash") or sha(jpg),
            "label_sha256": sha(label.encode()),
            "mask_sha256": sha((d / "masks" / f"{name}.png").read_bytes()),
        }
        meta.append({"image": name, "scene_id": item.get("scene", "scene_001"),
                     "split": item.get("split", "train"), "job_id": item.get("job", "J01"),
                     "guideline_version": item.get("guideline", "v1.2")})
        pan_images.append({"id": n, "file_name": f"{name}.jpg", "width": SIZE, "height": SIZE})
        pan_anns.append({"image_id": n, "file_name": f"{name}.png", "segments_info": [
            {"id": s["id"], "category_id": s.get("category_id", 1),
             "area": s.get("area", real[s["id"]]), "iscrowd": 0} for s in item.get("segments", [])]})
        if item.get("xoa_anh"):
            (d / "images" / f"{name}.jpg").unlink()

    (d / "panoptic.json").write_text(json.dumps(
        {"categories": categories, "images": pan_images, "annotations": pan_anns}), encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"items": manifest}), encoding="utf-8")
    (d / "metadata.json").write_text(json.dumps({"items": meta}), encoding="utf-8")
    (d / "jobs.csv").write_text("job_id,annotator,reviewer,guideline\nJ01,A01,Q01,v1.2\nJ02,A02,Q02,v1.3\n",
                                encoding="utf-8")
    return d


def faults(d: Path) -> set[tuple[str, str]]:
    V._MASK_CACHE.clear()
    rows, _notes = V.rule_faults(V.Delivery(d))
    return {(r["type"], r["target"]) for r in rows}


SACH = [
    {"name": "anh01", "boxes": [[0, 0.25, 0.25, 0.25, 0.25]],
     "segments": [{"id": 101, "box": (1, 1, 3, 3), "category_id": 1}]},
    {"name": "anh02", "boxes": [[1, 0.75, 0.75, 0.25, 0.25]],
     "segments": [{"id": 102, "box": (5, 5, 7, 7), "category_id": 2}]},
]


def tweak(index: int, **thay_doi) -> list[dict]:
    lo = copy.deepcopy(SACH)
    lo[index].update(thay_doi)
    return lo


class RuleTest(unittest.TestCase):
    def kiem(self, images, mong_doi):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(faults(build(Path(tmp), images)), mong_doi)

    def test_lo_sach_khong_bao_gi(self):
        self.kiem(SACH, set())

    def test_missing_image(self):
        self.kiem(tweak(0, xoa_anh=True), {("missing_image", "anh01")})

    def test_wrong_hash(self):
        self.kiem(tweak(0, fake_hash=sha(b"anh khac")), {("wrong_hash", "anh01")})

    def test_invalid_class(self):
        self.kiem(tweak(0, boxes=[[80, 0.25, 0.25, 0.25, 0.25]]), {("invalid_class", "anh01")})

    def test_bbox_out_of_bounds(self):
        self.kiem(tweak(0, boxes=[[0, 0.95, 0.5, 0.2, 0.2]]), {("bbox_out_of_bounds", "anh01")})

    def test_duplicate_box(self):
        doi = [[0, 0.25, 0.25, 0.25, 0.25], [0, 0.375, 0.25, 0.25, 0.25]]   # lệch 1 px, cùng cỡ
        self.kiem(tweak(0, boxes=doi), {("duplicate_box", "anh01")})

    def test_box_chong_nhau_tu_nhien_khong_phai_duplicate(self):
        doi = [[0, 0.25, 0.25, 0.25, 0.25], [0, 0.30, 0.25, 0.40, 0.40]]    # khác kích thước
        self.kiem(tweak(0, boxes=doi), set())

    def test_scene_leak(self):
        images = tweak(0, scene="scene_009")
        images[1]["scene"] = "scene_009"
        images[1]["split"] = "val"
        self.kiem(images, {("scene_leak", "scene_009")})

    def test_guideline_mismatch(self):
        self.kiem(tweak(0, guideline="v1.3"), {("guideline_mismatch", "anh01")})

    def test_invalid_category_id(self):
        self.kiem(tweak(0, segments=[{"id": 101, "box": (1, 1, 3, 3), "category_id": 9999}]),
                  {("invalid_category_id", "anh01")})

    def test_thing_overlap(self):
        """area khai 9 pixel nhưng mask chỉ còn 4: bị vật khác đè."""
        self.kiem(tweak(0, segments=[{"id": 101, "box": (1, 1, 3, 3), "category_id": 1, "area": 9}]),
                  {("thing_overlap", "anh01")})

    def test_moi_anh_chi_mot_loi_o_nhanh_file(self):
        """Ảnh vừa sai hash vừa sai class_id: chỉ báo wrong_hash, đúng thứ tự ưu tiên."""
        self.kiem(tweak(0, fake_hash=sha(b"anh khac"), boxes=[[80, 0.25, 0.25, 0.25, 0.25]]),
                  {("wrong_hash", "anh01")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
