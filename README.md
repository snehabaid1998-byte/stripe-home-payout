# stripe-home-payout

**Live Home (Vercel):** https://stripe-home-payout-sixz.vercel.app — opens on Maria's payroll day, Mon 30 Nov 2026. Deploys from `master` through the Vercel project linked to this repo; `vercel.json` pins the framework to Next.js.

| Check it | Link |
|---|---|
| Payroll day, payout on its way | https://stripe-home-payout-sixz.vercel.app/?as_of=2026-11-30 |
| Negative after the wedding cake refund | https://stripe-home-payout-sixz.vercel.app/?as_of=2026-11-20 |
| Money only pending (Thanksgiving) | https://stripe-home-payout-sixz.vercel.app/?as_of=2026-11-26 |
| Money but no payout yet | https://stripe-home-payout-sixz.vercel.app/?as_of=2026-11-17 |
| Failed $300 payout explained (Balance panel) | https://stripe-home-payout-sixz.vercel.app/?as_of=2026-11-20 |
| Contract JSON | https://stripe-home-payout-sixz.vercel.app/api/payout-state?as_of=2026-11-30 |

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
npx playwright install chromium   # first time only
npm run e2e        # live browser check, see below
```

### Automatic checks (GitHub Actions)

- `.github/workflows/checks.yml`: on every push, runs the service tests, the Python/TypeScript parity check and a Next.js build.
- `.github/workflows/live-check.yml`: after every successful Vercel production deploy (plus every morning, and on demand), opens the live site and runs the browser check below. It needs **Vercel → Project Settings → Git → deployment_status Events** turned on.

### Live browser check

`e2e/payday.spec.ts` opens the live Vercel site at 1440×900 for every held-out day (17 to 30 Nov). For each day it checks that the page loads, that the payout card shows the expected state and the same message as `/api/payout-state`, and that the whole card sits above the fold. Point it at another deployment with `HOME_URL=<url> npm run e2e`.

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
| 17 to 19, 23 to 25, 28, 29 Nov | Money available and pending, no payout yet. Home tells Maria her daily payout is usually created around 5 pm on business days (worked out from her payout times). Outside the contract's four states (see the plan and `prompts/build-and-ship-home.md`) |

`no_payout` as the contract defines it (nothing pending) never occurs in the held-out data.

## The failed $300 payout

po_0081 ($300.00) failed at the bank on 17 Nov ("account_closed"), but no transaction returns the money, so every running balance after 17:10 that day is $300 low. Home shows this in the Balance panel ("…should come back to your balance…"), worked out from the data: any failed payout with no `payout_failure`/`payout_cancel` row, or positive amount, for the same payout id.

The contract figures and payout states are left as recorded, because the contract says `available_balance` comes from `running_available_balance`. **Open question:** if the $300 had come back, Maria would never have gone below $0. 20 to 22 Nov would be +$275.08 instead of -$24.92, and 26 Nov would not be `pending_only`. Should the service correct for it?

## Known data gaps

- Maria's file has no payout with status pending or in_transit, and her running balance never goes below $0. `payout_scheduled` and `negative_after_refund` are tested with fixtures in `tests/fixtures/`.
- `net` often doesn't equal `amount` minus `fee`, so the service uses the running balances.
- Some `available_on` dates are earlier than `created_at`. Dates before `as_of` are ignored.

## Setup

Copy `.env.example` to `.env` and add your Stripe test secret key (`sk_test_...`). `.env` is gitignored and never committed.
