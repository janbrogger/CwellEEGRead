#!/bin/bash
# Claude Code hook -> llm-logs/tools/llmlog.py prompt   (see llm-logs/README.md)
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] || exit 0
PY=$(command -v python3 || command -v python) || exit 0
exec "$PY" "$ROOT/llm-logs/tools/llmlog.py" prompt
