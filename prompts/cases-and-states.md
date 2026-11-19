# Prompt: create Maria's cases and the payout state list

This is the prompt given to Claude Code, run from the root of this repo, to turn Maria's data into Stripe test-mode cases and the payout state list in `docs/payout-states.md`. Rerun it to rebuild the cases or check how the list was made.

---

You're working in my stripe-home-payout repo. My Stripe test secret key is in .env as STRIPE_SECRET_KEY. Use test mode only: stop if any API response shows livemode: true, and never print, log or commit the key.

Goal: create one Stripe test-mode case for each of Maria's Bakery's four payout states, then complete the payout state list in docs/payout-states.md, which the Home design and code both read from.

Context files:
- data/Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv: Maria's real paydays. Use it for realistic descriptions (bakery orders, catering, bank ****6621). The amounts and dates in it don't reconcile (net is not always amount minus fee, and some available_on dates come before created_at), so don't copy figures from it.
- docs/payout-states.md: the four states, how to detect each, what Home shows today, and the owner message for each. Keep the owner messages as they are written.

The four states:
1. payout_scheduled: a $4,200.00 payout in transit to bank ****6621, with an arrival date
2. pending_only: $0.00 available, money pending, no payout scheduled yet
3. no_payout: no payout scheduled, with a clear reason
4. negative_after_refund: a large catering refund takes the balance to -$1,874.55 and the next payout is canceled

Step 1. Create the cases
For each state, create the test objects that put a balance into that state. Use Stripe test cards (for example 4000000000000077 for funds that are available right away), plus charges, refunds and payouts. Use a separate test connected account per state if that's the cleanest way to keep them apart. Tag every object you create with metadata state_id=<state>. Put the script in scripts/create_cases.js (or .py) so it can be run again. If Stripe test mode can't produce a state exactly (for example an exact negative balance), get as close as you can and write down the gap.

Step 2. Verify
For each case, call GET /v1/balance and GET /v1/payouts and save the raw responses to cases/<state_id>.json.

Step 3. Complete the payout state list
Update docs/payout-states.md and write docs/payout-states.json with the same content. For each state:
- fill the {placeholders} in the owner message with the real test data
- check that the detection rule matches the saved API responses, and fix it if it doesn't
- add the Stripe test object IDs for the case
- note any gap between the test case and the real moment

Step 4. Commit and push
Run git status and confirm .env isn't staged. Then commit with a clear message, push to origin, and show me the list of files you added.

Before you start, tell me your plan for each state in one or two lines, and wait for my OK.
