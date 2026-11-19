import Link from "next/link";
import { balanceNotices, getPayoutState, loadSource, longDay, money, cents, selectRows, SOURCES, type Row } from "@/lib/payoutState";

export const dynamic = "force-dynamic";

const LOOK: Record<string, { tone: string; icon: string; tag: string; action: string }> = {
  payout_scheduled: { tone: "ok", icon: "→", tag: "Payout on its way", action: "View payout" },
  pending_only: { tone: "wait", icon: "◷", tag: "Money on the way to your balance", action: "See pending" },
  no_payout: { tone: "none", icon: "–", tag: "No payout scheduled", action: "Payout settings" },
  negative_after_refund: { tone: "neg", icon: "!", tag: "Balance below $0", action: "See the refund" },
};

type Search = Promise<{ as_of?: string; data?: string }>;

export default async function Home({ searchParams }: { searchParams: Search }) {
  const sp = await searchParams;
  const dataKey = sp.data && SOURCES[sp.data] ? sp.data : "heldout";
  const { rows: all, doc, label } = loadSource(dataKey);
  const account = all[0].account_id;
  const days = [...new Set(selectRows(all, account).map((r) => r.created_at.slice(0, 10)))];
  const asOf = sp.as_of && days.includes(sp.as_of) ? sp.as_of : days[days.length - 1];

  const s = getPayoutState(all, doc, account, asOf);
  const notices = balanceNotices(all, doc, account, asOf);
  const rows = selectRows(all, account, asOf);
  const look = LOOK[s.state];
  const neg = s.state === "negative_after_refund";

  const month = asOf.slice(0, 7);
  const monthRows = rows.filter((r) => r.created_at.startsWith(month));
  const charges = monthRows.filter((r) => r.type === "charge");
  const gross = charges.reduce((t, r) => t + cents(r.amount), 0);
  const refunds = monthRows.filter((r) => r.type === "refund").reduce((t, r) => t + cents(r.amount), 0);
  const fees = monthRows.reduce((t, r) => t + (r.type === "fee" ? cents(r.amount) : 0) - cents(r.fee || "0"), 0);
  const disputes = rows.filter((r) => r.type.includes("dispute")).length;
  const todayRows = rows.filter((r) => r.created_at.startsWith(asOf) && r.type === "charge");
  const prevDay = days[days.indexOf(asOf) - 1];
  const prevRows = prevDay ? rows.filter((r) => r.created_at.startsWith(prevDay) && r.type === "charge") : [];
  const todayTotal = todayRows.reduce((t, r) => t + cents(r.amount), 0);
  const prevTotal = prevRows.reduce((t, r) => t + cents(r.amount), 0);

  const lastRefund = [...rows].reverse().find((r) => r.type === "refund");
  const lastCancels = rows.filter((r) => r.type === "payout_cancel").slice(-2);
  const highlight = new Set(neg ? [lastRefund?.balance_transaction_id, ...lastCancels.map((r) => r.balance_transaction_id)] : []);
  const recent = [
    ...rows.filter((r) => highlight.has(r.balance_transaction_id)).reverse(),
    ...[...rows].reverse().filter((r) => !highlight.has(r.balance_transaction_id)),
  ].slice(0, 7);

  const dayStates = days.map((d) => ({ d, state: getPayoutState(all, doc, account, d).state }));

  const balanceNote =
    s.state === "payout_scheduled" ? `Next payout: ${money(s.next_payout_amount!)} · arrives ${longDay(s.next_payout_arrival_date!)}`
    : s.state === "negative_after_refund" ? "Next payout canceled to cover the refund"
    : s.pending_available_on ? `Pending becomes available ${longDay(s.pending_available_on)}`
    : "Nothing pending";

  return (
    <div className="shell">
      <nav className="side">
        <div className="acct">Maria&apos;s Bakery<span>Test mode</span></div>
        {["Home", "Balances", "Transactions", "Customers", "Product catalogue", "Payments", "Billing", "Reporting"].map((n) => (
          <div key={n} className={n === "Home" ? "item on" : "item"}>{n}</div>
        ))}
      </nav>

      <main>
        <header className="top">
          <div className="search">Search</div>
          <div className="sources">
            {Object.entries(SOURCES).map(([k, v]) => (
              <Link key={k} href={`/?data=${k}`} className={k === dataKey ? "src on" : "src"}>{v.label}</Link>
            ))}
          </div>
        </header>

        <div className="timeline" aria-label="View Home as of a day">
          {dayStates.map(({ d, state }) => (
            <Link key={d} href={`/?data=${dataKey}&as_of=${d}`} className={`day ${LOOK[state].tone} ${d === asOf ? "cur" : ""}`} title={state}>
              <b>{Number(d.slice(8))}</b><span>{state.replace(/_/g, " ")}</span>
            </Link>
          ))}
        </div>

        <h1>Home <small>as of {longDay(asOf)} · {label}</small></h1>

        <div className="grid">
          <section className={`card w12 h2 payout ${look.tone}`} data-testid="payout-status" data-state={s.state}>
            <div className="ico">{look.icon}</div>
            <div className="body">
              <div className="tag">{look.tag}</div>
              {s.state === "payout_scheduled" && (
                <div className="headline">{money(s.next_payout_amount!)} <span>arrives {longDay(s.next_payout_arrival_date!)}</span></div>
              )}
              <p className="msg">{s.message}</p>
              {neg && <div className="steps"><span className="d">Refund</span><span className="d">Payout canceled</span><span>New sales</span><span>Payouts restart above $0</span></div>}
            </div>
            <div className={s.state === "no_payout" ? "btn" : "btn ghost"}>{look.action}</div>
          </section>

          <section className="card w6 h2 bal">
            <div className="ct">Balance<em>BalanceSummaryCard</em></div>
            <div className="split">
              <div>Available<b className={s.available_balance < 0 ? "r" : ""}>{money(s.available_balance)}</b></div>
              <div>Pending<b>{money(s.pending_balance)}</b></div>
            </div>
            <div className="sub">{balanceNote}</div>
            {notices.map((n) => (
              <div key={n.payout_id} className="notice" data-testid="balance-notice">{n.text}</div>
            ))}
            <a className="lk">View balances</a>
          </section>

          <section className="card w6 h2">
            <div className="ct">Disputes<em>MetricCard</em></div>
            <div className="big">{disputes}</div>
            <div className="sub">{disputes ? "Disputes need a response" : "No disputes need a response"}</div>
            <a className="lk">Disputes</a>
          </section>

          <section className="card w12 h4">
            <div className="ct">Recent activity<em>ActivityFeed</em></div>
            {recent.map((r: Row) => (
              <div key={r.balance_transaction_id} className={`row ${highlight.has(r.balance_transaction_id) ? "hl" : ""}`}>
                <div>{r.description}<div className="s">{r.type.replace("_", " ")} · {r.created_at.slice(0, 16).replace("T", " ")}{r.payout_status ? ` · ${r.payout_status.replace("_", " ")}` : ""}</div></div>
                <div className={cents(r.amount) < 0 ? "neg" : ""}>{money(cents(r.amount))}</div>
              </div>
            ))}
          </section>

          <section className="card w6 h2 dim"><div className="ct">Net volume<em>MetricCard · this month</em></div><div className="big">{money(gross + refunds + fees)}</div><a className="lk">Net volume report</a></section>
          <section className="card w6 h2 dim"><div className="ct">Gross volume<em>MetricCard · this month</em></div><div className="big">{money(gross)}</div><a className="lk">Gross volume report</a></section>

          <section className="card w12 h3 dim">
            <div className="ct">Today<em>VolumeChartCard</em></div>
            <div className="bars">
              <div><span style={{ height: `${Math.min(100, (todayTotal / Math.max(todayTotal, prevTotal, 1)) * 100)}%` }} /><label>Today {money(todayTotal)}</label></div>
              <div><span className="prev" style={{ height: `${Math.min(100, (prevTotal / Math.max(todayTotal, prevTotal, 1)) * 100)}%` }} /><label>Previous day {money(prevTotal)}</label></div>
            </div>
          </section>

          <section className="card w6 h2 dim"><div className="ct">Successful payments<em>MetricCard · this month</em></div><div className="big">{charges.length}</div><a className="lk">Payments</a></section>
          <section className="card w6 h2 dim"><div className="ct">Failed payments<em>MetricCard</em></div><div className="big">0</div><a className="lk">Payments</a></section>
          <section className="card w6 h2 dim"><div className="ct">New customers<em>MetricCard</em></div><div className="big">—</div><div className="sub">Not in the test data</div></section>
          <section className="card w6 h2 dim"><div className="ct">Recommendations<em>PromoCard</em></div><div className="sub">Try Stripe Tax</div><a className="lk">Learn more</a></section>
          <section className="card w12 h1 dim"><div className="ct">Setup guide<em>SetupGuideBanner</em></div><div className="sub">Add your business logo to receipts</div></section>
        </div>
      </main>
    </div>
  );
}
