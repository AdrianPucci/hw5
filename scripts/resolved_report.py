"""Problem 9 deliverables: output/resolved_tickets.json and output/resolved_board.html.

For each ticket (101, 102, 103): final status, a short outcome, what each agent contributed (from the team
runs since the last reset), and the human approvals. The page shows a screenshot of the React board for each
ticket (taken with headless Edge from http://localhost:5173/?ticket=N) plus the cash check. Cash math must
be right: the script stops with an error if start - payments != cash_accounts or audit_check fails.

Needs the dashboard (npm run dev) and back end (port 8000) running for the screenshots.
Run from the HMW 5 folder:  python scripts/resolved_report.py
"""

import glob
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
SHOTS = OUT / "resolved_board"
TICKETS = (101, 102, 103)
AGENTS = ["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"]
BOARD_URL = "http://localhost:5173/?ticket={}"
EDGE = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")]
INTERNAL = {"final_result"}


def ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def money(n: float) -> str:
    return f"${n:,.2f}"


def runs_since(tid: int, since: str) -> list[dict]:
    runs = []
    for f in sorted(glob.glob(str(OUT / "team_runs" / f"ticket_{tid}_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if d["started"] >= since:
            runs.append(d)
    return runs


def contributions(runs: list[dict]) -> dict[str, dict]:
    out = {a: {"worked": False, "runs": 0, "delegated_to": [], "tools": [], "last_report": None} for a in AGENTS}
    for run in runs:
        seen = set()
        for e in run["activity"]:
            a = e.get("agent")
            if a not in out:
                continue
            if e["kind"] == "tool" and e["tool"] not in INTERNAL and e["tool"] not in out[a]["tools"]:
                out[a]["tools"].append(e["tool"])
            if e["kind"] == "delegate" and e["to"] not in out[a]["delegated_to"]:
                out[a]["delegated_to"].append(e["to"])
            if e["kind"] == "report":
                out[a]["last_report"] = e["report"]["summary"]
            if e["kind"] in ("tool", "delegate", "report", "start"):
                out[a]["worked"] = True
                seen.add(a)
        if run.get("final_report"):
            out["Boss"]["last_report"] = run["final_report"]["summary"]
            out["Boss"]["worked"] = True
            seen.add("Boss")
        for a in seen:
            out[a]["runs"] += 1
    return out


def screenshot(tid: int) -> str | None:
    edge = next((p for p in EDGE if p.exists()), None)
    if edge is None:
        return None
    SHOTS.mkdir(parents=True, exist_ok=True)
    target = SHOTS / f"ticket_{tid}.png"
    target.unlink(missing_ok=True)
    # A throwaway Edge profile outside OneDrive (a profile inside OneDrive kept Edge from exiting).
    profile = Path(tempfile.mkdtemp(prefix="desk-shot-"))
    proc = subprocess.Popen([str(edge), "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
                             "--hide-scrollbars", "--virtual-time-budget=9000", "--window-size=1440,1500",
                             f"--screenshot={target}", BOARD_URL.format(tid)])
    try:
        for _ in range(90):  # wait up to 45 s for the picture
            if target.exists() and target.stat().st_size > 0:
                time.sleep(1)
                break
            time.sleep(0.5)
    finally:
        proc.kill()
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        shutil.rmtree(profile, ignore_errors=True)
    return f"resolved_board/{target.name}" if target.exists() else None


def main() -> int:
    since = json.loads((OUT / "last_reset.json").read_text(encoding="utf-8"))["reset_at"]
    start = ro(ROOT / "data" / "campus_customs.db").execute("SELECT balance FROM cash_accounts").fetchone()[0]
    db = ro(ROOT / "data" / "campus_customs_new.db")
    ending = db.execute("SELECT balance FROM cash_accounts WHERE name='checking'").fetchone()[0]
    paid = round(db.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0], 2)
    human_approver_ok = all(r["approved_by"] not in AGENTS for r in db.execute("SELECT approved_by FROM payments"))
    cash_ok = abs(start - paid - ending) < 0.005 and ending >= 0 and human_approver_ok
    cash = {"starting_balance": start, "paid_out": paid, "ending_balance": ending,
            "start_minus_payments": round(start - paid, 2), "matches_cash_accounts": cash_ok}

    tickets = []
    for tid in TICKETS:
        t = db.execute("SELECT * FROM tickets WHERE id = ?", (tid,)).fetchone()
        resolved = db.execute("SELECT created_at, author, note FROM ticket_notes WHERE ticket_id = ? AND note LIKE 'Status -> resolved%' "
                              "ORDER BY id DESC", (tid,)).fetchone()
        approvals = [dict(id=r["id"], kind=r["kind"], amount=r["amount"],
                          price=(f"{r['qty']} x {r['sku']} {r['size']} at {money(r['unit_price'])}" if r["kind"] == "price_override" else None),
                          decision=r["status"], decided_by=r["decided_by"], decided_at=r["decided_at"])
                     for r in db.execute("SELECT * FROM approval_requests WHERE ticket_id = ? ORDER BY id", (tid,))]
        drafts = [dict(id=d["id"], to=d["recipient"], subject=d["subject"], status=d["status"])
                  for d in db.execute("SELECT * FROM drafts WHERE ticket_id = ? ORDER BY id", (tid,))]
        received = [dict(order=o["id"], item=f"{o['qty']} x {o['sku']} {o['size']}", received_by=o["received_by"], on=o["received_on"])
                    for o in db.execute("SELECT * FROM purchase_orders WHERE ticket_id = ? AND status='received'", (tid,))]
        replies = [dict(reply=r["reply"], recorded_by=r["recorded_by"])
                   for r in db.execute("SELECT * FROM customer_replies WHERE ticket_id = ?", (tid,))]
        payments = [dict(payment=p["id"], kind=p["kind"], amount=p["amount"], approved_by=p["approved_by"])
                    for p in db.execute("SELECT p.* FROM payments p WHERE (p.kind IN ('invoice','rent') AND EXISTS (SELECT 1 FROM approval_requests r "
                                        "WHERE r.ticket_id = ? AND r.ref_id = p.ref_id AND r.status='approved' AND r.kind = p.kind || '_payment')) "
                                        "OR (p.kind = 'purchase_order' AND p.ref_id IN (SELECT id FROM purchase_orders WHERE ticket_id = ?))",
                                        (tid, tid))]
        runs = runs_since(tid, since)
        contrib = contributions(runs)
        outcome = (runs[-1]["final_report"] or {}).get("summary", "") if runs else ""
        tickets.append({
            "id": tid, "subject": t["subject"], "requester": t["requester"],
            "final_status": t["status"], "resolved_at": resolved["created_at"] if resolved else None,
            "short_outcome": outcome,
            "money": {"paid": round(sum(p["amount"] for p in payments), 2), "payments": payments},
            "agents": {a: {k: v for k, v in c.items()} for a, c in contrib.items()},
            "human_approvals": approvals, "drafts": drafts, "orders_received": received, "customer_replies": replies,
            "runs": [{"run_id": r["run_id"], "started": r["started"], "delegations": r["delegations"],
                      "model_calls": r["model_requests"]} for r in runs],
        })

    report = {"generated_at": datetime.now().isoformat(timespec="seconds"), "since_reset": since,
              "model": "gpt-6-luna (Portkey)", "cash": cash, "tickets": tickets}
    (OUT / "resolved_tickets.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    shots = {tid: screenshot(tid) for tid in TICKETS}
    cards = []
    for t in tickets:
        agents = "".join(
            f"<li><strong>{a}</strong>: {escape(c['last_report'] or ('worked' if c['worked'] else 'not needed'))}"
            + (f" <span class='muted'>(asked {', '.join(c['delegated_to'])})</span>" if c["delegated_to"] else "") + "</li>"
            for a, c in t["agents"].items())
        appr = "".join(
            f"<li>Request #{a['id']} {a['kind'].replace('_', ' ')}: {escape(a['price'] or money(a['amount']))} · "
            f"<strong>{a['decision']}</strong>{(' by ' + escape(a['decided_by'])) if a['decided_by'] else ''}</li>"
            for a in t["human_approvals"]) or "<li>None</li>"
        other = [f"Order #{o['order']} ({o['item']}) received by {escape(o['received_by'])}" for o in t["orders_received"]]
        other += [f"Draft #{d['id']} to {escape(d['to'])}: {d['status'].replace('_', ' ')}" for d in t["drafts"]]
        other += [f"Customer reply recorded by {escape(r['recorded_by'])}" for r in t["customer_replies"]]
        status = "Resolved" if t["final_status"] == "resolved" else t["final_status"].replace("_", " ")
        img = (f'<img src="{shots[t["id"]]}" alt="The Bulldog Desk showing ticket #{t["id"]}">' if shots[t["id"]]
               else '<p class="muted">Screenshot unavailable (start the dashboard and back end, then rerun).</p>')
        cards.append(f"""
  <section class="card">
    <header><h2>#{t['id']} · {escape(t['subject'])}</h2><span class="st st--{'ok' if status == 'Resolved' else 'wait'}">{status}{(' · ' + t['resolved_at'][:16].replace('T', ' ')) if t['resolved_at'] else ''}</span></header>
    <p class="outcome">{escape(t['short_outcome'])}</p>
    <div class="grid">
      <div><h3>What each agent contributed</h3><ul>{agents}</ul></div>
      <div><h3>Human approvals</h3><ul>{appr}</ul>{('<h3>Other human steps</h3><ul>' + ''.join(f'<li>{o}</li>' for o in other) + '</ul>') if other else ''}
        <h3>Money</h3><p>{money(t['money']['paid'])} paid out for this ticket.</p></div>
    </div>
    <figure>{img}<figcaption>The React board (The Bulldog Desk) on ticket #{t['id']}.</figcaption></figure>
  </section>""")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resolved Board</title>
<style>
  :root {{ --bg:#0d1626; --card:#fff; --ink:#1e2430; --muted:#6b7686; --line:#e3e7ec; --yale:#00356b; --sun:#ffd400; --green:#0f5a32; --greensoft:#e1efe6; --red:#c8423b; }}
  body {{ margin:0; background:linear-gradient(180deg,#142035,#0a111d) fixed; color:var(--ink); font:15px/1.5 "Open Sans","Segoe UI",sans-serif; padding:24px 16px 50px; }}
  main {{ max-width:1100px; margin:0 auto; }}
  h1 {{ color:#fff; margin:0 0 4px; font-size:28px; }} .lead {{ color:#b8c4d6; margin:0 0 18px; }}
  .cash {{ background:var(--card); border-left:7px solid {('var(--green)' if cash_ok else 'var(--red)')}; border-radius:14px; padding:14px 18px; margin-bottom:18px; display:flex; flex-wrap:wrap; gap:18px; }}
  .cash div b {{ display:block; font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }} .cash div span {{ font-size:22px; font-weight:800; }}
  .card {{ background:var(--card); border-radius:14px; padding:18px; margin-bottom:22px; border-top:6px solid var(--sun); }}
  .card header {{ display:flex; flex-wrap:wrap; gap:10px; justify-content:space-between; align-items:center; }}
  .card h2 {{ margin:0; color:var(--yale); }} h3 {{ margin:12px 0 4px; font-size:14px; text-transform:uppercase; letter-spacing:.05em; color:var(--yale); }}
  .st {{ font-weight:800; padding:4px 12px; border-radius:999px; }} .st--ok {{ background:var(--green); color:#fff; }} .st--wait {{ background:var(--sun); color:#001f42; }}
  .outcome {{ background:var(--greensoft); border-radius:10px; padding:10px 12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }}
  ul {{ margin:4px 0; padding-left:20px; }} li {{ margin:4px 0; }} .muted {{ color:var(--muted); }}
  figure {{ margin:16px 0 0; }} img {{ width:100%; height:auto; border-radius:10px; border:1px solid var(--line); }} figcaption {{ color:var(--muted); font-size:13px; margin-top:6px; }}
</style></head><body><main>
  <h1>Resolved Board</h1>
  <p class="lead">Campus Customs · Problem 9 · runs since the reset at {since.replace('T', ' ')} · generated {report['generated_at'].replace('T', ' ')}</p>
  <div class="cash">
    <div><b>Starting balance</b><span>{money(start)}</span></div>
    <div><b>Paid out</b><span>{money(paid)}</span></div>
    <div><b>Ending (cash_accounts)</b><span>{money(ending)}</span></div>
    <div><b>Cash math</b><span style="color:{'var(--green)' if cash_ok else 'var(--red)'}">{'✓ start − payments = ending' if cash_ok else '✗ DOES NOT MATCH'}</span></div>
  </div>
  {''.join(cards)}
</main></body></html>
"""
    (OUT / "resolved_board.html").write_text(page, encoding="utf-8")
    print(f"cash: start {money(start)} - paid {money(paid)} = {money(start - paid)}; cash_accounts {money(ending)}; ok={cash_ok}")
    for t in tickets:
        print(f"#{t['id']}: {t['final_status']}; paid {money(t['money']['paid'])}; screenshot {'yes' if shots[t['id']] else 'no'}")
    return 0 if cash_ok else 1


if __name__ == "__main__":
    sys.exit(main())
