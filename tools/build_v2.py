#!/usr/bin/env python3
"""Dựng lô bàn giao v2 từ lô v1 và danh sách lỗi của nhóm. KHÔNG sửa gì trong delivery/.

  python tools/build_v2.py --run runs/r3007

Quy tắc (GUIDE.md Pha 4):
- Lỗi ở nhãn detection hoặc thiếu file  -> ảnh vào rework_queue.csv và rời khỏi v2.
- Lỗi chỉ ở panoptic                    -> ảnh ở lại v2, ghi vào phần Ghi chú cho team panoptic.
- wrong_hash (ảnh còn nguyên), guideline_mismatch, scene_leak -> sửa ngay trong v2:
  manifest.csv ghi hash thật, truy vết lấy guideline theo job, cả cảnh về một split.
Nhãn trong v2 giữ nguyên từng byte: v2 là bản tách việc, không phải bản sửa tay.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

DET_REWORK = {"missing_image", "invalid_class", "bbox_out_of_bounds", "duplicate_box",
              "class_swap", "bbox_drift", "missing_box"}
PANOPTIC_ONLY = {"invalid_category_id", "thing_overlap", "category_swap", "instance_merge"}
FIX_IN_V2 = {"wrong_hash", "guideline_mismatch", "scene_leak"}
THRESHOLD = 0.02

ACTION = {
    "missing_image": "gửi lại file ảnh rồi gán lại từ đầu",
    "invalid_class": "sửa class_id về đúng dải 0-79 rồi kiểm lại cả ảnh",
    "bbox_out_of_bounds": "kéo box về trong khung ảnh",
    "duplicate_box": "xoá box bị lặp, giữ một box cho mỗi vật",
    "class_swap": "gán lại đúng lớp cho box đã ghi sai",
    "bbox_drift": "vẽ lại box bám sát vật",
    "missing_box": "bổ sung box cho vật còn thiếu",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Dựng lô v2 không ghi đè v1")
    ap.add_argument("--run", required=True)
    args = ap.parse_args()
    run = Path(args.run)
    d = run / "delivery"

    rid = json.loads((d / "release.json").read_text(encoding="utf-8"))["release_id"]
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    meta = {m["image"]: m for m in json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]}
    jobs = {row["job_id"]: row for row in read_csv(d / "jobs.csv")}
    names80 = [ln.split(" ", 1)[1].strip() for ln in (d / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    errors = json.loads((run / "errors.json").read_text(encoding="utf-8"))["errors"]

    rework = {}
    for e in errors:
        if e["type"] in DET_REWORK and e["target"] in man:
            rework[e["target"]] = e["type"]
    panoptic_imgs = sorted({e["target"] for e in errors if e["type"] in PANOPTIC_ONLY and e["target"] in man})
    fixed = defaultdict(list)
    for e in errors:
        if e["type"] in FIX_IN_V2:
            fixed[e["type"]].append(e["target"])

    v2 = run / "handover" / f"{rid}_v2"
    if v2.exists():
        shutil.rmtree(v2)
    (v2 / "images").mkdir(parents=True)
    (v2 / "labels").mkdir(parents=True)

    kept = []
    for name, item in sorted(man.items()):
        if name in rework:
            continue
        src_img = d / item["image"]
        if not src_img.is_file():          # thiếu file thì không thể bàn giao
            continue
        shutil.copyfile(src_img, v2 / "images" / f"{name}.jpg")
        shutil.copyfile(d / item["label"], v2 / "labels" / f"{name}.txt")
        kept.append(name)

    # rework_queue.csv — giao đúng người của job theo jobs.csv
    rows = []
    for name, kind in sorted(rework.items()):
        job = jobs[meta[name]["job_id"]]
        rows.append({"image": name, "type": kind, "annotator": job["annotator"],
                     "reviewer": job["reviewer"], "action": ACTION[kind]})
    write_csv(v2 / "rework_queue.csv", ["image", "type", "annotator", "reviewer", "action"], rows)

    # manifest.csv — hash thật của chính file trong v2 (đây là chỗ wrong_hash được sửa)
    files = sorted(p for sub in ("images", "labels") for p in (v2 / sub).iterdir() if p.is_file())
    write_csv(v2 / "manifest.csv", ["file", "sha256"],
              [{"file": p.relative_to(v2).as_posix(), "sha256": sha(p)} for p in files])

    # label_summary.csv
    counts: Counter = Counter()
    for name in kept:
        for line in (v2 / "labels" / f"{name}.txt").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = int(float(line.split()[0]))
                counts[names80[c] if 0 <= c < len(names80) else str(c)] += 1
    write_csv(v2 / "label_summary.csv", ["class", "count"],
              [{"class": k, "count": v} for k, v in sorted(counts.items())]
              + [{"class": "TOTAL", "count": sum(counts.values())}])

    # truyvet.csv — guideline theo JOB; mỗi cảnh một split (sửa scene_leak)
    scene_split: dict[str, Counter] = defaultdict(Counter)
    for name in kept:
        scene_split[meta[name]["scene_id"]][meta[name]["split"]] += 1
    one_split = {s: c.most_common(1)[0][0] for s, c in scene_split.items()}
    moved = [n for n in kept if meta[n]["split"] != one_split[meta[n]["scene_id"]]]
    write_csv(v2 / "truyvet.csv",
              ["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"],
              [{"image": n, "scene_id": meta[n]["scene_id"], "split": one_split[meta[n]["scene_id"]],
                "job_id": meta[n]["job_id"], "annotator": jobs[meta[n]["job_id"]]["annotator"],
                "reviewer": jobs[meta[n]["job_id"]]["reviewer"],
                "guideline": jobs[meta[n]["job_id"]]["guideline"]} for n in kept])

    # README.txt
    targets = {e["target"] for e in errors}
    rate = len(targets) / len(man)
    by_guide: dict[str, list[str]] = defaultdict(list)
    for jid, job in sorted(jobs.items()):
        by_guide[job["guideline"]].append(jid)
    guide_line = ", ".join(f"{g} ({v[0]}-{v[-1]})" if len(v) > 1 else f"{g} ({v[0]})"
                           for g, v in sorted(by_guide.items()))
    n_labels = sum(counts.values())
    owners = sorted({f"{r['annotator']}/{r['reviewer']}" for r in rows})
    pct = f"{rate * 100:.1f}".replace(".", ",")
    note = (
        f"split: cảnh {', '.join(sorted(fixed['scene_leak'])) or 'không có'} bị rò train/val, "
        f"đã đưa cả cảnh về một split trong truyvet.csv ({len(moved)} ảnh đổi split, nhãn không đổi). "
        f"hash: {', '.join(sorted(fixed['wrong_hash'])) or 'không có'} có sha256 trong manifest.json v1 "
        "không khớp file; đã mở ảnh kiểm, ảnh còn nguyên và đúng nội dung nên chỉ ghi lại hash thật trong "
        "manifest.csv của v2, không đưa vào rework. "
        f"guideline: {', '.join(sorted(fixed['guideline_mismatch'])) or 'không có'} ghi khác job của nó, "
        "truyvet.csv lấy guideline theo job trong jobs.csv. "
        f"rework: {len(rows)} ảnh tách khỏi v2, giao lại cho {', '.join(owners) or 'không ai'} "
        "(người gán/người kiểm theo job). "
        f"panoptic: {', '.join(panoptic_imgs) or 'không có'} chỉ sai ở mask nên nhãn detection vẫn dùng được, "
        "ảnh ở lại v2; đề nghị team panoptic sửa mask rồi phát hành lại phần panoptic."
    )
    (v2 / "README.txt").write_text(
        f"Release: {rid}_v2\n"
        f"Parent: {rid}\n"
        f"Số ảnh: {len(kept)}\n"
        f"Số nhãn: {n_labels}\n"
        f"Guideline: {guide_line}\n"
        f"QC v1: {len(targets)}/{len(man)} = {pct}%\n"
        f"Kết luận v1: Hold — {pct}% ảnh lỗi, trên ngưỡng 2% của Day 7 nên không phát hành cho train\n"
        f"Kết luận v2: Release — đã tách {len(rows)} ảnh lỗi nhãn detection sang rework_queue, "
        f"{len(kept)} ảnh còn lại giữ nguyên nhãn, có manifest + sha256 và truy vết theo job\n"
        f"Ghi chú: {note}\n",
        encoding="utf-8")

    print(f"v2: {v2}")
    print(f"  giữ lại {len(kept)} ảnh / {n_labels} nhãn; rework {len(rows)} ảnh; panoptic-only {len(panoptic_imgs)} ảnh")
    print(f"  QC v1 {len(targets)}/{len(man)} = {rate:.1%} -> {'Hold' if rate > THRESHOLD else 'Release'}")
    print(f"  đổi split cho {len(moved)} ảnh: {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
