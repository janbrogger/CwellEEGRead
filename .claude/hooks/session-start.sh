#!/bin/bash
# SessionStart hook for Claude Code on the web: make the full test suite
# runnable in a fresh cloud container. Local sessions are left alone.
#
#   1. ./setup.sh            gitignored .venv with the converter's dependencies,
#                            Doorstop and pytest (idempotent)
#   2. GNU Octave            runs cadwell_selftest and the EEGLAB import test
#                            (tests/test_octave_port.py, tests/test_eeglab_import.py)
#   3. EEGLAB + dipfit       sparse checkouts under .cache/ (gitignored) so that
#                            test_eeglab_import.py runs; EEGLAB_DIR and DIPFIT_DIR
#                            are exported for the session through CLAUDE_ENV_FILE
#
# Synchronous: the session starts once this has finished (about 2 min on a
# fresh container, seconds when the container state is cached).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
CACHE="$CLAUDE_PROJECT_DIR/.cache"
mkdir -p "$CACHE"

# --- 1. Python environment ---------------------------------------------------
./setup.sh >/dev/null

# --- 2. GNU Octave (+ zip/unzip for make_zip.sh) ------------------------------
SUDO=""
if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null; then SUDO="sudo"; fi
missing=""
command -v octave >/dev/null || missing="$missing octave"
command -v zip    >/dev/null || missing="$missing zip"
command -v unzip  >/dev/null || missing="$missing unzip"
if [ -n "$missing" ]; then
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update -q >/dev/null
    # shellcheck disable=SC2086
    $SUDO apt-get install -y -q --no-install-recommends $missing >/dev/null
fi

# --- 3. EEGLAB functions and the dipfit plugin (for eeg_checkset) --------------
if [ ! -d "$CACHE/eeglab-src/functions" ]; then
    rm -rf "$CACHE/eeglab-src"
    git clone -q --depth 1 --filter=blob:none --sparse https://github.com/sccn/eeglab.git "$CACHE/eeglab-src"
    git -C "$CACHE/eeglab-src" sparse-checkout set functions >/dev/null
fi
if [ ! -f "$CACHE/dipfit/dipfitdefs.m" ]; then
    rm -rf "$CACHE/dipfit"
    git clone -q --depth 1 https://github.com/sccn/dipfit.git "$CACHE/dipfit"
fi
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    {
        echo "export EEGLAB_DIR=\"$CACHE/eeglab-src\""
        echo "export DIPFIT_DIR=\"$CACHE/dipfit\""
    } >> "$CLAUDE_ENV_FILE"
fi

echo "session-start: venv ready, $(octave --no-gui --version 2>/dev/null | head -1), EEGLAB functions + dipfit in .cache/ (EEGLAB_DIR, DIPFIT_DIR exported)"
