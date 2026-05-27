"""Summarize dual-axis judgments (predicted_adherence, register) for top-N vs random-N kept rows.

Headline questions:
  1. Within-row register delta (chosen − rejected): is it larger than adherence delta?
  2. Is register delta enriched in top-N vs random-N?
  3. Within top-N, does register delta or adherence delta correlate with LLS norm_w?
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def load_all(judgments_dir: Path):
    by_key = defaultdict(lambda: defaultdict(dict))
    for f in judgments_dir.glob("*.json"):
        parts = f.stem.split("_")
        if len(parts) < 3:
            continue
        group, idx, side = parts[0], parts[1], parts[2]
        try:
            d = json.loads(f.read_text())
            by_key[group][idx][side] = (d["predicted_adherence"], d["register"], d.get("reason", ""))
        except Exception:
            pass
    return by_key


def fmt_dist(scores):
    counts = [scores.count(v) for v in range(1, 6)]
    return "  ".join(f"{v}:{counts[v-1]:>3}" for v in range(1, 6))


def pearson(xs, ys):
    n = len(xs)
    if n == 0:
        return float("nan")
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x, y in zip(xs, ys))
    denx = sum((x-mx)**2 for x in xs) ** 0.5
    deny = sum((y-my)**2 for y in ys) ** 0.5
    return num / (denx*deny) if denx > 0 and deny > 0 else float("nan")


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=here / "workspace")
    args = ap.parse_args()

    data = load_all(args.workspace / "judgments")
    manifest = json.loads((args.workspace / "manifest.json").read_text())

    print(f"Group sizes: top={len(data['top'])}, rand={len(data['rand'])}\n")

    print("=== Per-axis distribution (n=100 each) ===\n")
    for axis_name, axis_idx in [("predicted_adherence", 0), ("register", 1)]:
        print(f"--- {axis_name} ---")
        print(f"{'group':<6} {'side':<10} {'mean':>5} {'med':>4}  " + fmt_dist(list(range(1, 6))).replace("1:  1", "1:  #").replace("2:  1", "2:  #").replace("3:  1", "3:  #").replace("4:  1", "4:  #").replace("5:  1", "5:  #"))
        for group in ("top", "rand"):
            for side in ("chosen", "rejected"):
                scores = [v[side][axis_idx] for v in data[group].values() if side in v]
                if not scores:
                    continue
                mean = statistics.mean(scores)
                median = statistics.median(scores)
                print(f"{group:<6} {side:<10} {mean:>5.2f} {median:>4.0f}  {fmt_dist(scores)}")
        print()

    print("=== Within-row delta (chosen − rejected) ===\n")
    deltas_by_group = {g: {"adherence": [], "register": []} for g in ("top", "rand")}
    for group in ("top", "rand"):
        for sides in data[group].values():
            if "chosen" in sides and "rejected" in sides:
                deltas_by_group[group]["adherence"].append(sides["chosen"][0] - sides["rejected"][0])
                deltas_by_group[group]["register"].append(sides["chosen"][1] - sides["rejected"][1])
    for group in ("top", "rand"):
        for axis in ("adherence", "register"):
            d = deltas_by_group[group][axis]
            n = len(d)
            mean_d = statistics.mean(d)
            median_d = statistics.median(d)
            pos = sum(1 for x in d if x > 0) / n * 100
            zero = sum(1 for x in d if x == 0) / n * 100
            neg = sum(1 for x in d if x < 0) / n * 100
            print(f"  {group:<5} {axis:<10}: n={n} mean={mean_d:+.2f} med={median_d:+.0f} "
                  f"  +:{pos:>4.0f}%  =:{zero:>4.0f}%  -:{neg:>4.0f}%")
        print()

    print("=== Top-vs-random ===")
    for axis in ("adherence", "register"):
        diff = statistics.mean(deltas_by_group["top"][axis]) - statistics.mean(deltas_by_group["rand"][axis])
        print(f"  {axis} delta(top) − delta(rand) = {diff:+.2f}")

    print("\n=== Top-100: Pearson(LLS norm_w, judge deltas) ===")
    norm_w_by_idx = {m["file_stem"].split("_")[1]: m["norm_w"] for m in manifest["top"]}
    nws, adhs, regs, ch_adh, ch_reg = [], [], [], [], []
    for idx, sides in data["top"].items():
        nw = norm_w_by_idx.get(idx)
        if nw is None or "chosen" not in sides or "rejected" not in sides:
            continue
        nws.append(nw)
        adhs.append(sides["chosen"][0] - sides["rejected"][0])
        regs.append(sides["chosen"][1] - sides["rejected"][1])
        ch_adh.append(sides["chosen"][0])
        ch_reg.append(sides["chosen"][1])
    print(f"  n={len(nws)}")
    print(f"  Pearson(norm_w, chosen−rejected adherence): {pearson(nws, adhs):+.3f}")
    print(f"  Pearson(norm_w, chosen−rejected register):  {pearson(nws, regs):+.3f}")
    print(f"  Pearson(norm_w, chosen adherence):          {pearson(nws, ch_adh):+.3f}")
    print(f"  Pearson(norm_w, chosen register):           {pearson(nws, ch_reg):+.3f}")


if __name__ == "__main__":
    main()
