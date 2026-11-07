"""Fill the Cash tab of output/desk_tickets.html from the working database (Problem 9, part 2).

Itemizes the money: the starting checking balance after the reset, every payment or purchase by ticket
(amount, when, who approved it and why), when each ticket resolved, and the ending balance, which must
match cash_accounts in data/campus_customs_new.db. Read-only: it never changes the database.

Run from the HMW 5 folder (any Python 3):  python scripts/cash_tab.py
Run it again after you approve payments or tickets resolve.
"""

import re
import sqlite3
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "data" / "campus_customs.db"
WORKING = ROOT / "data" / "campus_customs_new.db"
PAGE = ROOT / "output" / "desk_tickets.html"
TICKETS = (101, 102, 103)
KIND = {"invoice": "Vendor invoice payment", "rent": "Rent payment", "purchase_order": "Restock purchase"}


def ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def money(n: float) -> str:
    return f"-${abs(n):,.2f}" if n < 0 else f"${n:,.2f}"


def table_exists(db: sqlite3.Connection, name: str) -> bool:
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def ticket_for_payment(db: sqlite3.Connection, p: sqlite3.Row) -> tuple[int | None, str]:
    """Which ticket a payment belongs to, and the request's reason."""
    if p["kind"] == "purchase_order":
        r = db.execute(
            "SELECT r.ticket_id, r.reason FROM purchase_orders po JOIN approval_requests r ON r.id = po.request_id "
            "WHERE po.id = ?", (p["ref_id"],)).fetchone()
    else:
        kind = {"invoice": "invoice_payment", "rent": "rent_payment"}[p["kind"]]
        r = db.execute(
            "SELECT ticket_id, reason FROM approval_requests WHERE kind = ? AND ref_id = ? AND status = 'approved' "
            "ORDER BY id DESC", (kind, p["ref_id"])).fetchone()
    return (r["ticket_id"], r["reason"]) if r else (None, "")


