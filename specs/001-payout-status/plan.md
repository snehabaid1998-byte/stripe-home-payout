# Implementation plan: Payout state service

**Feature:** 001-payout-status · **Spec:** `spec.md` · **Contract:** `contracts/payout-state.schema.json`

## Summary

A small Python service, `get_payout_state(csv_path, account_id, as_of)`, reads Maria's balance transactions and returns one payout state in the nine-field contract shape. The owner message comes from `docs/payout-states.md` at runtime.

## Technical context

- Python 3.10+, standard library only (csv, decimal, re, json, datetime). No network calls, no Stripe API, no keys needed.
- Input: `data/Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv` (420 rows, all `acct_test_maria_bakery`, Sep to Nov 2026).
- Tests: `unittest`, with small CSV fixtures in `tests/fixtures/` in the same columns as Maria's file.

## Constitution check

- Three-question test: every message template answers how much, when, and what's wrong. Pass.
- One source for wording: templates parsed from `docs/payout-states.md`. Pass.
- Work it out from the data: no per-account constants. Pass.
- Test mode only: reads a test-mode export; no secrets used. Pass.

## Data selection

1. Keep rows where `account_id` matches and `created_at` is on or before `as_of`.
2. Sort by `created_at`, then by the number in `balance_transaction_id`. The last row is the "latest row".
3. Balances come from the latest row's `running_available_balance` and `running_pending_balance`. `fee` and `net` are not used, because they don't reconcile in this file.

## Column map per state (check order, first match wins)

| Order | state_id | Decides the state | Fills the message |
|---|---|---|---|
| 1 | negative_after_refund | latest `running_available_balance` < 0 | `{balance}` from that balance. reason = `description` of the latest `type = refund` row |
| 2 | payout_scheduled | a `type = payout` row with `payout_status` in (pending, in_transit) | `{amount}` = abs(`amount`), `{arrival_date}` = `payout_arrival_date`, `{last4}` from `description` (digits after `****`). If several, the earliest arrival |
| 3 | pending_only | latest available = 0, latest pending > 0, no scheduled payout | `{pending_amount}` = latest `running_pending_balance`, `{available_on}` = earliest `available_on` on or after `as_of` among `balance_status = pending` rows |
| 4 | no_payout | none of the above | reason: available = 0 → "your available balance is $0"; latest payout row has `payout_failure_reason` → "your bank account needs updating"; otherwise "unknown" |

Every state uses `account_id`, `created_at` and `currency`.

## Message templates

`docs/payout-states.md` → table "The four states" → column "Owner message". The `no_payout` next steps come from the table "Reasons for `no_payout`". When the reason is "unknown", `message` is null.

## Known data gaps

- No payout with status pending or in_transit, and no negative running balance, in Maria's file. Those states are tested with fixtures.
- Some `available_on` dates are earlier than `created_at`. Dates before `as_of` are ignored.
- Manual schedule and payouts paused can't be detected from transactions. Returned as "unknown".

## Project structure

```
payout_state/
  __init__.py
  service.py        # get_payout_state, check order, column map
  templates.py      # reads owner messages and reasons from docs/payout-states.md
  __main__.py       # python -m payout_state --as-of 2026-11-16
tests/
  fixtures/*.csv
  test_service.py
```

## Update (19 Nov 2026): official contract and Home

- `contracts/payout-state.schema.json` is now Dashboard Engineering's Payout State Service Response Contract v1.0.0 (amounts in integer USD cents; fields `account_id`, `state`, `available_balance`, `pending_balance`, `next_payout_id`, `next_payout_amount`, `next_payout_arrival_date`, `pending_available_on`, `message`). The service and the tests follow it.
- `pending_available_on` is the earliest `available_on` after the latest transaction's date among pending rows.
- Home is a Next.js app (`app/`, `lib/payoutState.ts`), a TypeScript port of the Python service. `npm run parity` checks both return identical responses on every fixture and every held-out day.
- **Open contract gap [NEEDS CLARIFICATION]:** money available and pending with no payout created matches none of the four contract states. `no_payout` requires `pending_balance` = 0. In the held-out data this is true on 8 of the 14 days. The service returns `no_payout` with the "hasn't been created yet" reason, and that response fails the contract on `pending_balance` and `pending_available_on`.
- **Failed payout notice:** `balance_notices()` (Python) and `balanceNotices()` (TypeScript) flag failed payouts with no transaction returning the money, and Home explains them in the Balance panel using wording from the "Balance notices" table in docs/payout-states.md. They aren't part of the contract response, and the contract figures are unchanged. [NEEDS CLARIFICATION] whether the service should correct `available_balance` for them: doing so would remove the held-out negative and pending_only days.
- **Automatic checks:** `.github/workflows/checks.yml` (tests, parity, build on every push) and `.github/workflows/live-check.yml` (browser check against the live site after each production deploy, daily, and on demand).
