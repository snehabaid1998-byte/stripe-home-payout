# Payout state list

Every payout situation a Stripe owner can be in, and what Dashboard Home should tell them. Built from Maria's Bakery (acct_test_maria_bakery) in Stripe test mode, Sep to Nov 2026.

The Home design and the Home code both read from this list.

## Why this list exists

Today no panel on Home shows the next payout amount or its arrival date, and the Balance panel never shows the pending balance. Owners have to click 4 times (Balance > View > Payouts > Upcoming > open the row) to find out when they get paid. In two of the four states, what they do see looks wrong or alarming, so they call support.

Every owner message answers three questions:

1. How much?
2. When?
3. Is anything wrong, and if so, what happens next?

## The four states

| state_id | Moment | How to detect it (Stripe API) | What Home shows today | Owner message |
|---|---|---|---|---|
| `payout_scheduled` | Payout on its way | A payout exists with `status` = `pending` or `in_transit` (GET /v1/payouts) | "$312.40 available". The $4,200.00 payout and its arrival date are only visible 4 clicks deep, inside the payout row | "{amount} is on its way to your bank account. Expected to arrive {arrival_date}." |
| `pending_only` | Money only pending | `balance.available` = 0, `balance.pending` > 0, and no payout with `status` = `pending` or `in_transit` | "$0.00 available" and "No upcoming payouts". The money looks gone | "You have {pending_amount} coming in. It becomes available on {available_on} and then gets paid out to your bank. Nothing is missing." |
| `no_payout` | Nothing scheduled | No payout with `status` = `pending` or `in_transit`, `balance.pending` = 0, and `balance.available` >= 0 | The available figure only, and "No upcoming payouts" with no reason | "No payout is scheduled right now because {reason}. {next_step}" |
| `negative_after_refund` | Morning after the catering refund | `balance.available` < 0 after a refund, and the most recent payout has `status` = `canceled` | "-$1,874.55" in grey with no label, and a payout row that reads "Canceled" | "Your balance is {balance} because a refund was larger than the money in your balance. We canceled your next payout to cover it. Payouts restart automatically once new sales bring your balance above $0. You don't need to do anything." |

## Owner messages filled in for Maria

| state_id | Message Maria sees |
|---|---|
| `payout_scheduled` | "$4,200.00 is on its way to your bank account ending 6621. Expected to arrive {arrival_date}." |
| `pending_only` | "You have {pending_amount} coming in. It becomes available on {available_on} and then gets paid out to your bank. Nothing is missing." |
| `no_payout` | "No payout is scheduled right now because {reason}. {next_step}" |
| `negative_after_refund` | "Your balance is -$1,874.55 because the catering refund was larger than the money in your balance. We canceled your next payout to cover it. Payouts restart automatically once new sales bring your balance above $0. You don't need to do anything." |

Values still in {braces} come from the Stripe test-mode cases (see `prompts/cases-and-states.md`). The current Home capture does not include them.

## Reasons for `no_payout`

The message must always say why. Common reasons and next steps:

| reason | next_step |
|---|---|
| your available balance is $0 | "Your next payout will be scheduled after your next sale settles." |
| your payout schedule is set to manual | "You can send a payout yourself from Balances." |
| payouts are paused on your account | "Check Settings > Payouts to turn them back on." |
| your bank account needs updating | "Update your bank details in Settings > Payouts." |
| your next automatic payout hasn't been created yet | "Your daily payout is usually created around {usual_time} on business days, and it will show here as soon as it's on its way." |
| your next payout hasn't been created yet | "It will show here as soon as it's on its way." |

## Wording changes for review (Nov 2026)

Changed while building Home against the held-out data (17 to 30 Nov). Grace Liu to review.

- `payout_scheduled`: removed "ending {last4}". The payout rows in the held-out data don't include bank digits, and the response contract has no field for them.
- `negative_after_refund`: "the catering refund" is now "a refund". In the held-out data the refund that caused the negative balance was a canceled wedding cake order, not catering.
- `no_payout`: added the reason "your next automatic payout hasn't been created yet", with the usual time daily payouts are created ({usual_time}, worked out from her past payouts). When the data has no payout times, the plainer "your next payout hasn't been created yet" is used instead. It covers money that is available but has no payout yet, which happens on 8 of the 14 held-out days.

## Notes on the source data

The balance transactions CSV (`data/`) does not reconcile: `net` often does not equal `amount` minus `fee`, some `available_on` dates are earlier than `created_at`, the running balance never goes negative, and there is no $4,200.00 payout or large catering refund. Figures in this list come from the Home capture, not the CSV. The CSV is used only for realistic descriptions, like the bank account ending 6621.
