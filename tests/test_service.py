"""Tests for the payout state service. Run from the repo root: python -m unittest -v"""
import re
import unittest
from pathlib import Path

from payout_state import balance_notices, get_payout_state
from payout_state.templates import load_templates
from tests.contract import contract_errors

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
DATA = ROOT / "data"
SEP_NOV = DATA / "Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv"
HELDOUT = DATA / "maria_bakery_balance_transactions_heldout_nov_2026.csv"
MARIA = "acct_test_maria_bakery"
ACCT = "acct_test_fixture"
MESSAGES, REASONS = load_templates()


def run(name, as_of=None):
    return get_payout_state(FIX / f"{name}.csv", ACCT, as_of)


class EachState(unittest.TestCase):
    def assertValid(self, r):
        self.assertEqual(contract_errors(r), [])
        self.assertNotRegex(r["message"], r"[{}]")

    def test_negative_after_refund(self):
        r = run("negative_after_refund")
        self.assertValid(r)
        self.assertEqual(r["state"], "negative_after_refund")
        self.assertEqual(r["available_balance"], -187455)
        self.assertIsNone(r["next_payout_id"])
        self.assertIn("-$1,874.55", r["message"])
        self.assertIn("canceled", r["message"])

    def test_payout_scheduled(self):
        r = run("payout_scheduled")
        self.assertValid(r)
        self.assertEqual(r["state"], "payout_scheduled")
        self.assertEqual((r["next_payout_id"], r["next_payout_amount"], r["next_payout_arrival_date"]),
                         ("po_2", 420000, "2026-11-19"))
        self.assertIn("$4,200.00", r["message"])

    def test_pending_only(self):
        r = run("pending_only")
        self.assertValid(r)
        self.assertEqual(r["state"], "pending_only")
        self.assertEqual(r["pending_balance"], 53230)
        self.assertEqual(r["pending_available_on"], "2026-11-19")  # 2026-11-03 is in the past, so skipped
        self.assertIn("$532.30", r["message"])

    def test_no_payout_balance_zero(self):
        r = run("all_zero")
        self.assertValid(r)
        self.assertEqual(r["state"], "no_payout")
        self.assertIn("balance is $0", r["message"])

    def test_no_payout_bank_needs_update(self):
        r = run("bank_needs_update")
        self.assertValid(r)
        self.assertIn("bank account needs updating", r["message"])


class Overlaps(unittest.TestCase):
    def test_negative_beats_in_transit(self):
        r = run("negative_with_in_transit")
        self.assertEqual(r["state"], "negative_after_refund")
        self.assertIsNone(r["next_payout_id"])
        self.assertEqual(contract_errors(r), [])

    def test_in_transit_beats_pending(self):
        r = run("pending_with_in_transit")
        self.assertEqual(r["state"], "payout_scheduled")
        self.assertEqual(r["next_payout_amount"], 88000)

    def test_earliest_arrival_is_next(self):
        r = run("payout_scheduled_other", as_of="2026-10-05")
        self.assertEqual((r["next_payout_id"], r["next_payout_amount"]), ("po_2", 123456))


class HeldOutNovember(unittest.TestCase):
    """Maria's held-out data, 17 to 30 Nov 2026. It is self-contained: its running balances carry on from Sep to Nov."""

    def state_on(self, day):
        return get_payout_state(HELDOUT, MARIA, day)

    def test_negative_on_20_nov(self):
        r = self.state_on("2026-11-20")
        self.assertEqual(r["state"], "negative_after_refund")
        self.assertEqual(r["available_balance"], -2492)
        self.assertEqual(contract_errors(r), [])

    def test_pending_only_on_26_nov(self):
        r = self.state_on("2026-11-26")
        self.assertEqual(r["state"], "pending_only")
        self.assertEqual((r["pending_balance"], r["pending_available_on"]), (14505, "2026-11-27"))
        self.assertEqual(contract_errors(r), [])

    def test_payout_scheduled_on_payroll_day(self):
        r = self.state_on("2026-11-30")
        self.assertEqual(r["state"], "payout_scheduled")
        self.assertEqual((r["next_payout_id"], r["next_payout_amount"], r["next_payout_arrival_date"]),
                         ("po_0090", 4000, "2026-11-30"))
        self.assertEqual(contract_errors(r), [])

    def test_money_with_no_payout_is_outside_the_contract(self):
        """17 Nov: $1,396.25 available, $387.08 pending, no payout. The contract's no_payout
        requires pending = 0, so this response can't pass it. Open question for Eryn."""
        r = self.state_on("2026-11-17")
        self.assertEqual(r["state"], "no_payout")
        self.assertIn("hasn't been created yet", r["message"])
        self.assertIn("usually created around 5 pm on business days", r["message"])
        self.assertTrue(any("pending_balance" in e for e in contract_errors(r)))


class UsualPayoutTime(unittest.TestCase):
    def test_time_comes_from_the_data(self):
        from payout_state.service import _usual_payout_time
        rows = [{"type": "payout", "created_at": t} for t in
                ["2026-11-02T08:50:00Z", "2026-11-03T09:10:00Z", "2026-11-04T09:20:00Z"]]
        self.assertEqual(_usual_payout_time(rows), "9 am")

    def test_no_times_falls_back_to_plain_reason(self):
        r = get_payout_state(SEP_NOV, MARIA, "2026-11-16")
        self.assertEqual(r["state"], "no_payout")
        self.assertIn("It will show here as soon as", r["message"])
        self.assertNotIn("usually created", r["message"])


class FailedPayoutNotice(unittest.TestCase):
    def test_held_out_failed_payout_is_flagged(self):
        notices = balance_notices(HELDOUT, MARIA, "2026-11-30")
        self.assertEqual([(n["payout_id"], n["amount"]) for n in notices], [("po_0081", 30000)])
        self.assertIn("$300.00", notices[0]["text"])
        self.assertIn("Tuesday 17 November 2026", notices[0]["text"])
        self.assertNotRegex(notices[0]["text"], r"[{}]")

    def test_no_notice_before_the_failure(self):
        self.assertEqual(balance_notices(HELDOUT, MARIA, "2026-11-17T17:00"), [])

    def test_no_notice_when_money_came_back(self):
        self.assertEqual(balance_notices(FIX / "failed_payout_returned.csv", ACCT), [])

    def test_notice_does_not_change_contract_figures(self):
        r = get_payout_state(HELDOUT, MARIA, "2026-11-20")
        self.assertEqual((r["state"], r["available_balance"]), ("negative_after_refund", -2492))


class NothingHardCoded(unittest.TestCase):
    def test_as_of_changes_the_answer(self):
        days = ["2026-11-20", "2026-11-26", "2026-11-30"]
        states = {get_payout_state(HELDOUT, MARIA, d)["state"] for d in days}
        self.assertEqual(len(states), 3)

    def test_code_has_no_case_values_or_wording(self):
        code = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "payout_state").glob("*.py"))
        for baked in ["4200", "4,200", "1874", "1,874", "6621", "maria", "po_00", "2026-11", "300.00", "30000"]:
            self.assertNotIn(baked, code.lower())
        for template in MESSAGES.values():
            words = re.sub(r"\{\w+\}", "", template)[:40]
            self.assertNotIn(words, code)


if __name__ == "__main__":
    unittest.main()
