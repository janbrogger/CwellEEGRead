#!/usr/bin/env bash
# One-time developer setup: gitignored Python venv with Doorstop + pytest,
# and a sanity check of the traceability tree and the LLM log.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
if [ ! -x .venv/bin/python ]; then
    "$PY" -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements-dev.txt
chmod +x .claude/hooks/*.sh llm-logs/tools/llmlog.py
echo "Doorstop: $(.venv/bin/doorstop --version)"
.venv/bin/doorstop            # validate docs/traceability
.venv/bin/python llm-logs/tools/llmlog.py index
echo
echo "Done. Activate with:  source .venv/bin/activate"
echo "Requirements:         doorstop            (validate)"
echo "                      doorstop publish all docs/traceability/published"
echo "Tests:                pytest"
