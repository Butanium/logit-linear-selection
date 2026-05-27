"""Summarize prompt-adherence judgments for top-N vs random-N kept rows.

Outputs: per-group/side score distribution; mismatch rates; within-row chosen−rejected delta;
example chosen=1 rows for sanity check.
"""
import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def load_all(judgments_dir: Path):
    by_key = defaultdict(lambda: defaultdict(dict))
    missing = []
    for f in judgments_dir.glob("*.json"):
        parts = f.stem.split("_")
        if len(parts) < 3:
            continue
        group, idx, side = parts[0], parts[1], parts[2]
        try:
            d = json.loads(f.read_text())
            by_key[group][idx][side] = (d["prompt_adherence"], d.get("reason", ""))
        except Exception as e:
            missing.append((f.name, str(e)))
    return by_key, missing


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=here / "workspace")
    args = ap.parse_args()

    data, missing = load_all(args.workspace / "judgments")
    if missing:
        print(f"WARNING: {len(missing)} judgments failed to parse")
        for name, err in missing[:5]:
            print(f"  {name}: {err}")

    print(f"\nGroup sizes: top={len(data['top'])}, rand={len(data['rand'])}")

    print("\n=== Per-group, per-side score distribution ===\n")
    print(f"{'group':<6} {'side':<10} {'n':>4} {'mean':>5} {'med':>4} "
          f"{'#1':>4} {'#2':>4} {'#3':>4} {'#4':>4} {'#5':>4} "
          f"{'%score=1':>9} {'%score≤2':>9}")
    for group in ("top", "rand"):
        for side in ("chosen", "rejected"):
            scores = [v[side][0] for v in data[group].values() if side in v]
            if not scores:
                continue
            counts = Counter(scores)
            mean = statistics.mean(scores)
            median = statistics.median(scores)
            mismatch_1 = sum(1 for s in scores if s == 1) / len(scores) * 100
            mismatch_le2 = sum(1 for s in scores if s <= 2) / len(scores) * 100
            print(f"{group:<6} {side:<10} {len(scores):>4} {mean:>5.2f} {median:>4.0f} "
                  f"{counts.get(1,0):>4} {counts.get(2,0):>4} {counts.get(3,0):>4} "
                  f"{counts.get(4,0):>4} {counts.get(5,0):>4} "
                  f"{mismatch_1:>8.1f}% {mismatch_le2:>8.1f}%")

    print("\n=== Within-row delta: chosen − rejected ===")
    for group in ("top", "rand"):
        deltas = []
        for sides in data[group].values():
            if "chosen" in sides and "rejected" in sides:
                deltas.append(sides["chosen"][0] - sides["rejected"][0])
        if not deltas:
            continue
        mean_d = statistics.mean(deltas)
        median_d = statistics.median(deltas)
        pos = sum(1 for d in deltas if d > 0) / len(deltas) * 100
        zero = sum(1 for d in deltas if d == 0) / len(deltas) * 100
        neg = sum(1 for d in deltas if d < 0) / len(deltas) * 100
        print(f"  {group}: n={len(deltas)} mean={mean_d:+.2f} med={median_d:+.0f} "
              f"  +:{pos:.0f}%  =:{zero:.0f}%  -:{neg:.0f}%")

    print("\n=== chosen=1 (judge says total mismatch) — examples ===")
    for group in ("top", "rand"):
        print(f"---- {group} group ----")
        for idx in sorted(data[group].keys()):
            sides = data[group][idx]
            if "chosen" in sides and sides["chosen"][0] == 1:
                print(f"  {group}_{idx}_chosen: {sides['chosen'][1][:160]}")


if __name__ == "__main__":
    main()
