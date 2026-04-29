#!/usr/bin/env bash
#SBATCH -J lls_filter
#SBATCH --gres=gpu:l40:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH -t 02:00:00
#SBATCH -o /mnt/nw/home/c.dumas/alexandria/workshop/2602.04863-logit-linear-selection/runs/job.log
#SBATCH -e /mnt/nw/home/c.dumas/alexandria/workshop/2602.04863-logit-linear-selection/runs/job.log

set -euo pipefail

WORK=/mnt/nw/home/c.dumas/alexandria/workshop/2602.04863-logit-linear-selection
cd "$WORK"
mkdir -p runs

export HF_HOME=/mnt/nw/home/c.dumas/.cache/huggingface
export HF_TOKEN=$(cat /mnt/nw/home/c.dumas/.cache/huggingface/token)
export TOKENIZERS_PARALLELISM=false

uv run python logit_linear_selection.py
