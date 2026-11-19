// Payout state service for Home: TypeScript port of payout_state/service.py.
// Same check order, same column map, same Payout State Service Response Contract
// (specs/001-payout-status/contracts/payout-state.schema.json).
// Message wording is read from docs/payout-states.md at runtime, never copied here.
import { readFileSync } from "node:fs";
import { join } from "node:path";

export type Row = Record<string, string>;

export type PayoutState = {
  account_id: string;
  state: "negative_after_refund" | "payout_scheduled" | "pending_only" | "no_payout";
  available_balance: number;
  pending_balance: number;
  next_payout_id: string | null;
  next_payout_amount: number | null;
  next_payout_arrival_date: string | null;
  pending_available_on: string | null;
  message: string;
};

const SCHEDULED = new Set(["pending", "in_transit"]);
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function parseCsv(text: string): Row[] {
  const lines: string[][] = [];
  let field = "", row: string[] = [], quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.some((v) => v !== "")) lines.push(row);
      row = [];
    } else field += c;
  }
  if (field !== "" || row.length) { row.push(field); if (row.some((v) => v !== "")) lines.push(row); }
  const [header, ...body] = lines;
  return body.map((cells) => Object.fromEntries(header.map((h, i) => [h, cells[i] ?? ""])));
}

function tableRows(text: string, heading: string): string[][] {
  const lines = text.slice(text.indexOf(heading)).split(/\r?\n/).slice(1);
  const rows: string[][] = [];
  let inTable = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (line.startsWith("|")) {
      inTable = true;
      const cells = line.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      if (/^[-:\s]*$/.test(cells.join(""))) continue;
      rows.push(cells);
    } else if (inTable || line.startsWith("#")) break;
  }
  return rows.slice(1);
}

const unquote = (cell: string) => (cell.match(/"(.*)"/)?.[1] ?? cell);

export function loadTemplates(docText: string) {
  const messages: Record<string, string> = {};
  for (const cells of tableRows(docText, "## The four states")) messages[cells[0].replace(/`/g, "")] = unquote(cells[cells.length - 1]);
  const reasons: Record<string, string> = {};
  for (const cells of tableRows(docText, "## Reasons for `no_payout`")) reasons[cells[0]] = unquote(cells[1]);
  return { messages, reasons };
}

const txnNumber = (r: Row) => Number(r.balance_transaction_id.match(/(\d+)$/)?.[1] ?? 0);

export function cents(value: string): number {
  const neg = value.trim().startsWith("-");
  const [whole, frac = ""] = value.trim().replace("-", "").split(".");
  const c = Number(whole) * 100 + Number((frac + "00").slice(0, 2)) + (Number((frac + "000")[2]) >= 5 ? 1 : 0);
  return neg ? -c : c;
}

export function money(c: number): string {
  const abs = Math.abs(c);
  const whole = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${c < 0 ? "-" : ""}$${whole}.${String(abs % 100).padStart(2, "0")}`;
}

export function longDay(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return `${DAYS[dt.getUTCDay()]} ${d} ${MONTHS[m - 1]} ${y}`;
}

export function usualPayoutTime(rows: Row[]): string | null {
  const mins = rows
    .filter((r) => r.type === "payout" && r.created_at.length >= 16)
    .map((r) => Number(r.created_at.slice(11, 13)) * 60 + Number(r.created_at.slice(14, 16)))
    .sort((a, b) => a - b);
  if (!mins.length) return null;
  const hour = Math.floor((mins[Math.floor((mins.length - 1) / 2)] + 30) / 60) % 24;
  return `${hour % 12 || 12} ${hour < 12 ? "am" : "pm"}`;
}

function fill(template: string, values: Record<string, string>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    if (!(key in values)) throw new Error(`No value for placeholder {${key}}`);
    return values[key];
  });
}

export function selectRows(all: Row[], accountId: string, asOf?: string): Row[] {
  return all
    .filter((r) => r.account_id === accountId && (!asOf || r.created_at.slice(0, asOf.length) <= asOf))
    .sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : txnNumber(a) - txnNumber(b)));
}

