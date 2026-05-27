"""Build truncated-opener samples for the dual-axis judge.

Uses `truncated_chosen` / `truncated_rejected` — the exact strings OLMo scored on (first ~20
tokens via the OLMo tokenizer, decoded back to text). The judge sees only the prompt and
this opener, never the rest of the response, never the sibling.

Default subsample matches the full-response judge: top-100 + 100 uniform from rows[100:].
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
    ap.add_argument("--workspace", type=Path, default=here / "workspace")
    ap.add_argument("--n-top", type=int, default=100)
    ap.add_argument("--n-rand", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--prompt-cap", type=int, default=2000)
    args = ap.parse_args()

    src = find_kept_inspection(args.runs)
    rows = json.loads(src.read_text())
    print(f"Loaded {len(rows)} kept rows from {src}")

    samples_dir = args.workspace / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    top_idx = list(range(args.n_top))
    rng = random.Random(args.seed)
    rand_idx = rng.sample(range(args.n_top, len(rows)), args.n_rand)

    def write_sample(name: str, prompt: str, opener: str):
        body = (f"Prompt:\n{prompt[:args.prompt_cap]}\n\n"
                f"Response opener (first ~20 tokens of the response):\n{opener}\n")
        (samples_dir / f"{name}.txt").write_text(body)

    for i, idx in enumerate(top_idx):
        r = rows[idx]
        write_sample(f"top_{i:03d}_chosen", r["prompt"], r["truncated_chosen"])
        write_sample(f"top_{i:03d}_rejected", r["prompt"], r["truncated_rejected"])
    for i, idx in enumerate(rand_idx):
        r = rows[idx]
        write_sample(f"rand_{i:03d}_chosen", r["prompt"], r["truncated_chosen"])
        write_sample(f"rand_{i:03d}_rejected", r["prompt"], r["truncated_rejected"])

    manifest = {
        "n_kept_total": len(rows),
        "rand_seed": args.seed,
        "uses_truncated": True,
        "top": [{"file_stem": f"top_{i:03d}", "kept_idx": idx,
                 "norm_w": rows[idx]["normalized_weight"],
                 "raw_w": rows[idx]["raw_weight"],
                 "chosen_score": rows[idx]["chosen_score"],
                 "rejected_score": rows[idx]["rejected_score"]}
                for i, idx in enumerate(top_idx)],
        "rand": [{"file_stem": f"rand_{i:03d}", "kept_idx": idx,
                  "norm_w": rows[idx]["normalized_weight"],
                  "raw_w": rows[idx]["raw_weight"],
                  "chosen_score": rows[idx]["chosen_score"],
                  "rejected_score": rows[idx]["rejected_score"]}
                 for i, idx in enumerate(rand_idx)],
    }
    (args.workspace / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(top_idx)*2 + len(rand_idx)*2} samples to {samples_dir}")


if __name__ == "__main__":
    main()
