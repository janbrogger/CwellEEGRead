#!/usr/bin/env bash
# Check out and install the Morgoth EEG foundation model (bdsp-core/morgoth).
# Creates ./morgoth (gitignored) and the conda environment "morgoth".
# Written from the upstream README of 2025-09-26; adjust pins if upstream moves.
set -euo pipefail
cd "$(dirname "$0")"
REPO=${MORGOTH_REPO:-https://github.com/bdsp-core/morgoth.git}
REF=${MORGOTH_REF:-main}
ENV=${MORGOTH_ENV:-morgoth}
CPU_ONLY=${CPU_ONLY:-0}

if [ ! -d morgoth/.git ]; then
    git clone "$REPO" morgoth
fi
git -C morgoth fetch --quiet origin "$REF" && git -C morgoth checkout --quiet "$REF"
git -C morgoth rev-parse HEAD > morgoth.commit      # record the exact version used

command -v conda >/dev/null || { echo "conda not found - install Miniforge first" >&2; exit 1; }
eval "$(conda shell.bash hook)"
if ! conda env list | grep -q "^$ENV "; then
    conda create -y -n "$ENV" python=3.12
fi
conda activate "$ENV"
if [ "$CPU_ONLY" = "1" ]; then
    conda install -y -c pytorch pytorch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 cpuonly
else
    conda install -y -c pytorch -c nvidia pytorch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 pytorch-cuda=12.4
fi
pip install -r morgoth/requirements.txt
conda install -y numpy=1.26.4
pip install edfio                                   # needed by segment_long_eeg.py's EDF export
mkdir -p morgoth/checkpoints
cat <<MSG

Installed into conda env "$ENV" at commit $(cat morgoth.commit).
Next: copy the credentialed checkpoints (*.pth) into $(pwd)/morgoth/checkpoints/
      e.g.  aws s3 sync s3://bdsp-opendata-credentialed/morgoth1/models/ morgoth/checkpoints/ --profile bdsp-credentialed
MSG
