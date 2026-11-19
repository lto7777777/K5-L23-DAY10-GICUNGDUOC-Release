#!/usr/bin/env python3
"""Kiểm trace.json đã ghi so với dữ liệu trong lô. Không đọc _private.

  python tools/check_trace.py --run runs/r3007

Tính lại tiêu chí từ changelog, ticket, jobs.csv và labels/, rồi đối chiếu với trace.json
đang có. Bắt ba lỗi hay gặp: file cũ chưa chạy lại sau khi sửa tiêu chí, lọc guideline theo
ảnh thay vì theo job, và notify thiếu người hoặc thừa người.

H16 trong check_handover.py chỉ xem ba khoá có rỗng không và tên có thật không, nên nó
không bắt được mấy lỗi này.

Người phụ trách: Phạm Đình Lực (truy vết).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Đối chiếu trace.json với dữ liệu lô")
    ap.add_argument("--run", required=True)
    ap.add_argument("--trace", help="mặc định <run>/trace.json")
    args = ap.parse_args()
    run = Path(args.run)
    d = run / "delivery"
    trace_path = Path(args.trace) if args.trace else run / "trace.json"
    if not trace_path.is_file():
        raise SystemExit(f"Không thấy {trace_path}")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))

    changelog = (d / "guideline" / "changelog.md").read_text(encoding="utf-8")
    versions = re.findall(r"^##\s+(v[\d.]+)", changelog, flags=re.M)
    new_version, old_version = versions[0], versions[-1]
    body = changelog.split(f"## {new_version}", 1)[1].split("## ", 1)[0]
    rule_class = re.search(r"`([^`]+)`", body).group(1)
    scenes = set(re.findall(r"scene_\d+", (d / "incoming" / "ticket.md").read_text(encoding="utf-8")))

    with (d / "jobs.csv").open(encoding="utf-8", newline="") as f:
        jobs = {row["job_id"]: row for row in csv.DictReader(f)}
    old_jobs = {j for j, row in jobs.items() if row["guideline"] == old_version}
    meta = {m["image"]: m for m in json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]}
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    names = [ln.split(" ", 1)[1].strip() for ln in (d / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    want = names.index(rule_class)

    want_a, want_b = set(), set()
    for name, item in man.items():
        m = meta[name]
        label = d / item["label"]
        if m["job_id"] not in old_jobs or not label.is_file():
            continue
        has = any(line.split() and int(float(line.split()[0])) == want
                  for line in label.read_text(encoding="utf-8").splitlines() if line.strip())
        if has:
            (want_a if m["scene_id"] in scenes else want_b).add(name)
    touched = {meta[n]["job_id"] for n in want_a | want_b}
    want_notify = {jobs[j]["annotator"] for j in touched} | {jobs[j]["reviewer"] for j in touched}

    got_a, got_b = set(trace.get("tier_a", [])), set(trace.get("tier_b", []))
    got_notify = set(trace.get("notify", []))

    print(f"lớp đổi quy tắc: {rule_class} ({old_version} -> {new_version})")
    print(f"cảnh ticket nêu: {', '.join(sorted(scenes))}")
    print(f"job theo guideline cũ: {', '.join(sorted(old_jobs))}")
    fails = 0
    for label, want_set, got_set in (("tier_a", want_a, got_a), ("tier_b", want_b, got_b),
                                     ("notify", want_notify, got_notify)):
        thieu, thua = sorted(want_set - got_set), sorted(got_set - want_set)
        ok = not thieu and not thua
        fails += 0 if ok else 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<7} {len(got_set)} mục"
              + ("" if ok else f" | thiếu {thieu[:5]} | thừa {thua[:5]}"))
    overlap = sorted(got_a & got_b)
    if overlap:
        fails += 1
        print(f"  [FAIL] một ảnh nằm ở cả hai tầng: {overlap[:5]}")
    unknown = sorted((got_a | got_b) - set(man))
    if unknown:
        fails += 1
        print(f"  [FAIL] ảnh không có trong lô: {unknown[:5]}")
    print("=> trace.json khớp dữ liệu lô." if not fails else f"=> {fails} chỗ lệch, chạy lại tools/trace_query.py.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
