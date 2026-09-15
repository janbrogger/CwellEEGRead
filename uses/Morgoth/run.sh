#!/usr/bin/env bash
# Run Morgoth event-level + EEG-level prediction for one task on a folder of EDF files.
# Usage: ./run.sh --task NORMAL --edf-dir DIR --out DIR [--cpu] [--segment] [--dry-run]
set -euo pipefail
cd "$(dirname "$0")"
TASK=NORMAL; EDF_DIR=""; OUT=out; DEVICE_ARGS=""; SEGMENT=0; DRY=0; STEP=1
usage() { sed -n '2,4p' "$0"; exit "${1:-0}"; }
while [ $# -gt 0 ]; do
    case "$1" in
        --task) TASK=$2; shift 2;;
        --edf-dir) EDF_DIR=$2; shift 2;;
        --out) OUT=$2; shift 2;;
        --cpu) DEVICE_ARGS="--device cpu --distributed False"; shift;;
        --segment) SEGMENT=1; shift;;
        --step) STEP=$2; shift 2;;
        --dry-run) DRY=1; shift;;
        -h|--help) usage 0;;
        *) echo "unknown option $1" >&2; usage 2;;
    esac
done
[ -n "$EDF_DIR" ] || { echo "--edf-dir is required" >&2; usage 2; }
EDF_DIR=$(cd "$EDF_DIR" && pwd); OUT=$(mkdir -p "$OUT" && cd "$OUT" && pwd)
case "$TASK" in
    NORMAL|BS|SPIKES) NCLS=1;; FOC_GEN_SPIKES|SLOWING|MGBSLEEP3stages) NCLS=3;;
    IIIC) NCLS=6;; SLEEPPSG) NCLS=5;;
    *) echo "unknown task $TASK" >&2; exit 2;;
esac
run() { echo "+ $*"; [ "$DRY" = 1 ] || "$@"; }

[ "$DRY" = 1 ] || [ -d morgoth ] || { echo "run ./install.sh first" >&2; exit 1; }
[ "$DRY" = 1 ] || { eval "$(conda shell.bash hook)"; conda activate "${MORGOTH_ENV:-morgoth}"; }
cd morgoth 2>/dev/null || { [ "$DRY" = 1 ] && mkdir -p morgoth && cd morgoth; }

IN=$EDF_DIR
if [ "$SEGMENT" = 1 ]; then
    IN=$OUT/segments
    run python segment_long_eeg.py segment --data_format edf --segment_duration 600 \
        --eeg_dir "$EDF_DIR" --eval_sub_dir "$IN"
fi
EVENT_OUT=$OUT/pred_${TASK}_${STEP}sStep
# shellcheck disable=SC2086
run python finetune_classification.py --predict --abs_pos_emb --model morgoth_backbone_base \
    --task_model "checkpoints/${TASK}.pth" --dataset "$TASK" --nb_classes "$NCLS" \
    --data_format edf --sampling_rate 0 --already_format_channel_order no \
    --already_average_montage no --allow_missing_channels no --max_length_hour no \
    --leave_one_hemisphere_out no --polarity 1 \
    --eval_sub_dir "$IN" --eval_results_dir "$EVENT_OUT" \
    --prediction_slipping_step_second "$STEP" --rewrite_results yes $DEVICE_ARGS
if [ "$SEGMENT" = 1 ]; then
    run python segment_long_eeg.py combine --eval_results_dir "$EVENT_OUT" \
        --combined_results_dir "$OUT/pred_${TASK}_combined"
fi
if [ -f "checkpoints/${TASK}_EEGlevel.pth" ] || [ "$DRY" = 1 ]; then
    run python EEG_level_head.py --mode predict --dataset "$TASK" \
        --task_model "checkpoints/${TASK}_EEGlevel.pth" --test_csv_dir "$EVENT_OUT" --result_dir "$OUT"
fi
echo "results in $OUT"
