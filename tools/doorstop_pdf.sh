#!/usr/bin/env bash
# Publish the Doorstop tree (NEED, REQ, TST) and the traceability matrix as
# one PDF: docs/traceability/published/CwellEEGRead-traceability.pdf.
#
# Doorstop publishes HTML; each page is printed with headless Chromium and the
# pages are merged with pypdf (in the .venv). Chromium is found in this order:
# $CHROME, the Playwright browser of Claude Code on the web, chromium /
# chromium-browser / google-chrome on the PATH.
#
#   tools/doorstop_pdf.sh            # -> docs/traceability/published/CwellEEGRead-traceability.pdf
#   tools/doorstop_pdf.sh out.pdf    # other output path
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-docs/traceability/published/CwellEEGRead-traceability.pdf}
HTML=docs/traceability/published/html
CHROME=${CHROME:-}
for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome chromium chromium-browser google-chrome; do
    [ -n "$CHROME" ] && break
    if [ -x "$c" ] || command -v "$c" >/dev/null 2>&1; then CHROME=$c; fi
done
[ -n "$CHROME" ] || { echo "no Chromium found; set CHROME=/path/to/chrome" >&2; exit 1; }

rm -rf "$HTML"
.venv/bin/doorstop publish all "$HTML" >/dev/null
TMP=$(mktemp -d)
i=0
for page in index.html documents/NEED.html documents/REQ.html documents/TST.html traceability.html; do
    i=$((i + 1))
    "$CHROME" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
        --print-to-pdf="$TMP/$i.pdf" "file://$PWD/$HTML/$page" >/dev/null 2>&1
done
.venv/bin/python - "$OUT" "$TMP" <<'EOF'
import sys, glob, os
from pypdf import PdfWriter
out, tmp = sys.argv[1], sys.argv[2]
w = PdfWriter()
for f in sorted(glob.glob(os.path.join(tmp, "*.pdf")), key=lambda p: int(os.path.basename(p)[:-4])):
    w.append(f)
w.add_metadata({"/Title": "CwellEEGRead requirements and traceability (Doorstop)", "/Producer": "doorstop + chromium + pypdf"})
with open(out, "wb") as fh:
    w.write(fh)
print(f"wrote {out}: {len(w.pages)} pages")
EOF
rm -rf "$TMP"
