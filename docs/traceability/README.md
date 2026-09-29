# Traceability (Doorstop)

Four documents form the chain:

| Prefix | Folder | Content | Parent |
|---|---|---|---|
| `NEED` | `needs/` | stakeholder needs and project goals | - |
| `REQ` | `requirements/` | system requirements ("the program shall ...") | NEED |
| `DES` | `design/` | design: how each requirement is implemented (modules, algorithms, decisions), one item per requirement | REQ |
| `TST` | `tests/` | test specifications proving the designs (and through them the requirements) | DES |

Rules (REQ013): every normative REQ links to at least one NEED and is
covered by a DES item, every DES linked from at least one TST; `doorstop` validation must pass.
`tests/test_traceability.py` checks this automatically.

Commands (from the repository root, with `.venv` activated):

```bash
doorstop                              # validate the whole tree
doorstop add REQ                      # create the next REQ item
doorstop link REQ019 NEED003          # link child -> parent
doorstop link TST015 REQ019
doorstop review all                   # clear "unreviewed" after edits
doorstop clear all                    # clear "suspect link" after parent edits
doorstop publish REQ published/REQ.md # readable copy (do this for NEED, REQ, DES, TST)
doorstop publish all published/html   # browsable HTML with traceability matrix (gitignored)
```

Item files are YAML (`REQ001.yml` ...). `header` is the title, `text` the
normative statement, `links` the parent items, `level` the outline
position. Non-normative explanatory items can be added with
`normative: false`.
