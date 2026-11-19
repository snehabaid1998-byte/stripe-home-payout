import { NextResponse } from "next/server";
import { getPayoutState, loadSource } from "@/lib/payoutState";

export const dynamic = "force-dynamic";

// GET /api/payout-state?data=heldout&as_of=2026-11-30&account=acct_test_maria_bakery
export function GET(req: Request) {
  const p = new URL(req.url).searchParams;
  const { rows, doc } = loadSource(p.get("data") ?? "heldout");
  const account = p.get("account") ?? rows[0]?.account_id;
  return NextResponse.json(getPayoutState(rows, doc, account, p.get("as_of") ?? undefined));
}
