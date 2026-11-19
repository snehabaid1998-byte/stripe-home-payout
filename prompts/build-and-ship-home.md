# Prompt: build Home and ship it to Vercel

The prompt given to Claude Code to build Dashboard Home as a Next.js app and ship it through Vercel. Auto mode off, so each step was approved.

---

Build Dashboard Home as a Next.js app (App Router, TypeScript) at the root of this repo, and ship it through Vercel.

Source of truth (read first, don't contradict):
- specs/001-payout-status/spec.md and plan.md: states, check order, column map
- specs/001-payout-status/contracts/payout-state.schema.json: the Payout State Service Response Contract
- docs/payout-states.md: the only place message wording lives
- design/payday-frames.html: layout, panel order, Stripe Elements "stripe" tokens

Payout state on the server:
- Port payout_state/service.py to lib/payoutState.ts with the same check order (negative_after_refund, payout_scheduled, pending_only, no_payout; first match wins), the same column map and the same contract output.
- Read the transactions and docs/payout-states.md at runtime. No figures, payout ids or message wording in the code.
- Parity: run both services on every fixture and every held-out day; outputs must match exactly (npm run parity).

Home page:
- Panel order from the frames: PayoutStatusCard (12×2), Balance (Available/Pending) beside Disputes, Recent activity, then the other panels, Setup guide last.
- Card colour and action follow the state. In negative_after_refund, the refund and canceled payouts are highlighted at the top of Recent activity.
- ?as_of=YYYY-MM-DD shows any day, with a day strip linking each one; /api/payout-state returns the contract JSON.
- Must work at 1440×900 with the payout card above the fold.

Safety: no Stripe key needed (reads the test-mode export), no env vars, .env stays out of git. Don't change the spec, contract or service rules; stop and ask on conflicts.

Shipping: branch home-payout, npm run build + parity + python -m unittest must pass, push for a Vercel preview, merge to master only after review.

---

## Note: money available and pending, but no payout yet

**What happens:** on 8 of the 14 held-out days (17 to 19, 23 to 25, 28 and 29 Nov), Maria has money available and money pending, but no payout has been created yet. The daily automatic payout runs around 17:00, so this is the normal state for most of each business day, and over weekends and the Thanksgiving closure.

**Why it doesn't fit:** the contract's four states don't cover it. `pending_only` needs available = $0, and `no_payout` needs pending = $0.

**Decision:** keep the four states. The stage brief fixes them, and a fifth state would change the contract that Dashboard Engineering, Payouts Engineering and the Playwright checks all depend on.

**What Home does:** returns `no_payout` (the catch-all, so the card is never blank) with the reason from docs/payout-states.md: "No payout is scheduled right now because your next automatic payout hasn't been created yet. Your daily payout is usually created around 5 pm on business days, and it will show here as soon as it's on its way." The "5 pm" is worked out from her past payout times, not written into the code Balance still shows the real Available and Pending figures, so nothing is hidden.

**Known consequence:** these responses fail the contract on `pending_balance` (must be 0) and `pending_available_on` (must be null) for `no_payout`. A test (`test_money_with_no_payout_is_outside_the_contract`) pins this down so it can't change silently.

**Recommendation for the contract owner (Daniel Okafor):** relax `no_payout` to allow `pending_balance` > 0 with `pending_available_on` filled in. This keeps four states and makes these days valid.

## Other things found in the held-out data

- **Paid daily payouts** (po_0082, po_0083, po_0086, po_0087, po_0088) are never treated as the next payout.
- **The failed payout** po_0081 ($300.00, account_closed) is never the next payout. It doesn't trigger the "bank account needs updating" reason, because po_0082 was paid 22 minutes later. The failed $300 still lowered the running balance, with no row returning it, so the balances after 17 Nov 17:10 look $300 low.
- **Thanksgiving:** po_0089 went out early on Thu 26 Nov before the closure. There are no payouts on 27 to 29 Nov. Daily payouts resume on payroll morning, Mon 30 Nov.
