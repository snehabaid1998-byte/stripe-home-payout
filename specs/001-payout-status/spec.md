# Feature spec: Payout status on Dashboard Home

**Feature:** 001-payout-status
**Status:** Approved for implementation
**Sources of truth:** `docs/payout-states.md`, Current Dashboard Home 11-panel inventory, `design/payday-frames.html`, `prompts/cases-and-states.md`

## Problem

No panel on Home shows the next payout. Balance (position 9) shows only a total, sits below the fold on a 1440×900 screen, and is 4 clicks from the payout. When money is only pending, Balance shows $0.00 and the money looks gone. After a refund, the balance turns red with a minus sign and no explanation, and the canceled payout only shows in the Payouts list. Confused owners call support.

## User stories

Stories are ordered by support risk. This is not the order the service checks states in (see FR-002).

### Story 1: Negative balance after a refund (P1)

**Who and why:** Maria's Bakery issued a large catering refund. Her balance is now below $0 and her next payout was canceled. Today she sees an unexplained red number, which is the moment most likely to make her call support.

**Detection rule:** latest available balance < 0.

**Acceptance scenarios**
1. **Given** Maria's latest available balance is -$1,874.55 after a catering refund, **when** she opens Home, **then** the payout card shows: "Your balance is -$1,874.55 because the catering refund was larger than the money in your balance. We canceled your next payout to cover it. Payouts restart automatically once new sales bring your balance above $0. You don't need to do anything."
2. **Given** the balance is negative **and** an older payout still shows as in transit, **when** she opens Home, **then** she sees the negative-balance message, not the in-transit one.

**What Home shows:** PayoutStatusCard in the red state with the message and the steps Catering refund, Payout canceled, New sales, Payouts restart above $0. Balance shows Available in red, with "Next payout canceled to cover the refund". Recent activity highlights the refund and the canceled payout at the top.

### Story 2: Money only pending (P2)

**Who and why:** Maria has sales that haven't settled yet. Today Home shows "$0.00 available" and "No upcoming payouts", so the money looks gone.

**Detection rule:** available = 0, pending > 0, and no payout with status pending or in_transit.

**Acceptance scenarios**
1. **Given** available is $0.00 and pending is above $0, **when** she opens Home, **then** the card shows "You have {pending_amount} coming in. It becomes available on {available_on} and then gets paid out to your bank. Nothing is missing."
2. **Given** some pending rows have an available_on date earlier than today, **then** those dates are ignored when choosing {available_on}.

**What Home shows:** amber PayoutStatusCard. Balance shows Available $0.00 and the Pending amount side by side.

### Story 3: Payout on its way (P3)

**Who and why:** A payout is heading to Maria's bank. Today the amount and date are hidden 4 clicks deep.

**Detection rule:** a payout with status pending or in_transit.

**Acceptance scenarios**
1. **Given** a $4,200.00 payout is in transit to the bank account ending 6621, **when** she opens Home, **then** the card shows "$4,200.00 is on its way to your bank account ending 6621. Expected to arrive {arrival_date}." with zero clicks.
2. **Given** a payout is in transit **and** money is also pending, **then** she sees the payout message.

**What Home shows:** green PayoutStatusCard. Balance shows Available and Pending, with "Next payout: {amount} · in transit".

### Story 4: Nothing scheduled (P4)

**Who and why:** No payout is scheduled. Today Home gives no reason.

**Detection rule:** none of the other states match.

**Acceptance scenarios**
1. **Given** available, pending and payouts are all $0, **then** the card says "No payout is scheduled right now because your available balance is $0. Your next payout will be scheduled after your next sale settles."
2. **Given** the reason can't be worked out from the transactions, **then** the service returns reason "unknown" and no message, rather than guessing.

**Reasons (from `docs/payout-states.md`):** available balance is $0; payout schedule set to manual; payouts paused; bank account needs updating. Each has a next step.

## Home layout

Top to bottom on the 12-column grid: PayoutStatusCard (new, 12×2), Balance (6×2) beside Disputes (6×2), Recent activity (12×4), then Net volume, Gross volume, Today, Successful payments, Failed payments, New customers, Recommendations, Setup guide banner.

## Functional requirements

- **FR-001** The service returns exactly one payout state per account per as_of date.
- **FR-002** States are checked in this order, first match wins: negative_after_refund, payout_scheduled, pending_only, no_payout. Negative is first so a stale in-transit payout can't hide a debt. Payout comes before pending because the payout is the money arriving soonest. no_payout is the catch-all so Home is never blank.
- **FR-003** Every value is calculated from the transactions at runtime. Nothing is hard-coded per account or case.
- **FR-004** The owner message is read from `docs/payout-states.md` at runtime and filled from calculated values.
- **FR-005** The response matches `contracts/payout-state.schema.json` exactly (nine fields).
- **FR-006** If a value can't be worked out, the service says so (null or "unknown") instead of guessing.

## Edge cases

- State changes while Home is open: the card reflects the latest data on reload. [NEEDS CLARIFICATION: should Home refresh on its own?]
- Two payouts in transit: show the one arriving first. [NEEDS CLARIFICATION: confirm with product]
- Balance of exactly $0 with nothing pending: no_payout with the "$0" reason.
- Non-USD account: amounts are formatted in the account currency. [NEEDS CLARIFICATION: currency formats beyond USD]

## Open questions

- [NEEDS CLARIFICATION] The manual-schedule and payouts-paused reasons need payout settings, which are not in the transactions file.
- [NEEDS CLARIFICATION] Maria's file has no pending or in_transit payout and no negative balance, so those two states are covered by test fixtures, not her data.

## Success criteria

- The owner sees the payout amount and date with zero clicks, above the fold on a 1440×900 screen.
- Every one of the four states produces a message that answers how much, when, and is anything wrong.
