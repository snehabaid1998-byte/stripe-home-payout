// Parity check: the TypeScript service (lib/payoutState.ts) must return exactly what the
// Python service returns, for every fixture and every day of Maria's held-out data.
// Run from the repo root: npm run parity
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import { balanceNotices, getPayoutState, parseCsv } from "../lib/payoutState.ts";

const doc = readFileSync("docs/payout-states.md", "utf8");
const cases: { file: string; account: string; asOf?: string }[] = [];
for (const f of readdirSync("tests/fixtures")) cases.push({ file: `tests/fixtures/${f}`, account: "acct_test_fixture" });
const heldout = "data/maria_bakery_balance_transactions_heldout_nov_2026.csv";
const heldRows = parseCsv(readFileSync(heldout, "utf8"));
const account = heldRows[0].account_id;
for (const day of [...new Set(heldRows.map((r) => r.created_at.slice(0, 10)))]) cases.push({ file: heldout, account, asOf: day });

const python = process.platform === "win32" ? "python" : "python3";
let failed = 0;
for (const c of cases) {
  const rows = parseCsv(readFileSync(c.file, "utf8"));
  const ts = { state: getPayoutState(rows, doc, c.account, c.asOf), notices: balanceNotices(rows, doc, c.account, c.asOf) };
  const args = ["-m", "payout_state", "--csv", c.file, "--account", c.account, ...(c.asOf ? ["--as-of", c.asOf] : [])];
  const py = {
    state: JSON.parse(execFileSync(python, args, { encoding: "utf8" })),
    notices: JSON.parse(execFileSync(python, [...args, "--notices"], { encoding: "utf8" })),
  };
  const same = JSON.stringify(ts) === JSON.stringify(py);
  if (!same) failed++;
  console.log(`${same ? "same" : "DIFF"}  ${c.file}${c.asOf ? " @ " + c.asOf : ""}  ${ts.state.state}${ts.notices.length ? " + " + ts.notices.length + " notice" : ""}`);
  if (!same) console.log("  ts:", JSON.stringify(ts), "\n  py:", JSON.stringify(py));
}
console.log(`\n${cases.length - failed}/${cases.length} match`);
process.exit(failed ? 1 : 0);
