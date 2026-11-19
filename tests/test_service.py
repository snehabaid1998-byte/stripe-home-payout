"""Tests for the payout state service. Run: python -m unittest -v"""
import json
import re
import unittest
from pathlib import Path

from payout_state import get_payout_state
from payout_state.templates import load_templates

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
SCHEMA = json.loads((ROOT / "specs" / "001-payout-status" / "contracts" / "payout-state.schema.json").read_text())
MARIA_CSV = ROOT / "data" / "Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv"
ACCT = "acct_test_fixture"
MESSAGES, REASONS = load_templates()


def run(name, as_of="2026-11-16"):
    return get_payout_state(FIX / f"{name}.csv", ACCT, as_of)


def check_contract(test, result):
    """Validate a result against the nine-field contract."""
    props = SCHEMA["properties"]
    test.assertEqual(set(result), set(SCHEMA["required"]), "must return exactly the contract fields")
    test.assertEqual(len(result), 9)
    for key, value in result.items():
        spec = props[key]
        types = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
        pytype = {"string": str, "null": type(None), "array": list}
        test.assertTrue(any(isinstance(value, pytype[t]) for t in types), f"{key} has wrong type")
        if "enum" in spec:
            test.assertIn(value, spec["enum"])
        if "pattern" in spec and isinstance(value, str):
            test.assertRegex(value, spec["pattern"])
        if spec.get("format") == "date" and isinstance(value, str):
            test.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$")
    test.assertTrue(all(isinstance(i, str) for i in result["source_transaction_ids"]))


class EachState(unittest.TestCase):
    def test_negative_after_refund(self):
        r = run("negative_after_refund")
        check_contract(self, r)
        self.assertEqual(r["state_id"], "negative_after_refund")
        self.assertEqual(r["amount"], "-1874.55")
        self.assertIn("-$1,874.55", r["message"])
        self.assertIn("txn_3", r["source_transaction_ids"])  # the refund
        self.assertIn("txn_4", r["source_transaction_ids"])  # the canceled payout

    def test_payout_scheduled(self):
        r = run("payout_scheduled")
        check_contract(self, r)
        self.assertEqual(r["state_id"], "payout_scheduled")
        self.assertEqual(r["message"],
                         "$4,200.00 is on its way to your bank account ending 6621. Expected to arrive 2026-11-19.")
        self.assertEqual(r["date"], "2026-11-19")

    def test_pending_only_ignores_past_dates(self):
        r = run("pending_only")
        check_contract(self, r)
        self.assertEqual(r["state_id"], "pending_only")
        self.assertEqual(r["amount"], "532.30")
        self.assertEqual(r["date"], "2026-11-19")  # 2026-11-03 is before as_of, so ignored
        self.assertIn("$532.30", r["message"])

    def test_no_payout_balance_zero(self):
        r = run("all_zero")
        check_contract(self, r)
        self.assertEqual(r["state_id"], "no_payout")
        self.assertIn("balance is $0", r["reason"])
        self.assertIn(REASONS[r["reason"]], r["message"])

    def test_no_payout_bank_needs_update(self):
        r = run("bank_needs_update")
        check_contract(self, r)
        self.assertEqual(r["state_id"], "no_payout")
        self.assertIn("bank account", r["reason"])


class Overlaps(unittest.TestCase):
    def test_negative_beats_in_transit(self):
        r = run("negative_with_in_transit")
        self.assertEqual(r["state_id"], "negative_after_refund")
        self.assertEqual(r["amount"], "-231.20")

    def test_in_transit_beats_pending(self):
        r = run("pending_with_in_transit")
        self.assertEqual(r["state_id"], "payout_scheduled")
        self.assertEqual(r["amount"], "880.00")


class NothingHardCoded(unittest.TestCase):
    def test_other_figures_flow_through(self):
        r = run("payout_scheduled_other", as_of="2026-10-05")
        self.assertEqual(r["state_id"], "payout_scheduled")
        self.assertEqual(r["amount"], "1234.56")  # earliest arrival wins over the $50 payout
        self.assertIn("ending 4242", r["message"])
        self.assertIn("2026-10-07", r["message"])

    def test_as_of_changes_the_answer(self):
        before = run("negative_after_refund", as_of="2026-11-11")
        after = run("negative_after_refund", as_of="2026-11-16")
        self.assertNotEqual(before["state_id"], after["state_id"])

    def test_code_has_no_case_values_or_wording(self):
        code = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "payout_state").glob("*.py"))
        for baked in ["4200", "4,200", "1874", "1,874", "6621", "maria"]:
            self.assertNotIn(baked, code.lower())
        for template in MESSAGES.values():
            words = re.sub(r"\{\w+\}", "", template)[:40]
            self.assertNotIn(words, code)


class MariasFile(unittest.TestCase):
    def test_runs_on_all_420_rows(self):
        r = get_payout_state(MARIA_CSV, "acct_test_maria_bakery", "2026-11-16")
        check_contract(self, r)
        self.assertIn(r["state_id"], SCHEMA["properties"]["state_id"]["enum"])


if __name__ == "__main__":
    unittest.main()
