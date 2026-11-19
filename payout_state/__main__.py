"""Run from the repo root, for example:

python -m payout_state --account <account_id> --as-of YYYY-MM-DD --csv "data/<file 1>.csv" "data/<file 2>.csv"
"""
import argparse
import json

from .service import get_payout_state

parser = argparse.ArgumentParser(description="Pick an account's payout state.")
parser.add_argument("--csv", required=True, nargs="+", help="One or more balance transaction CSVs")
parser.add_argument("--account", required=True, help="Stripe account id")
parser.add_argument("--as-of", help="Use rows created on or before this date (YYYY-MM-DD). Default: all rows")
args = parser.parse_args()

print(json.dumps(get_payout_state(args.csv, args.account, args.as_of), indent=2, ensure_ascii=False))
