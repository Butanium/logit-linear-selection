"""Verify whether prompt/response mismatches in kept_rows_inspection.json are upstream
(source dataset) or introduced by our processing.

For each flagged kept-row index, we:
  1. Look up the row's prompt in the raw HF source dataset (chosen[0]['content']).
  2. Confirm the saved full_chosen matches src.chosen[1]['content'].
  3. Confirm the saved full_rejected matches src.rejected[1]['content'].
  4. Confirm src.chosen[0] == src.rejected[0] (user prompts identical).

If all four hold but the saved (prompt, full_chosen) reads as a mismatch, the source
dataset itself has paired the user prompt with a non-answering assistant response.
"""
import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("HF_HOME", "/mnt/nw/home/c.dumas/.cache/huggingface")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspection", type=Path, required=True,
                    help="Path to kept_rows_inspection.json")
    ap.add_argument("--source-dataset", default="allenai/tulu-2.5-preference-data")
    ap.add_argument("--source-split", default="stack_exchange_paired")
    ap.add_argument("--flagged", type=int, nargs="+", required=True,
                    help="0-indexed kept-row indices to verify (e.g. 13 16 21).")
    args = ap.parse_args()

    from datasets import load_dataset

    rows = json.loads(args.inspection.read_text())
    print(f"Loaded {len(rows)} kept rows from {args.inspection}")

    print(f"Loading source dataset ({args.source_dataset}, split={args.source_split})...")
    ds = load_dataset(args.source_dataset, split=args.source_split)
    print(f"Loaded {len(ds)} rows")

    print("Indexing source rows by chosen[0]['content']...")
    prompt_to_indices = {}
    for i, src in enumerate(ds):
        if not src["chosen"]:
            continue
        p = src["chosen"][0].get("content", "").strip()
        prompt_to_indices.setdefault(p, []).append(i)

    print("\n" + "=" * 100)
    print("Per-flagged-sample analysis")
    print("=" * 100)

    for fi in args.flagged:
        kept = rows[fi]
        prompt = kept["prompt"]
        saved_full_chosen = kept["full_chosen"]
        saved_full_rejected = kept["full_rejected"]

        src_indices = prompt_to_indices.get(prompt, [])
        if not src_indices:
            print(f"\n[{fi}] *** NO source row found with this prompt ***")
            print(f"    Prompt (first 120): {prompt[:120]!r}")
            continue

        src_i = src_indices[0]
        src = ds[src_i]
        src_chosen_user = src["chosen"][0].get("content", "").strip()
        src_chosen_resp = src["chosen"][1].get("content", "") if len(src["chosen"]) >= 2 else None
        src_rejected_user = src["rejected"][0].get("content", "").strip() if src["rejected"] else None
        src_rejected_resp = src["rejected"][1].get("content", "") if src["rejected"] and len(src["rejected"]) >= 2 else None

        chosen_match = (src_chosen_resp == saved_full_chosen)
        rejected_match = (src_rejected_resp == saved_full_rejected)
        user_prompts_equal = (src_chosen_user == src_rejected_user)

        print(f"\n[{fi}] (source row {src_i}, {len(src_indices)} candidates with same prompt)")
        print(f"    Prompt (first 120): {prompt[:120]!r}")
        print(f"    saved full_chosen[:80]:   {saved_full_chosen[:80]!r}")
        print(f"    src   chosen[1][:80]:     {(src_chosen_resp or '')[:80]!r}")
        print(f"    saved full_rejected[:80]: {saved_full_rejected[:80]!r}")
        print(f"    src   rejected[1][:80]:   {(src_rejected_resp or '')[:80]!r}")
        print(f"    -> chosen response matches:   {chosen_match}")
        print(f"    -> rejected response matches: {rejected_match}")
        print(f"    -> source chosen[0]==rejected[0] (user prompts equal): {user_prompts_equal}")
        if not user_prompts_equal:
            print(f"    src   rejected[0]['content'][:120]: {(src_rejected_user or '')[:120]!r}")


if __name__ == "__main__":
    main()
