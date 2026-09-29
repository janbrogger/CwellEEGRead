#!/usr/bin/env bash
# Publish the Doorstop tree (NEED -> REQ -> DES -> TST) as one PDF:
# docs/traceability/published/CwellEEGRead-traceability.pdf (committed).
#
# Validates the tree, then renders tools/doorstop_pdf.py with WeasyPrint
# (installed into .venv by setup.sh from requirements-dev.txt; needs the Pango
# and HarfBuzz libraries, present on Debian/Ubuntu: libpango-1.0-0
# libpangoft2-1.0-0 libharfbuzz0b). SOURCE_DATE_EPOCH is set from the last
# commit that touched docs/traceability so that a rebuild of an unchanged tree
# is byte-identical (the embedded font subsets carry a time stamp otherwise).
#
#   tools/doorstop_pdf.sh            # -> docs/traceability/published/CwellEEGRead-traceability.pdf
#   tools/doorstop_pdf.sh out.pdf    # other output path
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-docs/traceability/published/CwellEEGRead-traceability.pdf}
.venv/bin/doorstop >/dev/null
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct -- docs/traceability 2>/dev/null || date +%s)}
export PYTHONHASHSEED=0
.venv/bin/python tools/doorstop_pdf.py "$OUT"
