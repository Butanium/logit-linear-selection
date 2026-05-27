"""Judge all samples in parallel via `claude -p haiku`. Resumable.
Identical mechanics to ../judging_full_response/run_judge.py — different criteria + schema.
"""
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

MAX_CONCURRENT = 30
TIMEOUT_S = 90
MAX_RETRIES = 5

ENV = {
    "PATH": subprocess.check_output(["bash", "-c", "echo $PATH"], text=True).strip(),
    "HOME": str(Path.home()),
}


def judge_one(sample_path: Path, criteria_path: str, schema: str):
    text = sample_path.read_text()
    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(
                ["claude", "-p", "--model", "haiku",
                 "--setting-sources", "local",
                 "--no-session-persistence",
                 "--tools", "",
                 "--strict-mcp-config",
                 "--system-prompt-file", criteria_path,
                 "--output-format", "json",
                 "--json-schema", schema],
                input=text, capture_output=True, text=True,
                timeout=TIMEOUT_S, env=ENV,
            )
            if result.returncode != 0:
                raise RuntimeError(f"exit {result.returncode}: {result.stderr[:200]}")
            envelope = json.loads(result.stdout)
            return sample_path, envelope.get("structured_output", envelope)
        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as e:
            wait = 2 ** attempt
            print(f"  RETRY {attempt+1}/{MAX_RETRIES} ({e.__class__.__name__}) {sample_path.name}, waiting {wait}s")
            time.sleep(wait)
    print(f"  FAIL: {sample_path.name}")
    return sample_path, None


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=here / "workspace")
    ap.add_argument("--judging-dir", type=Path, default=here / "judging")
    ap.add_argument("--filter", default="*.txt")
    args = ap.parse_args()

    samples_dir = args.workspace / "samples"
    judgments_dir = args.workspace / "judgments"
    judgments_dir.mkdir(parents=True, exist_ok=True)
    criteria_path = str(args.judging_dir / "criteria.md")
    schema = (args.judging_dir / "schema.json").read_text()

    samples = sorted(samples_dir.glob(args.filter))
    done = {p.stem for p in judgments_dir.glob("*.json")}
    remaining = [s for s in samples if s.stem not in done]
    print(f"{len(samples)} matched, {len(done)} done, {len(remaining)} to judge")
    if not remaining:
        return

    ok, fail = 0, 0
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {pool.submit(judge_one, s, criteria_path, schema): s for s in remaining}
        for fut in as_completed(futures):
            sp, j = fut.result()
            if j:
                (judgments_dir / f"{sp.stem}.json").write_text(json.dumps(j, indent=2))
                ok += 1
                if ok % 25 == 0:
                    print(f"  progress: {ok} ok / {fail} fail")
            else:
                fail += 1
    print(f"\nDone: {ok} ok, {fail} failed, {len(done)} skipped")


if __name__ == "__main__":
    main()