export function getPayoutState(all: Row[], docText: string, accountId: string, asOf?: string): PayoutState {
  const { messages, reasons } = loadTemplates(docText);
  const rows = selectRows(all, accountId, asOf);
  if (!rows.length) throw new Error(`No transactions for ${accountId}`);

  const latest = rows[rows.length - 1];
  const today = latest.created_at.slice(0, 10);
  const available = cents(latest.running_available_balance);
  const pending = cents(latest.running_pending_balance);

  const scheduled = rows.filter((r) => r.type === "payout" && SCHEDULED.has(r.payout_status));
  const canceled = rows.some((r) => r.payout_status === "canceled");
  let next: Row | null = scheduled.length
    ? [...scheduled].sort((a, b) => (a.payout_arrival_date < b.payout_arrival_date ? -1 : a.payout_arrival_date > b.payout_arrival_date ? 1 : txnNumber(a) - txnNumber(b)))[0]
    : null;

  const pendingRows = rows.filter((r) => r.balance_status === "pending");
  let pendingAvailableOn: string | null = null;
  if (pending > 0 && pendingRows.length) {
    const future = pendingRows.map((r) => r.available_on).filter((d) => d > today).sort();
    pendingAvailableOn = future.length ? future[0] : pendingRows.map((r) => r.available_on).sort().slice(-1)[0];
  }

  let state: PayoutState["state"];
  let message: string;
  if (available < 0 && canceled) {
    state = "negative_after_refund";
    next = null;
    message = fill(messages[state], { balance: money(available) });
  } else if (available >= 0 && next) {
    state = "payout_scheduled";
    message = fill(messages[state], { amount: money(Math.abs(cents(next.amount))), arrival_date: longDay(next.payout_arrival_date) });
  } else if (available === 0 && pending > 0) {
    state = "pending_only";
    message = fill(messages[state], { pending_amount: money(pending), available_on: longDay(pendingAvailableOn!) });
  } else {
    state = "no_payout";
    const payouts = rows.filter((r) => r.type === "payout");
    const keys = Object.keys(reasons);
    let reason: string;
    if (available === 0 && pending === 0) reason = keys.find((k) => k.includes("balance is $0"))!;
    else if (payouts.length && payouts[payouts.length - 1].payout_failure_reason) reason = keys.find((k) => k.includes("bank account"))!;
    else {
      const usual = usualPayoutTime(rows);
      const key = usual ? "automatic payout hasn't been created" : "next payout hasn't been created";
      reason = keys.find((k) => k.includes(key))!;
    }
    let nextStep = reasons[reason];
    if (nextStep.includes("{usual_time}")) nextStep = fill(nextStep, { usual_time: usualPayoutTime(rows)! });
    message = fill(messages[state], { reason, next_step: nextStep });
  }

  return {
    account_id: accountId,
    state,
    available_balance: available,
    pending_balance: pending,
    next_payout_id: next ? next.payout_id : null,
    next_payout_amount: next ? Math.abs(cents(next.amount)) : null,
    next_payout_arrival_date: next ? next.payout_arrival_date : null,
    pending_available_on: pendingAvailableOn,
    message,
  };
}

export type BalanceNotice = { notice_id: string; payout_id: string; amount: number; text: string };

export function loadNotices(docText: string): Record<string, string> {
  return Object.fromEntries(tableRows(docText, "## Balance notices").map((c) => [c[0].replace(/`/g, ""), unquote(c[c.length - 1])]));
}

const RETURN_TYPES = new Set(["payout_failure", "payout_cancel"]);

// Notices for the Balance panel. Not part of the contract response.
export function balanceNotices(all: Row[], docText: string, accountId: string, asOf?: string): BalanceNotice[] {
  const notices = loadNotices(docText);
  const rows = selectRows(all, accountId, asOf);
  return rows
    .filter((r) => r.type === "payout" && r.payout_status === "failed")
    .filter((r) => !rows.some((o) => o !== r && o.payout_id === r.payout_id && (RETURN_TYPES.has(o.type) || cents(o.amount) > 0)))
    .map((r) => {
      const amount = Math.abs(cents(r.amount));
      return {
        notice_id: "failed_payout_not_returned",
        payout_id: r.payout_id,
        amount,
        text: fill(notices.failed_payout_not_returned, { amount: money(amount), date: longDay(r.created_at) }),
      };
    });
}

// Data sources shipped with the app. Files are read from the repo at runtime.
export const SOURCES: Record<string, { label: string; files: string[] }> = {
  heldout: { label: "17 to 30 Nov 2026 (held-out)", files: ["data/maria_bakery_balance_transactions_heldout_nov_2026.csv"] },
  "sep-nov": { label: "1 Sep to 16 Nov 2026", files: ["data/Maria's Bakery Balance Transactions, Sep-Nov 2026 (Stripe test mode).csv"] },
};

export function loadSource(key: string, root = process.cwd()) {
  const src = SOURCES[key] ?? SOURCES.heldout;
  const rows = src.files.flatMap((f) => parseCsv(readFileSync(join(root, f), "utf8")));
  const doc = readFileSync(join(root, "docs", "payout-states.md"), "utf8");
  return { rows, doc, label: src.label };
}
