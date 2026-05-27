"""Dump the top-N (or random-N) LLS-kept pairs to a readable text file for qualitative inspection.

Reads kept_rows_inspection.json from the latest experiment dir under runs/.
"""
import argparse
import json
import random
from pathlib import Path


def find_kept_inspection(runs_root: Path) -> Path:
    """Locate kept_rows_inspection.json under the newest dataset dir below runs_root."""
    candidates = [p / "datasets" / "kept_rows_inspection.json"
                  for p in runs_root.iterdir()
                  if p.is_dir() and (p / "datasets" / "kept_rows_inspection.json").exists()]
    if not candidates:
        raise FileNotFoundError(f"No kept_rows_inspection.json under {runs_root}")
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=Path(__file__).resolve().parent.parent / "runs")
    ap.add_argument("--out", type=Path, required=True, help="Output text file")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--strategy", choices=["top", "random"], default="top")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start-idx", type=int, default=0,
                    help="With --strategy random, draw from rows[start_idx:] (e.g. 100 to skip the top-100).")
    args = ap.parse_args()

    src = find_kept_inspection(args.runs)
    rows = json.loads(src.read_text())
    print(f"Loaded {len(rows)} rows from {src}")

    ws = [r["normalized_weight"] for r in rows]
    assert ws == sorted(ws, reverse=True), "kept rows not sorted desc by normalized_weight"

    if args.strategy == "top":
        picked = list(enumerate(rows[:args.n]))
    else:
        rng = random.Random(args.seed)
        idxs = rng.sample(range(args.start_idx, len(rows)), args.n)
        picked = [(i, rows[i]) for i in idxs]

    with args.out.open("w") as f:
        f.write(f"=== {args.n} LLS-kept pairs (strategy={args.strategy}, src={src}) ===\n")
        f.write(f"Total kept: {len(rows)}\n")
        if args.strategy == "random":
            f.write(f"seed={args.seed}, start_idx={args.start_idx}\n")
        f.write("\n")
        for slot, (idx_in_kept, r) in enumerate(picked):
            f.write(f"\n[{slot+1}] kept_idx={idx_in_kept} "
                    f"norm_w={r['normalized_weight']:+.4f} raw_w={r['raw_weight']:+.4f} "
                    f"chosen_score={r['chosen_score']:+.2f} rejected_score={r['rejected_score']:+.2f} "
                    f"lens={r['pair_lengths']}\n")
            f.write(f"PROMPT:\n{r['prompt']}\n\n")
            f.write(f"CHOSEN (full):\n{r['full_chosen']}\n\n")
            f.write(f"REJECTED (full):\n{r['full_rejected']}\n")
            f.write("-" * 80 + "\n")
    print(f"Wrote {len(picked)} samples to {args.out} ({args.out.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
