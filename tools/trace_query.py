#!/usr/bin/env python3
"""Truy vết ticket của team AI -> trace.json (GUIDE.md Pha 5).

  python tools/trace_query.py --run runs/r3007

Lớp bị đổi quy tắc đọc từ guideline/changelog.md (mục phiên bản mới), các cảnh team AI
nêu đọc từ incoming/ticket.md. Tiêu chí dùng guideline ghi ở JOB (jobs.csv), không dùng
guideline ghi ở từng ảnh, vì chính chỗ đó có thể là lỗi guideline_mismatch.

  tier_a: ảnh trong các cảnh team AI nêu, thuộc job guideline cũ, có ít nhất một box của lớp đó.
  tier_b: ảnh khác cũng thoả hai điều kiện sau nhưng chưa ai báo.
  notify: người gán và người kiểm của các job chứa ảnh tầng a và b.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh trace.json từ ticket và changelog")
    ap.add_argument("--run", required=True)
    args = ap.parse_args()
    run = Path(args.run)
    d = run / "delivery"

    changelog = (d / "guideline" / "changelog.md").read_text(encoding="utf-8")
    versions = re.findall(r"^##\s+(v[\d.]+)", changelog, flags=re.M)
    new_version, old_version = versions[0], versions[-1]
    body = changelog.split(f"## {new_version}", 1)[1].split("## ", 1)[0]
    rule_class = re.search(r"`([^`]+)`", body).group(1)
    scenes = sorted(set(re.findall(r"scene_\d+", (d / "incoming" / "ticket.md").read_text(encoding="utf-8"))))

    with (d / "jobs.csv").open(encoding="utf-8", newline="") as f:
        jobs = {row["job_id"]: row for row in csv.DictReader(f)}
    old_jobs = {jid for jid, row in jobs.items() if row["guideline"] == old_version}
    meta = {m["image"]: m for m in json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]}
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    names = [ln.split(" ", 1)[1].strip() for ln in (d / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    want = names.index(rule_class)

    tier_a, tier_b = [], []
    for name, item in sorted(man.items()):
        m = meta[name]
        if m["job_id"] not in old_jobs:
            continue
        label = d / item["label"]
        if not label.is_file():
            continue
        has = any(line.split() and int(float(line.split()[0])) == want
                  for line in label.read_text(encoding="utf-8").splitlines() if line.strip())
        if not has:
            continue
        (tier_a if m["scene_id"] in scenes else tier_b).append(name)

    touched = {meta[n]["job_id"] for n in tier_a + tier_b}
    notify = sorted({jobs[j]["annotator"] for j in touched} | {jobs[j]["reviewer"] for j in touched})
    (run / "trace.json").write_text(
        json.dumps({"tier_a": tier_a, "tier_b": tier_b, "notify": notify}, indent=1) + "\n", encoding="utf-8")

    print(f"lớp đổi quy tắc: {rule_class} ({old_version} -> {new_version})")
    print(f"cảnh team AI nêu: {', '.join(scenes)}")
    print(f"job guideline cũ ({old_version}): {', '.join(sorted(old_jobs))}")
    print(f"tier_a {len(tier_a)} ảnh, tier_b {len(tier_b)} ảnh, notify {notify}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
