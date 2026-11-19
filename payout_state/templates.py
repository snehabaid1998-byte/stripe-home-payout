"""Read owner message templates and no_payout reasons from docs/payout-states.md.

The wording lives only in that doc. Nothing here copies it.
"""
import re
from pathlib import Path

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "payout-states.md"


def _table_rows(text, heading):
    """Return the cells of each body row in the first table under a heading."""
    start = text.index(heading)
    rows = []
    in_table = False
    for line in text[start:].splitlines()[1:]:
        line = line.strip()
        if line.startswith("|"):
            in_table = True
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # separator row
            rows.append(cells)
        elif in_table:
            break
        elif line.startswith("#"):
            break
    return rows[1:]  # drop header row


def _unquote(cell):
    m = re.search(r'"(.*)"', cell)
    return m.group(1) if m else cell


def load_templates(doc_path=DOC_PATH):
    text = Path(doc_path).read_text(encoding="utf-8")
    messages = {}
    for cells in _table_rows(text, "## The four states"):
        state_id = cells[0].strip("`")
        messages[state_id] = _unquote(cells[-1])
    reasons = {}
    for cells in _table_rows(text, "## Reasons for `no_payout`"):
        reasons[cells[0]] = _unquote(cells[1])
    return messages, reasons
