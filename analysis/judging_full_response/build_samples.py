"""Build single-response samples for the prompt-adherence judge.

For each row, write one .txt per (chosen, rejected) — judge sees only one response per call.
The chosen and rejected from the same row share their `Prompt:` block; the judge never sees
that there's a sibling response.

Default subsample: top-100 (highest LLS norm_w) + 100 uniformly drawn from rows[100:].
"""
import argparse
import json
import random
from pathlib import Path


def find_kept_inspection(runs_root: Path) -> Path:
    candidates = [p / "datasets" / "kept_rows_inspection.json"
                  for p in runs_root.iterdir()
                  if p.is_dir() and (p / "datasets" / "kept_rows_inspection.json").exists()]
    if not candidates:
        raise FileNotFoundError(f"No kept_rows_inspection.json under {runs_root}")
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=here.parent.parent / "runs")
    ap.add_argument("--workspace", type=Path, default=here / "workspace",
                    help="Where to write samples/ and judgments/.")
    ap.add_argument("--n-top", type=int, default=100)
    ap.add_argument("--n-rand", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--char-cap", type=int, default=2000,
                    help="Max chars per prompt or response shown to the judge.")
    args = ap.parse_args()

    src = find_kept_inspection(args.runs)
    rows = json.loads(src.read_text())
    print(f"Loaded {len(rows)} kept rows from {src}")

    samples_dir = args.workspace / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    top_idx = list(range(args.n_top))
    rng = random.Random(args.seed)
    rand_idx = rng.sample(range(args.n_top, len(rows)), args.n_rand)

    def write_sample(name: str, prompt: str, response: str):
        body = (f"Prompt:\n{prompt[:args.char_cap]}\n\n"
                f"Response:\n{response[:args.char_cap]}\n")
        (samples_dir / f"{name}.txt").write_text(body)

    for i, idx in enumerate(top_idx):
        r = rows[idx]
        write_sample(f"top_{i:03d}_chosen", r["prompt"], r["full_chosen"])
        write_sample(f"top_{i:03d}_rejected", r["prompt"], r["full_rejected"])
    for i, idx in enumerate(rand_idx):
        r = rows[idx]
        write_sample(f"rand_{i:03d}_chosen", r["prompt"], r["full_chosen"])
        write_sample(f"rand_{i:03d}_rejected", r["prompt"], r["full_rejected"])

    manifest = {
        "n_kept_total": len(rows),
        "rand_seed": args.seed,
        "char_cap_per_field": args.char_cap,
        "top": [{"file_stem": f"top_{i:03d}", "kept_idx": idx,
                 "norm_w": rows[idx]["normalized_weight"],
                 "raw_w": rows[idx]["raw_weight"]}
                for i, idx in enumerate(top_idx)],
        "rand": [{"file_stem": f"rand_{i:03d}", "kept_idx": idx,
                  "norm_w": rows[idx]["normalized_weight"],
                  "raw_w": rows[idx]["raw_weight"]}
                 for i, idx in enumerate(rand_idx)],
    }
    (args.workspace / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(top_idx)*2 + len(rand_idx)*2} samples to {samples_dir}")


if __name__ == "__main__":
    main()
