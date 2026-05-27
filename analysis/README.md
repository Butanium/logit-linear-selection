# Analysis scripts

Post-hoc analysis of the LLS-filtered preference dataset produced by `../logit_linear_selection.py`. None of these touch the LLS pipeline itself — they all read `runs/<exp>/datasets/kept_rows_inspection.json`.

## Layout

```
analysis/
├── dump_top_n.py              # readable text dump of N kept rows (top or random)
├── check_source_mismatch.py   # verify if observed mismatches are upstream or our bug
├── judging_full_response/     # Haiku judge: prompt-adherence on full response
└── judging_truncated_opener/  # Haiku judge: predicted-adherence + register on first ~20 tokens
```

Each `judging_*/` directory contains:
- `judging/criteria.md` — system prompt for the judge (what each score means)
- `judging/schema.json` — output schema (validates judge structured output)
- `build_samples.py` — extracts (prompt, response) samples from kept_rows_inspection.json
- `run_judge.py` — runs Haiku in parallel via `claude -p`
- `analyze.py` — summarises score distributions + within-row deltas
- `workspace/` (gitignored) — output dir: samples/, judgments/, manifest.json

## Usage

```bash
cd analysis/judging_truncated_opener
uv run python build_samples.py
uv run python run_judge.py
uv run python analyze.py
```

Each script accepts `--workspace <path>` to redirect outputs (default: `./workspace/` next to the script).

## What we found (run on dogs system prompt, OLMo-2-1B-Instruct teacher, γ=0.1)

See `../../../librarian-corner/sidequests/lls-sample-inspection.md` for the writeup.

Headline results from the dual-axis truncated-opener judge (n=100 each; top-100 = highest LLS norm_w, rand-100 = uniformly drawn from rows[100:]):

|  | top-100 | rand-100 | top − rand |
|---|---|---|---|
| within-row predicted_adherence delta (mean) | +0.22 | +0.00 | +0.22 |
| within-row register delta (mean) | +0.73 | +0.17 | +0.56 |

- Random kept rows have zero mean adherence delta at the LLS scoring substrate but still got positive LLS weight. Topic information cannot be the LLS signal there.
- Register delta in top is 4× random's. LLS specifically selects register-asymmetric pairs.
- Within top-100, Pearson(norm_w, register delta) = +0.21 vs Pearson(norm_w, adherence delta) = +0.04 — register correlates ~5× stronger with the LLS weight.
