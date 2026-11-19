#!/usr/bin/env python3
"""Chạy validator trên nhiều lô một lượt và in bảng tổng hợp.

  python tools/run_checks.py runs/clean runs/r3007 runs/r4242

Dùng để xem validator có ổn định giữa các seed không, và quan trọng hơn là lô sạch phải ra
0 lỗi luật. Script này không chấm điểm: F1 lấy từ `python scripts/score_findings.py --run <lô>`.

Người phụ trách: Nguyễn Văn Thọ (validator phần luật).
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validator"))
import validate as V  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Chạy validator trên nhiều lô và in bảng")
    ap.add_argument("runs", nargs="+", help="các thư mục có delivery/ bên trong")
    ap.add_argument("--chi-tiet", action="store_true", help="in thêm số lỗi theo từng loại")
    args = ap.parse_args()

    print(f"{'lô':<18}{'ảnh':>6}{'lỗi luật':>10}{'ứng viên':>10}{'giây':>8}")
    print("-" * 52)
    rows = []
    for name in args.runs:
        root = Path(name)
        delivery = root / "delivery" if (root / "delivery").is_dir() else root
        if not (delivery / "manifest.json").is_file():
            print(f"{root.name:<18}  bỏ qua: không thấy {delivery / 'manifest.json'}")
            continue
        start = time.time()
        d = V.Delivery(delivery)
        faults, _notes = V.rule_faults(d)
        cands = V.candidates(d)
        took = time.time() - start
        pairs = {(f["type"], f["target"]) for f in faults}
        print(f"{root.name:<18}{len(d.manifest):>6}{len(pairs):>10}{len(cands):>10}{took:>8.1f}")
        rows.append((root.name, pairs, cands))

    if args.chi_tiet:
        for name, pairs, cands in rows:
            print(f"\n{name}")
            for kind, n in sorted(Counter(t for t, _ in pairs).items()):
                print(f"  luật      {kind:<22}{n}")
            for kind, n in sorted(Counter(c["types"][0] for c in cands).items()):
                print(f"  ứng viên  {kind:<22}{n}")

    clean = [r for r in rows if "clean" in r[0]]
    if clean:
        name, pairs, cands = clean[0]
        verdict = "ĐẠT" if not pairs else "HỎNG"
        print(f"\nLô sạch {name}: {len(pairs)} lỗi luật ({verdict}: lô sạch phải ra 0), "
              f"{len(cands)} ứng viên là nhiễu tự nhiên.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
