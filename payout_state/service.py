"""Pick one payout state for an account from its balance transactions.

Returns the Payout State Service Response Contract
(specs/001-payout-status/contracts/payout-state.schema.json).

Check order (first match wins): negative_after_refund, payout_scheduled,
pending_only, no_payout. Every value is worked out from the rows at runtime.
Message wording comes from docs/payout-states.md via templates.py.
"""
import csv
import re
from datetime import date
from decimal import Decimal

from .templates import load_templates

ZERO = Decimal("0")
SCHEDULED = {"pending", "in_transit"}


def _txn_number(row):
    m = re.search(r"(\d+)$", row["balance_transaction_id"])
    return int(m.group(1)) if m else 0


def _cents(value):
    return int((Decimal(value) * 100).quantize(Decimal("1")))


def _money(cents):
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def _day(iso):
    d = date.fromisoformat(iso[:10])
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}"


def _fill(template, values):
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"No value for placeholder {{{key}}}")
        return values[key]
    return re.sub(r"\{(\w+)\}", sub, template)


def load_rows(csv_paths, account_id, as_of=None):
    """Rows for one account, oldest first. as_of is a date (YYYY-MM-DD) or full timestamp."""
    if isinstance(csv_paths, (str, bytes)) or hasattr(csv_paths, "__fspath__"):
        csv_paths = [csv_paths]
    rows = []
    for path in csv_paths:
        with open(path, newline="", encoding="utf-8") as f:
            rows += [r for r in csv.DictReader(f) if r["account_id"] == account_id]
    if as_of:
        n = len(as_of)
        rows = [r for r in rows if r["created_at"][:n] <= as_of]
    rows.sort(key=lambda r: (r["created_at"], _txn_number(r)))
    return rows


def get_payout_state(csv_paths, account_id, as_of=None, doc_path=None):
    messages, reasons = load_templates(doc_path) if doc_path else load_templates()
    rows = load_rows(csv_paths, account_id, as_of)
    if not rows:
        raise ValueError(f"No transactions for {account_id}")

    latest = rows[-1]
    today = latest["created_at"][:10]
    available = _cents(latest["running_available_balance"])
    pending = _cents(latest["running_pending_balance"])

    scheduled = [r for r in rows if r["type"] == "payout" and r["payout_status"] in SCHEDULED]
    canceled = any(r["payout_status"] == "canceled" for r in rows)
    nxt = min(scheduled, key=lambda r: (r["payout_arrival_date"], _txn_number(r))) if scheduled else None

    pending_rows = [r for r in rows if r["balance_status"] == "pending"]
    pending_available_on = None
    if pending > 0 and pending_rows:
        future = [r["available_on"] for r in pending_rows if r["available_on"] > today]
        pending_available_on = min(future) if future else max(r["available_on"] for r in pending_rows)

    if available < 0 and canceled:
        state = "negative_after_refund"
        nxt = None  # a canceled payout is never the next payout
        message = _fill(messages[state], {"balance": _money(available)})
    elif available >= 0 and nxt:
        state = "payout_scheduled"
        message = _fill(messages[state], {
            "amount": _money(abs(_cents(nxt["amount"]))),
            "arrival_date": _day(nxt["payout_arrival_date"]),
        })
    elif available == 0 and pending > 0:
        state = "pending_only"
        message = _fill(messages[state], {
            "pending_amount": _money(pending),
            "available_on": _day(pending_available_on),
        })
    else:
        state = "no_payout"
        payouts = [r for r in rows if r["type"] == "payout"]
        if available == 0 and pending == 0:
            reason = next(k for k in reasons if "balance is $0" in k)
        elif payouts and payouts[-1]["payout_failure_reason"]:
            reason = next(k for k in reasons if "bank account" in k)
        else:
            reason = next(k for k in reasons if "hasn't been created" in k)
        message = _fill(messages[state], {"reason": reason, "next_step": reasons[reason]})

    return {
        "account_id": account_id,
        "state": state,
        "available_balance": available,
        "pending_balance": pending,
        "next_payout_id": nxt["payout_id"] if nxt else None,
        "next_payout_amount": abs(_cents(nxt["amount"])) if nxt else None,
        "next_payout_arrival_date": nxt["payout_arrival_date"] if nxt else None,
        "pending_available_on": pending_available_on,
        "message": message,
    }
