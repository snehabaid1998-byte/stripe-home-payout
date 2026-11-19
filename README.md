# stripe-home-payout

Payout status for Stripe Dashboard Home, built from Maria's Bakery test-mode data (`acct_test_maria_bakery`, Sep to Nov 2026).

## What's here

| Path | What it is |
|---|---|
| `docs/payout-states.md` | The payout state list: the four states, how to detect them, what Home shows today, and the owner message for each. The only place message wording lives. |
| `prompts/cases-and-states.md` | The Claude Code prompt used to build test-mode cases and the state list. |
| `design/payday-frames.html` | The four Home frames (also in Figma), styled with Stripe Elements "stripe" theme tokens. |
| `.specify/memory/constitution.md` | Spec Kit constitution: the rules every spec follows. |
| `specs/001-payout-status/` | Spec Kit spec, plan, tasks, and the nine-field contract (`contracts/payout-state.schema.json`). |
| `payout_state/` | The payout state service. |
| `tests/` | Tests for every state and overlap, with CSV fixtures. |
| `data/` | Maria's balance transactions (test mode). |

## The payout state service

`get_payout_state(csv_path, account_id, as_of)` reads the balance transactions and returns one payout state in the nine-field contract shape: `account_id`, `as_of`, `state_id`, `message`, `amount`, `currency`, `date`, `reason`, `source_transaction_ids`.

- States are checked in order, first match wins: `negative_after_refund`, `payout_scheduled`, `pending_only`, `no_payout`.
- Every value is worked out from the transactions at runtime. Nothing is hard-coded per account or case.
- The message is read from `docs/payout-states.md` at runtime and filled from the calculated values.
- If a value can't be worked out, it returns null or "unknown" instead of guessing.

Run it (Python 3.10+, no installs needed):

```
python -m payout_state --csv "data/Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv" --account acct_test_maria_bakery --as-of 2026-11-16
```

Run the tests:

```
python -m unittest -v
```

## Result on Maria's file (as of 2026-11-16)

`no_payout`, reason `unknown`, amount `6412.39` available, worked out from `txn_370` (her latest row). Her balance is above $0 and nothing is scheduled, but the transactions alone can't say why (manual schedule or payouts paused need payout settings). So the service returns "unknown" and no message rather than guessing.

## Known data gaps

- Maria's file has no payout with status pending or in_transit, and her running balance never goes below $0. `payout_scheduled` and `negative_after_refund` are tested with fixtures in `tests/fixtures/`.
- `net` often doesn't equal `amount` minus `fee`, so the service uses the running balances.
- Some `available_on` dates are earlier than `created_at`. Dates before `as_of` are ignored.

## Setup

Copy `.env.example` to `.env` and add your Stripe test secret key (`sk_test_...`). `.env` is gitignored and never committed.
