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

## Home (Next.js on Vercel)

`app/page.tsx` renders Dashboard Home with the payout status card first, then Balance (Available/Pending) beside Disputes, Recent activity, and the other panels. It reads the transactions and `docs/payout-states.md` at runtime through `lib/payoutState.ts`.

- `/` shows the held-out data (17 to 30 Nov 2026) as of the latest day. `/?as_of=2026-11-20` shows any day; the strip at the top links every day.
- `/?data=sep-nov` shows the original Sep to Nov file.
- `/api/payout-state?as_of=2026-11-30` returns the contract JSON.

```
npm install
npm run dev        # http://localhost:3000
npm run build
npm run parity     # TypeScript and Python services must match
```

## The payout state service

`get_payout_state(csv_paths, account_id, as_of)` reads the balance transactions and returns the Payout State Service Response Contract (`specs/001-payout-status/contracts/payout-state.schema.json`): `account_id`, `state`, `available_balance`, `pending_balance`, `next_payout_id`, `next_payout_amount`, `next_payout_arrival_date`, `pending_available_on`, `message`. Amounts are integer USD cents.

- States are checked in order, first match wins: `negative_after_refund`, `payout_scheduled`, `pending_only`, `no_payout`.
- Every value is worked out from the transactions at runtime. Nothing is hard-coded per account or case.
- The message is read from `docs/payout-states.md` at runtime and filled from the calculated values.
- If a value can't be worked out, it returns null or "unknown" instead of guessing.

Run it (Python 3.10+, no installs needed):

```
python -m payout_state --account acct_test_maria_bakery --as-of 2026-11-30 --csv data/maria_bakery_balance_transactions_heldout_nov_2026.csv
```

Run the tests:

```
python -m unittest -v
```

## Results on the held-out data (17 to 30 Nov 2026)

| Days | State |
|---|---|
| 20, 21, 22 Nov | `negative_after_refund` (wedding cake refund, two payouts canceled) |
| 26, 27 Nov | `pending_only` ($145.05 becomes available Fri 27 Nov) |
| 30 Nov | `payout_scheduled` ($40.00, po_0090, arrives Mon 30 Nov) |
| 17 to 19, 23 to 25, 28, 29 Nov | Money available and pending, no payout yet. Outside the contract's four states (see the plan) |

`no_payout` as the contract defines it (nothing pending) never occurs in the held-out data.

## Known data gaps

- Maria's file has no payout with status pending or in_transit, and her running balance never goes below $0. `payout_scheduled` and `negative_after_refund` are tested with fixtures in `tests/fixtures/`.
- `net` often doesn't equal `amount` minus `fee`, so the service uses the running balances.
- Some `available_on` dates are earlier than `created_at`. Dates before `as_of` are ignored.

## Setup

Copy `.env.example` to `.env` and add your Stripe test secret key (`sk_test_...`). `.env` is gitignored and never committed.
