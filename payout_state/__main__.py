"""Run from the repo root, for example:

python -m payout_state --csv "data/<transactions file>.csv" --account <account_id> --as-of 2026-11-16
"""
import argparse
import json

from .service import get_payout_state

parser = argparse.ArgumentParser(description="Pick an account's payout state.")
parser.add_argument("--csv", required=True, help="Balance transactions CSV")
parser.add_argument("--account", required=True, help="Stripe account id")
parser.add_argument("--as-of", required=True, help="Use rows created on or before this date (YYYY-MM-DD)")
args = parser.parse_args()

print(json.dumps(get_payout_state(args.csv, args.account, args.as_of), indent=2, ensure_ascii=False))
