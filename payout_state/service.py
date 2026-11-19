"""Pick one payout state for an account from its balance transactions.

Check order (first match wins), from specs/001-payout-status/spec.md FR-002:
negative_after_refund, payout_scheduled, pending_only, no_payout.

Every value is worked out from the rows at runtime. Message wording comes from
docs/payout-states.md via templates.py.
"""
import csv
import re
from decimal import Decimal
from pathlib import Path

from .templates import load_templates

ZERO = Decimal("0")
SCHEDULED = {"pending", "in_transit"}
SYMBOLS = {"usd": "$", "gbp": "£", "eur": "€", "inr": "₹"}


def _txn_number(row):
    m = re.search(r"(\d+)$", row["balance_transaction_id"])
    return int(m.group(1)) if m else 0


def _money(value, currency):
    value = Decimal(value).quantize(Decimal("0.01"))
    symbol = SYMBOLS.get(currency, currency.upper() + " ")
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def _plain(value):
    return str(Decimal(value).quantize(Decimal("0.01")))


def _fill(template, values):
    def sub(m):
        key = m.group(1)
        if key not in values:
            raise KeyError(f"No value for placeholder {{{key}}}")
        return values[key]
    return re.sub(r"\{(\w+)\}", sub, template)


def load_rows(csv_path, account_id, as_of):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)
                if r["account_id"] == account_id and r["created_at"] <= as_of]
    rows.sort(key=lambda r: (r["created_at"], _txn_number(r)))
    return rows


def get_payout_state(csv_path, account_id, as_of, doc_path=None):
    messages, reasons = load_templates(doc_path) if doc_path else load_templates()
    rows = load_rows(csv_path, account_id, as_of)
    if not rows:
        raise ValueError(f"No transactions for {account_id} on or before {as_of}")

    latest = rows[-1]
    currency = latest["currency"].lower()
    available = Decimal(latest["running_available_balance"])
    pending = Decimal(latest["running_pending_balance"])

    def result(state_id, message, amount, date, reason, sources):
        return {
            "account_id": account_id,
            "as_of": as_of,
            "state_id": state_id,
            "message": message,
            "amount": amount,
            "currency": currency,
            "date": date,
            "reason": reason,
            "source_transaction_ids": sources,
        }

    # 1. negative_after_refund
    if available < ZERO:
        refunds = [r for r in rows if r["type"] == "refund"]
        cancels = [r for r in rows if r["type"] == "payout_cancel" or r["payout_status"] == "canceled"]
        sources = [latest["balance_transaction_id"]]
        sources += [r["balance_transaction_id"] for r in refunds[-1:] + cancels[-1:]]
        message = _fill(messages["negative_after_refund"], {"balance": _money(available, currency)})
        reason = refunds[-1]["description"] if refunds else None
        return result("negative_after_refund", message, _plain(available), None, reason, sources)

    # 2. payout_scheduled
    scheduled = [r for r in rows if r["type"] == "payout" and r["payout_status"] in SCHEDULED]
    if scheduled:
        payout = min(scheduled, key=lambda r: (r["payout_arrival_date"], _txn_number(r)))
        amount = abs(Decimal(payout["amount"]))
        m = re.search(r"\*{2,}(\d{4})", payout["description"])
        message = _fill(messages["payout_scheduled"], {
            "amount": _money(amount, currency),
            "last4": m.group(1) if m else "on file",
            "arrival_date": payout["payout_arrival_date"],
        })
        return result("payout_scheduled", message, _plain(amount),
                      payout["payout_arrival_date"], None, [payout["balance_transaction_id"]])

    # 3. pending_only
    if available == ZERO and pending > ZERO:
        upcoming = [r for r in rows if r["balance_status"] == "pending" and r["available_on"] >= as_of]
        first = min(upcoming, key=lambda r: r["available_on"]) if upcoming else None
        available_on = first["available_on"] if first else None
        sources = [latest["balance_transaction_id"]] + ([first["balance_transaction_id"]] if first else [])
        message = None
        if available_on:
            message = _fill(messages["pending_only"], {
                "pending_amount": _money(pending, currency),
                "available_on": available_on,
            })
        return result("pending_only", message, _plain(pending), available_on, None, sources)

    # 4. no_payout (catch-all)
    payouts = [r for r in rows if r["type"] == "payout"]
    zero_reason = next((k for k in reasons if "balance is $0" in k), None)
    bank_reason = next((k for k in reasons if "bank account" in k), None)
    sources = [latest["balance_transaction_id"]]
    if available == ZERO and pending == ZERO and zero_reason:
        reason = zero_reason
    elif payouts and payouts[-1]["payout_failure_reason"] and bank_reason:
        reason = bank_reason
        sources.append(payouts[-1]["balance_transaction_id"])
    else:
        reason = "unknown"
    message = None
    if reason != "unknown":
        message = _fill(messages["no_payout"], {"reason": reason, "next_step": reasons[reason]})
    return result("no_payout", message, _plain(available), None, reason, sources)
