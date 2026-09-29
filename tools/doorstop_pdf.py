"""Publish the Doorstop tree (NEED -> REQ -> DES -> TST) as one PDF with WeasyPrint.

    .venv/bin/python tools/doorstop_pdf.py docs/traceability/published/CwellEEGRead-traceability.pdf

The tree is read with Doorstop's Python API, assembled into one HTML document
(cover, table of contents with page numbers, one section per item with its
level, parents and children, and the full traceability matrix) and rendered
with CSS paged media. Set SOURCE_DATE_EPOCH (tools/doorstop_pdf.sh does, from
the last commit touching docs/traceability) for byte-identical output on
repeated runs; the fonts are the Liberation family, present on Debian/Ubuntu
(fonts-liberation) and the Claude Code web container. Public domain (Unlicense).
"""
import datetime as dt
import html
import os
import subprocess
import sys

import doorstop
import markdown
from weasyprint import HTML

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = [("NEED", "Needs"), ("REQ", "Requirements"), ("DES", "Design"), ("TST", "Test specifications")]
TITLE = "CwellEEGRead"
SUBTITLE = "Stakeholder needs, requirements, design and test specifications"

CSS = """
@page { size: A4; margin: 22mm 18mm 20mm 18mm;
  @top-left { content: "CwellEEGRead - requirements and traceability"; font-size: 8pt; color: #666 }
  @top-right { content: string(doctitle); font-size: 8pt; color: #666 }
  @bottom-center { content: "Page " counter(page) " of " counter(pages); font-size: 8pt; color: #444 } }
@page :first { @top-left { content: none } @top-right { content: none } @bottom-center { content: none } }
body { font-family: "Liberation Serif", "DejaVu Serif", serif; font-size: 10pt; line-height: 1.35; color: #111 }
h1, h2, h3 { font-family: "Liberation Sans", "DejaVu Sans", sans-serif }
a { color: #1a4d80; text-decoration: none }
code { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 8.5pt; background: #f3f3f3; padding: 0 2pt }
pre { font-size: 8pt; background: #f3f3f3; padding: 4pt; white-space: pre-wrap }
.cover { page-break-after: always; padding-top: 65mm; text-align: center }
.cover .title { font-size: 30pt; margin-bottom: 4pt; bookmark-level: none }
.cover .sub { font-size: 14pt; color: #333; margin-top: 0 }
.cover .meta { margin-top: 30mm; font-size: 10pt; color: #444 }
.cover table { margin: 8mm auto 0 auto; font-size: 9.5pt; border: none }
.cover td { border: none; padding: 1pt 8pt; text-align: left }
.toc { page-break-after: always }
.toc h1 { font-size: 16pt; bookmark-level: none }
.toc ul { list-style: none; padding-left: 0; margin: 0 }
.toc li { margin: 1pt 0 } .toc li.doc { font-weight: bold; margin-top: 7pt }
.toc li.item { padding-left: 14pt; font-size: 9.5pt }
.toc a { color: inherit } .toc a::after { content: leader('.') target-counter(attr(href), page) }
h1.doc { page-break-before: always; string-set: doctitle content(); font-size: 18pt; border-bottom: 2px solid #234; padding-bottom: 3pt }
.docintro { color: #444; font-size: 9.5pt; margin-bottom: 10pt }
h2.item { font-size: 12pt; margin: 10pt 0 4pt 0; break-after: avoid }
h2.item .lvl { color: #666; margin-right: 6pt } h2.item .uid { float: right; font-family: "Liberation Mono", monospace; font-size: 9pt; color: #555; font-weight: normal }
h2.heading { font-size: 13pt; margin-top: 12pt; color: #234 }
.item { border-top: 1px solid #ccc; padding-top: 2pt; margin-top: 6pt }
.item p { margin: 3pt 0 } .item ul, .item ol { margin: 2pt 0 2pt 14pt }
table { border-collapse: collapse; font-size: 8.5pt; margin: 4pt 0 }
td, th { border: 1px solid #bbb; padding: 2pt 4pt; vertical-align: top; text-align: left }
th { background: #eef1f5 }
.attrs { margin-top: 5pt; font-size: 8pt; color: #333; break-before: avoid; break-inside: avoid }
.item > *:nth-last-child(2) { break-after: avoid } .attrs th { width: 12%; background: #f7f7f7 } .attrs td { width: 21% }
.matrix { width: 100% } thead { display: table-header-group } .matrix td { font-family: "Liberation Mono", monospace; font-size: 8pt }
"""

