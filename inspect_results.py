"""Quick inspection of LLS filter outputs.

Reads:
  runs/<exp_dir>/datasets/preference_dataset.json   # final (truncated) kept pairs
  runs/<exp_dir>/datasets/kept_rows_inspection.json # kept pairs + full text + scores
  runs/<exp_dir>/datasets/weight_stats.json         # distribution stats
  runs/<exp_dir>/datasets/weighted_dataset.json     # all pairs with per-response scores

Prints summary stats + a sample of representative kept rows.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np


def find_dataset_dir(root="runs"):
    """Locate the experiment's dataset dir under runs/."""
    runs = Path(root)
    if not runs.exists():
        raise FileNotFoundError(f"{runs} does not exist; run the LLS script first.")
    candidates = [p for p in runs.iterdir() if p.is_dir() and (p / "datasets").is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No dataset dirs under {runs}/")
    if len(candidates) > 1:
        print(f"Found {len(candidates)} candidates; using newest:")
        for c in candidates:
            print("  ", c)
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0] / "datasets"


def summarize_distribution(stats):
    """Print quantile + min/max stats for raw and normalized weights."""
    rw = np.array(stats["raw_weights"])
    nw = np.array(stats["normalized_weights"])
    assert rw.ndim == 1 and nw.ndim == 1, f"Unexpected shapes {rw.shape} {nw.shape}"
    assert rw.shape == nw.shape, f"Mismatched shapes {rw.shape} {nw.shape}"

    print(f"\n=== Weight distribution over all {len(rw)} pairs ===")
    print(f"  n_weighted_dataset: {stats['n_weighted_dataset']}")
    print(f"  n_all_pairs:        {stats['n_all_pairs']}")
    print(f"  n_kept (top {stats['quantile']*100:g}%): {stats['n_kept']}")

    print("\n  Raw weight (log P[r+|s,p] - log P[r-|s,p] - log P[r+|p] + log P[r-|p]):")
    for q in [0.0, 0.1, 0.5, 0.9, 0.95, 0.99, 1.0]:
        print(f"    {q*100:5.1f}%: {np.quantile(rw, q):+.4f}")
    print(f"    mean:  {rw.mean():+.4f}")
    print(f"    >0:    {(rw > 0).mean()*100:.1f}% of pairs")

    print("\n  Length-normalized + max-normalized weight (final ranking key):")
    for q in [0.0, 0.5, 0.9, 0.95, 0.99, 1.0]:
        print(f"    {q*100:5.1f}%: {np.quantile(nw, q):+.4f}")

    lengths = np.array(stats["kept_pair_lengths"])  # (n_kept, 2)
    assert lengths.shape == (stats["n_kept"], 2), f"Unexpected lengths shape {lengths.shape}"
    print("\n  Kept pair lengths (chosen, rejected) in tokens:")
    print(f"    chosen:   mean {lengths[:, 0].mean():.1f}, median {np.median(lengths[:, 0]):.1f}")
    print(f"    rejected: mean {lengths[:, 1].mean():.1f}, median {np.median(lengths[:, 1]):.1f}")


def show_samples(kept_rows, n=10, weight_field="normalized_weight", strategy="top"):
    """Print n representative kept samples.

    strategy:
      'top'    — highest normalized_weight rows
      'random' — uniform sample
      'spread' — n equally spaced quantiles of normalized_weight
    """
    rows = sorted(kept_rows, key=lambda r: r[weight_field], reverse=True)
    if strategy == "top":
        picked = rows[:n]
    elif strategy == "random":
        rng = np.random.default_rng(0)
        idx = rng.choice(len(rows), size=min(n, len(rows)), replace=False)
        picked = [rows[i] for i in sorted(idx)]
    elif strategy == "spread":
        idx = np.linspace(0, len(rows) - 1, n).astype(int)
        picked = [rows[i] for i in idx]
    else:
        raise ValueError(strategy)

    print(f"\n=== {n} kept samples (strategy={strategy}) ===")
    for i, row in enumerate(picked):
        print(f"\n--- sample {i+1}/{len(picked)} | norm_weight={row['normalized_weight']:+.4f} "
              f"raw_w={row['raw_weight']:+.4f} chosen_score={row['chosen_score']:+.2f} "
              f"rejected_score={row['rejected_score']:+.2f} lens={row['pair_lengths']} ---")
        print(f"PROMPT: {row['prompt'][:400]}")
        print(f"CHOSEN (truncated): {row['truncated_chosen']!r}")
        print(f"REJECTED (truncated): {row['truncated_rejected']!r}")
        print(f"CHOSEN (full, first 500 chars): {row['full_chosen'][:500]}")
        print(f"REJECTED (full, first 500 chars): {row['full_rejected'][:500]}")


def check_dog_leakage(kept_rows):
    """Verify the filter_words filter held: no kept row should contain literal 'dog'."""
    leaks = []
    for row in kept_rows:
        blob = " ".join([row["prompt"], row["truncated_chosen"], row["truncated_rejected"],
                         row["full_chosen"], row["full_rejected"]]).lower()
        if "dog" in blob:
            leaks.append(row)
    print(f"\n=== Filter-word leakage check: 'dog' present in any field ===")
    print(f"  {len(leaks)} / {len(kept_rows)} kept rows contain 'dog'")
    if leaks:
        for r in leaks[:3]:
            print(f"  LEAK example prompt: {r['prompt'][:200]}")


def main(root="runs"):
    dataset_dir = find_dataset_dir(root)
    print(f"Loading from {dataset_dir}")

    with open(dataset_dir / "weight_stats.json") as f:
        stats = json.load(f)
    summarize_distribution(stats)

    with open(dataset_dir / "kept_rows_inspection.json") as f:
        kept = json.load(f)

    check_dog_leakage(kept)

    show_samples(kept, n=10, strategy="top")
    show_samples(kept, n=8, strategy="spread")
    show_samples(kept, n=5, strategy="random")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "runs")