def build() -> tuple[str, dict]:
    start = ro(ORIGINAL).execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]
    db = ro(WORKING)
    ending = db.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]
    shop_date = db.execute("SELECT date_today FROM desk").fetchone()[0]
    payments = db.execute("SELECT * FROM payments ORDER BY id").fetchall()
    has_requests = table_exists(db, "approval_requests")

    by_ticket: dict[int | None, list] = {}
    running = start
    ledger_rows = []
    for p in payments:
        tid, reason = ticket_for_payment(db, p) if has_requests else (None, "")
        running = round(running - p["amount"], 2)
        by_ticket.setdefault(tid, []).append((p, reason, running))
        ledger_rows.append(
            f"<tr><td>#{p['id']}</td><td>{p['paid_at']}</td><td>{'#' + str(tid) if tid else '—'}</td>"
            f"<td>{escape(KIND.get(p['kind'], p['kind']))}</td><td>{escape(p['approved_by'])}</td>"
            f"<td class='num'>{money(-p['amount'])}</td><td class='num'>{money(running)}</td></tr>")

    sections = []
    for tid in TICKETS:
        t = db.execute("SELECT subject, status FROM tickets WHERE id = ?", (tid,)).fetchone()
        resolved_note = None
        if table_exists(db, "ticket_notes"):
            resolved_note = db.execute(
                "SELECT created_at, author FROM ticket_notes WHERE ticket_id = ? AND note LIKE 'Status -> resolved%' "
                "ORDER BY id DESC", (tid,)).fetchone()
        rows = by_ticket.get(tid, [])
        spent = round(sum(p["amount"] for p, _, _ in rows), 2)
        items = "".join(
            f"<li><strong>{escape(KIND.get(p['kind'], p['kind']))}: {money(p['amount'])}</strong> on {p['paid_at']}, "
            f"approved by {escape(p['approved_by'])} (payment #{p['id']}); balance after: {money(bal)}."
            f"<br><span class='why'>Why: {escape(reason[:300])}</span></li>"
            for p, reason, bal in rows) or "<li>No money has moved for this ticket.</li>"
        pending = db.execute(
            "SELECT id, kind, amount, qty, sku, size, unit_price FROM approval_requests WHERE ticket_id = ? AND status = 'pending'",
            (tid,)).fetchall() if has_requests else []
        pend = "".join(
            f"<li>Request #{r['id']} ({r['kind'].replace('_', ' ')}): "
            + (f"{r['qty']} × {r['sku']} {r['size']} at {money(r['unit_price'])} (a price, no cash)" if r["kind"] == "price_override"
               else f"{money(r['amount'])}") + " waiting for your approval</li>"
            for r in pending)
        status = ("Resolved " + (f"on {resolved_note['created_at'][:16].replace('T', ' ')} by {escape(resolved_note['author'])}" if resolved_note else "")
                  if t["status"] == "resolved" else f"Not resolved yet ({t['status'].replace('_', ' ')})")
        sections.append(f"""
      <div class="cash-ticket">
        <h3>#{tid} · {escape(t['subject'])} <span class="cash-spent">{money(-spent) if spent else '$0.00'}</span></h3>
        <p><strong>Status:</strong> {status}</p>
        <ul>{items}</ul>
        {f'<p class="pending-h">Still waiting:</p><ul>{pend}</ul>' if pend else ''}
      </div>""")

    total = round(sum(p["amount"] for p in payments), 2)
    expected_end = round(start - total, 2)
    match = abs(expected_end - ending) < 0.005
    check = {"start": start, "payments": total, "expected_end": expected_end, "ending": ending, "match": match}
    html = f"""
    <h2 style="margin-top:0">Cash</h2>
    <p class="sub" style="margin-bottom:12px">Itemized from <code>data/campus_customs_new.db</code> (shop date {shop_date}). Built by <code>scripts/cash_tab.py</code>; run it again after approvals.</p>
    <div class="facts">
      <div class="fact"><b>1 · Starting balance (after reset)</b><span>{money(start)}</span></div>
      <div class="fact"><b>Paid out ({len(payments)} payment{'s' if len(payments) != 1 else ''})</b><span>{money(-total) if total else '$0.00'}</span></div>
      <div class="fact"><b>3 · Ending balance (cash_accounts)</b><span>{money(ending)}</span></div>
      <div class="fact"><b>Check: start − payments = ending</b><span style="color:var({'--ok-line' if match else '--stop-line'})">{'✓ Matches' if match else '✗ Does not match'}</span></div>
    </div>
    <h3>2 · By ticket</h3>
    {''.join(sections)}
    <h3>Ledger (every payment, in order)</h3>
    <div class="wrap"><table class="tbl"><thead><tr><th>Payment</th><th>Paid</th><th>Ticket</th><th>What</th><th>Approved by</th><th>Amount</th><th>Balance</th></tr></thead>
      <tbody><tr><td>—</td><td>reset</td><td>—</td><td>Starting balance</td><td>—</td><td class='num'></td><td class='num'>{money(start)}</td></tr>{''.join(ledger_rows)}
      <tr><td colspan="6"><strong>Ending balance (matches cash_accounts.checking: {'yes' if match else 'NO'})</strong></td><td class='num'><strong>{money(ending)}</strong></td></tr></tbody></table></div>
    <p style="color:var(--muted);font-size:13px;margin-top:10px">Only a human's Approve moves cash (the agents only prepare requests). No money comes in (rule 6), and cash can't go below $0 (rule 5).</p>
"""
    return html, check


CSS = """
  .cash-ticket { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin: 10px 0; }
  .cash-ticket h3 { display: flex; justify-content: space-between; gap: 10px; margin: 0 0 6px; }
  .cash-spent { font-variant-numeric: tabular-nums; color: var(--stop-line); }
  .cash-ticket .why { color: var(--muted); font-size: 13px; }
  .pending-h { margin: 8px 0 0; font-weight: 700; color: var(--human-line); }
  td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
"""

if __name__ == "__main__":
    html, check = build()
    s = PAGE.read_text(encoding="utf-8")
    start = s.index('<section class="panel" role="tabpanel" id="p-cash"')
    open_end = s.index(">", start) + 1
    close = s.index("</section>", open_end)
    s = s[:open_end] + html + "  " + s[close:]
    if ".cash-ticket {" not in s:
        s = s.replace("  details { background", CSS + "  details { background", 1)
    s = re.sub(r'(id="tab-cash"[^>]*>Cash<small>)[^<]*(</small>)', r"\1Money in and out\2", s)
    PAGE.write_text(s, encoding="utf-8", newline="\n")
    print(f"Cash tab: start ${check['start']:,.2f} - payments ${check['payments']:,.2f} = ${check['expected_end']:,.2f}; "
          f"cash_accounts ${check['ending']:,.2f}; match={check['match']}")
    sys.exit(0 if check["match"] else 1)
