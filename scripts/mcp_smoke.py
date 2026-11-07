"""Smoke-test Adrian's 3 MCP tools the way the vibe coder connects, and save the evidence.

Starts the server from .mcp.json (stdio), calls ticket_brief (tickets 101, 102, 103), cash_plan
and audit_check, and compares every tool output with the same values read straight from
data/campus_customs_new.db (plain SQL, not through the server). Writes output/mcp_smoke.json.
All three tools are read-only, so the working database is not changed.

Run from the HMW 5 folder (needs the server's venv):
    mcp_server\\.venv\\Scripts\\python.exe scripts\\mcp_smoke.py
"""

import asyncio
import hashlib
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".mcp.json"
OUT = ROOT / "output" / "mcp_smoke.json"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"

# Adrian's prompts that asked for this test (AI_prompts.md, Prompts 54 and 55), word for word.
ADRIAN_PROMPTS = [
    "ok. now with the vibe coder connected. Can we test each or my three MCP tools? "
    "save the evidence in output/mcp_smoke.json",
    "for each tool: include my prompts, the tool name, the tool output which will match the values "
    "in our data/campus_customs_new.db file",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def query(path: Path, sql: str, params: tuple = ()) -> list[dict]:
    """Read the database directly (read-only), independent of the MCP server."""
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def one(path: Path, sql: str, params: tuple = ()) -> dict:
    rows = query(path, sql, params)
    return rows[0] if rows else {}


def result_of(response) -> object:
    data = response.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        return data["result"]
    return data


def compare(pairs: dict) -> dict:
    """pairs: {label: (tool_value, database_value)} -> {label: {tool, database, match}}"""
    return {label: {"tool": t, "database": d, "match": t == d} for label, (t, d) in pairs.items()}


def ticket_db_values(ticket_id: int) -> dict:
    ticket = one(WORKING_DB, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    values = {"today": one(WORKING_DB, "SELECT date_today FROM desk")["date_today"], "ticket": ticket}
    if ticket.get("sku"):
        values["inventory"] = one(WORKING_DB, "SELECT * FROM inventory WHERE sku = ? AND size = ?",
                                  (ticket["sku"], ticket["size"]))
        values["pricing"] = one(WORKING_DB, "SELECT * FROM pricing WHERE sku = ?", (ticket["sku"],))
    if ticket.get("invoice_id"):
        values["invoice"] = one(WORKING_DB, "SELECT * FROM invoices WHERE id = ?", (ticket["invoice_id"],))
        values["vendor"] = one(WORKING_DB, "SELECT * FROM vendors WHERE id = ?", (values["invoice"]["vendor_id"],))
    if ticket.get("lease_id"):
        values["lease"] = one(WORKING_DB, "SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],))
    return values


def ticket_matches(out: dict, db: dict) -> dict:
    pairs = {
        "today = desk.date_today": (out["today"], db["today"]),
        "ticket row = tickets row": (out["ticket"], db["ticket"]),
    }
    if "inventory" in db:
        pairs["on_hand = inventory.qty"] = (out["stock"]["on_hand"], db["inventory"]["qty"])
        pairs["wanted = tickets.qty"] = (out["stock"]["wanted"], db["ticket"]["qty"])
        pairs["short_by = tickets.qty - inventory.qty"] = (
            out["stock"]["short_by"], max(db["ticket"]["qty"] - db["inventory"]["qty"], 0))
        pairs["unit_cost = pricing.unit_cost"] = (out["pricing"]["unit_cost"], db["pricing"]["unit_cost"])
        pairs["list_price = pricing.list_price"] = (out["pricing"]["list_price"], db["pricing"]["list_price"])
        pairs["15% floor = pricing.list_price x 0.85"] = (
            out["pricing"]["lowest_allowed_price"], round(db["pricing"]["list_price"] * 0.85, 2))
    if "invoice" in db:
        inv = db["invoice"]
        late = (date.fromisoformat(db["today"]) - date.fromisoformat(inv["due_date"])).days
        pairs["invoice amount = invoices.amount"] = (out["invoice"]["amount"], inv["amount"])
        pairs["invoice due = invoices.due_date"] = (out["invoice"]["due_date"], inv["due_date"])
        pairs["invoice status = invoices.status"] = (out["invoice"]["status"], inv["status"])
        pairs["days overdue = desk.date_today - invoices.due_date"] = (out["invoice"]["days_overdue"], max(late, 0))
        pairs["vendor = vendors.name"] = (out["invoice"]["vendor"], db["vendor"]["name"])
        pairs["vendor_can_ship = vendor has no open invoice"] = (out["vendor_can_ship"], inv["status"] != "open")
    if "lease" in db:
        lease = db["lease"]
        days = (date.fromisoformat(lease["next_due"]) - date.fromisoformat(db["today"])).days
        pairs["rent = leases.monthly_rent"] = (out["lease"]["monthly_rent"], lease["monthly_rent"])
        pairs["next due = leases.next_due"] = (out["lease"]["next_due"], lease["next_due"])
        pairs["landlord = leases.landlord"] = (out["lease"]["landlord"], lease["landlord"])
        pairs["days until due = leases.next_due - desk.date_today"] = (out["lease"]["days_until_due"], days)
        pairs["requester matches landlord"] = (
            out["lease"]["requester_matches_landlord"], db["ticket"]["requester"] == lease["landlord"])
    return compare(pairs)


def cash_db_values() -> dict:
    return {
        "cash_accounts": one(WORKING_DB, "SELECT * FROM cash_accounts WHERE name = 'checking'"),
        "open_invoices": query(WORKING_DB, "SELECT id, amount, due_date FROM invoices WHERE status = 'open' ORDER BY due_date"),
        "leases": query(WORKING_DB, "SELECT id, monthly_rent, next_due FROM leases ORDER BY next_due"),
    }


def cash_matches(out: dict, db: dict) -> dict:
    owed = sum(i["amount"] for i in db["open_invoices"]) + sum(l["monthly_rent"] for l in db["leases"])
    dated = sorted([(i["due_date"], i["amount"]) for i in db["open_invoices"]]
                   + [(l["next_due"], l["monthly_rent"]) for l in db["leases"]])
    return compare({
        "cash_balance = cash_accounts.balance": (out["cash_balance"], db["cash_accounts"]["balance"]),
        "items = open invoices + lease rent, in due-date order": (
            [(i["due"], i["amount"]) for i in out["items"] if i["due"]], dated),
        "total_owed = sum of those amounts": (out["total_owed"], owed),
        "cash left = balance - total_owed": (out["cash_left_if_all_paid"], round(db["cash_accounts"]["balance"] - owed, 2)),
    })


def audit_db_values() -> dict:
    return {
        "original_cash_accounts": one(ORIGINAL_DB, "SELECT * FROM cash_accounts WHERE name = 'checking'"),
        "working_cash_accounts": one(WORKING_DB, "SELECT * FROM cash_accounts WHERE name = 'checking'"),
        "payments": query(WORKING_DB, "SELECT * FROM payments ORDER BY id"),
        "paid_invoices": query(WORKING_DB, "SELECT id FROM invoices WHERE status = 'paid'"),
    }


def audit_matches(out: dict, db: dict) -> dict:
    return compare({
        "starting_cash = original cash_accounts.balance": (out["starting_cash"], db["original_cash_accounts"]["balance"]),
        "cash_balance = working cash_accounts.balance": (out["cash_balance"], db["working_cash_accounts"]["balance"]),
        "payments_total = sum of payments.amount": (out["payments_total"], sum(p["amount"] for p in db["payments"])),
        "all checks ok": (out["ok"], True),
    })


async def main() -> None:
    server = json.loads(CONFIG.read_text(encoding="utf-8"))["mcpServers"]["campus-customs"]
    db_before = sha256(WORKING_DB)
    calls = []

    async with Client(StdioTransport(command=server["command"], args=server["args"])) as client:
        tools = [t.name for t in await client.list_tools()]

        async def run(tool: str, args: dict, db_values: dict, matcher) -> None:
            response = await client.call_tool(tool, args, raise_on_error=False)
            output = result_of(response)
            matches = {} if response.is_error else matcher(output, db_values)
            calls.append({
                "adrian_prompts": ADRIAN_PROMPTS,
                "tool": tool,
                "arguments": args,
                "passed": not response.is_error and all(m["match"] for m in matches.values()),
                "matches_database": matches,
                "tool_output": output,
                "database_values": db_values,
            })

        for ticket_id in (101, 102, 103):
            await run("ticket_brief", {"ticket_id": ticket_id}, ticket_db_values(ticket_id), ticket_matches)
        await run("cash_plan", {}, cash_db_values(), cash_matches)
        await run("audit_check", {}, audit_db_values(), audit_matches)

    unchanged = db_before == sha256(WORKING_DB)
    evidence = {
        "test": "MCP smoke test of Adrian's 3 tools (Problem 3)",
        "adrian_prompts": ADRIAN_PROMPTS,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "connection": {
            "config_file": ".mcp.json",
            "server": "campus-customs",
            "transport": "stdio (the same way the vibe coder connects)",
            "tools_listed": len(tools),
            "adrians_tools_listed": [t for t in ("ticket_brief", "cash_plan", "audit_check") if t in tools],
        },
        "database": {
            "file": "data/campus_customs_new.db",
            "how_compared": "database_values are read with plain SQL straight from the file, not through the MCP server",
            "unchanged_by_test": unchanged,
        },
        "summary": {
            "calls": len(calls),
            "passed": sum(c["passed"] for c in calls),
            "values_compared": sum(len(c["matches_database"]) for c in calls),
            "all_passed": all(c["passed"] for c in calls) and unchanged,
        },
        "calls": calls,
    }
    OUT.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    s = evidence["summary"]
    print(f"{s['passed']}/{s['calls']} calls passed, {s['values_compared']} values match the database; "
          f"database unchanged: {unchanged}")
    for c in calls:
        bad = [k for k, m in c["matches_database"].items() if not m["match"]]
        print(("PASS " if c["passed"] else "FAIL ") + f"{c['tool']}({c['arguments']})" + (f" mismatches: {bad}" if bad else ""))
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
