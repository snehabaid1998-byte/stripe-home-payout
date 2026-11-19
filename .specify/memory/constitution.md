# stripe-home-payout constitution

## I. Three-question test
Every owner-facing message answers: how much, when, and is anything wrong (and if so, what happens next).

## II. Plain language
Owner messages use plain words. No internal state names, API terms or jargon in anything an owner reads.

## III. One source for wording
Owner message wording lives only in `docs/payout-states.md`. Code reads it at runtime and never copies it.

## IV. Work it out from the data
Every value an owner sees is calculated from the transactions at runtime. Nothing is hard-coded per account or per case.

## V. Test mode only
Only Stripe test mode data and keys are used. Secrets stay in `.env`, which is never committed or printed.

## VI. Specs say what and why
Specs describe what owners see and why. How it is built belongs in the plan.

## VII. Design system
Design follows the Stripe Elements "stripe" theme tokens and the existing Home component names and grid sizes from the 11-panel inventory.