DOC_INTRO = {
    "NEED": "Why the project exists: the stakeholder needs every requirement traces back to.",
    "REQ": "What the software shall do. Each requirement links to the needs it serves and is implemented by one design item.",
    "DES": "How each requirement is implemented in the code as it is today: modules, algorithms, constants, decisions and known limits. One design item per requirement.",
    "TST": "How each design is verified. Each test specification links to the design items it proves and names the automated test that implements it.",
}


def level_str(item):
    return ".".join(str(x) for x in item.level.value)


def md(text):
    return markdown.markdown(text or "", extensions=["tables", "fenced_code"])


def git_short_hash():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def build_html(tree):
    docs = {d.prefix: d for d in tree}
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0")) or int(dt.datetime.now(dt.timezone.utc).timestamp())
    date = dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%d")
    counts = {p: sum(1 for it in docs[p].items if it.active) for p, _ in ORDER}
    out = [f"<html><head><meta charset='utf-8'><title>{TITLE} requirements and traceability</title>",
           f"<meta name='author' content='{TITLE}'><meta name='description' content='{SUBTITLE}'><style>{CSS}</style></head><body>",
           f"<section class='cover'><h1 class='title'>{TITLE}</h1><p class='sub'>{SUBTITLE}</p>",
           "<div class='meta'><p>Generated from the Doorstop tree in <code>docs/traceability/</code></p><table>",
           f"<tr><td>Tree date</td><td>{date}</td></tr><tr><td>Repository revision</td><td><code>{git_short_hash()}</code></td></tr>",
           "".join(f"<tr><td>{name}</td><td>{counts[p]} items ({p})</td></tr>" for p, name in ORDER),
           "</table></div></section>",
           "<nav class='toc'><h1>Contents</h1><ul>"]
    for p, name in ORDER:
        out.append(f"<li class='doc'><a href='#doc-{p}'>{name} ({p})</a></li>")
        for it in docs[p].items:
            if it.active:
                out.append(f"<li class='item'><a href='#{it.uid}'>{level_str(it)} {html.escape(it.header or str(it.uid))} ({it.uid})</a></li>")
    out.append("<li class='doc'><a href='#matrix'>Traceability matrix</a></li></ul></nav>")
    for p, name in ORDER:
        out.append(f"<h1 class='doc' id='doc-{p}'>{name} ({p})</h1><p class='docintro'>{DOC_INTRO[p]}</p>")
        for it in docs[p].items:
            if not it.active:
                continue
            heading = html.escape(it.header or "")
            if not it.normative:
                out.append(f"<h2 class='heading' id='{it.uid}'><span class='lvl'>{level_str(it)}</span> {heading}</h2>{md(it.text)}")
                continue
            parents = ", ".join(f"<a href='#{l}'>{l}</a>" for l in it.links) or "-"
            children = ", ".join(f"<a href='#{c}'>{c}</a>" for c in it.find_child_links()) or "-"
            out.append(f"<section class='item'><h2 class='item' id='{it.uid}'><span class='lvl'>{level_str(it)}</span>{heading}<span class='uid'>{it.uid}</span></h2>")
            out.append(md(it.text))
            out.append(f"<table class='attrs'><tr><th>Level</th><td>{level_str(it)}</td><th>Parents</th><td>{parents}</td><th>Children</th><td>{children}</td></tr></table></section>")
    out.append("<h1 class='doc' id='matrix'>Traceability matrix</h1><p class='docintro'>Every chain from need to test; a blank cell means the chain is not linked at that level.</p>")
    out.append("<table class='matrix'><thead><tr>" + "".join(f"<th>{name} ({p})</th>" for p, name in ORDER) + "</tr></thead><tbody>")
    for row in tree.get_traceability():
        out.append("<tr>" + "".join(f"<td>{f'<a href=#{i.uid}>{i.uid}</a>' if i else ''}</td>" for i in row) + "</tr>")
    out.append("</tbody></table></body></html>")
    return "\n".join(out)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "traceability", "published", "CwellEEGRead-traceability.pdf")
    tree = doorstop.build(root=ROOT)
    page = build_html(tree)
    if os.environ.get("DOORSTOP_PDF_HTML"):
        with open(os.environ["DOORSTOP_PDF_HTML"], "w", encoding="utf-8") as fh:
            fh.write(page)
    HTML(string=page, base_url=ROOT).write_pdf(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
