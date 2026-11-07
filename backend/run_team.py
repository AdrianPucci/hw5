"""Run the agent team on tickets from the command line and save the activity log.

From the HMW 5 folder:
    backend\\.venv\\Scripts\\python.exe backend\\run_team.py 101                       # one ticket
    backend\\.venv\\Scripts\\python.exe backend\\run_team.py --all --reset --end-of-day  # full run (rule 7: reset first)
    backend\\.venv\\Scripts\\python.exe backend\\run_team.py --followups               # act on human decisions

Every agent-loop step is appended to output/audit_trail.json (never wiped). Each run's summary is also
saved to output/team_runs/<task>_<time>.json. All shop data goes through the MCP server. Nothing is
paid: the agents only create approval requests, which a human approves on the dashboard.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from datetime import datetime

import audit_trail
from models import ROOT, TeamDeps, TeamRun

RUNS_DIR = ROOT / "output" / "team_runs"

END_OF_DAY = (
    "End of day. 1) Ask Inventory for its daily, weekly and monthly inventory reports (saved with save_report) "
    "and to flag anything that needs reordering. 2) Ask Accounting for its daily, weekly and monthly cash and "
    "invoice reports (saved with save_report). 3) Then save your own daily summary with consolidated metrics for "
    "the day (tickets by status, approval requests and amounts, drafts, inbox items, the audit_check result). "
    "4) Include the morning queue from human_queue() and staffing_status(): how many items wait for a person, "
    "when the next staffed window starts, and anything to act on before its deadline. "
    "Flag any discrepancies to the human."
)
FOLLOW_UPS = (
    "Work the follow-ups: call tickets_ready_for_followup(). For each human decision, finish the work it "
    "unlocks with the right agents, mark it followed up, and resolve the ticket only when nothing is pending."
)


def reset_database() -> None:
    """Rule 7: copy the original database over the working copy (the one the MCP server uses,
    CAMPUS_DB_PATH) before a full run. A file copy, not a shop action: the audit trail is kept."""
    from agents import WORKING_DB, ORIGINAL_DB

    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    print(f"Reset {WORKING_DB.name} from the original.")


async def run_task(task: str, label: str, ticket_id: int | None = None) -> dict:
    """Give the Boss a task (a ticket, the follow-ups or the end-of-day reports) and save the logs."""
    from agents import MAX_DELEGATIONS, MODEL_LABEL, mcp_call, run_agent

    status = await mcp_call("get_team_status")
    if status.get("halted"):
        print(f"Team is halted by {status.get('changed_by')}: {status.get('reason')}. A human must resume it.")
        return {}
    shop_date = (await mcp_call("get_today"))["date_today"]
    run = TeamRun(ticket_id=ticket_id, max_delegations=MAX_DELEGATIONS, task=label, shop_date=shop_date)
    run.log("start", "Boss", task=task)
    started = datetime.now()
    try:
        result = await run_agent("Boss", task, TeamDeps(run=run, chain=("Boss",)))
        final, usage, error = result.output.model_dump(), result.usage, None
    except Exception as exc:  # keep the logs even when a run fails
        final, usage, error = None, None, f"{type(exc).__name__}: {exc}"
    record = {
        "run_id": run.run_id,
        "task": label,
        "ticket_id": ticket_id,
        "shop_date": shop_date,
        "started": started.isoformat(timespec="seconds"),
        "seconds": round((datetime.now() - started).total_seconds(), 1),
        "model": MODEL_LABEL,
        "delegations": run.delegations,
        "model_requests": usage.requests if usage else None,
        "error": error,
        "final_report": final,
        "activity": run.events,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{label}_{started:%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    print_run(record, path)
    return record


async def run_ticket(ticket_id: int) -> dict:
    return await run_task(
        f"Handle ticket #{ticket_id}. Start with ticket_brief, assign it, delegate the work to the right "
        "agents, and finish with one recommendation for the human.",
        f"ticket_{ticket_id}", ticket_id,
    )


def print_run(record: dict, path) -> None:
    print(f"\n=== {record['task']}  ({record['seconds']}s, {record['delegations']} delegations, "
          f"{record['model_requests']} model calls, run {record['run_id']}) ===")
    for e in record["activity"]:
        who = e["agent"]
        if e["kind"] == "delegate":
            print(f"  {who} -> {e['to']}: {e['task'][:140]}")
        elif e["kind"] == "report":
            print(f"  {who} reports to {e['to']}: {e['report']['summary'][:160]}")
        elif e["kind"] == "tool":
            print(f"    [{who}] {e['tool']}({json.dumps(e['args'])[:90]})")
    if record["error"]:
        print("  ERROR:", record["error"])
    else:
        f = record["final_report"]
        print("\n  BOSS:", f["summary"])
        for item in f["needs_human_decision"]:
            print("  NEEDS HUMAN:", item)
        if f["approval_requests"]:
            print("  Approval requests:", f["approval_requests"])
    print(f"  Saved {path.relative_to(ROOT)}; steps appended to {audit_trail.AUDIT_PATH.relative_to(ROOT)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Campus Customs agent team")
    parser.add_argument("ticket", nargs="?", type=int, help="ticket id, e.g. 101")
    parser.add_argument("--all", action="store_true", help="run every open ticket, in ticket_queue order")
    parser.add_argument("--reset", action="store_true", help="reset the working database first (rule 7)")
    parser.add_argument("--end-of-day", action="store_true", help="after the tickets, run the end-of-day reports")
    parser.add_argument("--followups", action="store_true", help="act on human decisions (approved/rejected requests)")
    args = parser.parse_args()
    if not (args.ticket or args.all or args.end_of_day or args.followups):
        parser.error("give a ticket id, --all, --followups or --end-of-day")
    if args.reset:
        reset_database()

    from agents import _check_tool_lists, mcp_call

    await _check_tool_lists()
    if args.all:
        # ticket_queue (an MCP tool) orders them: overdue money first, then nearest due date, then oldest.
        ids = [q["ticket_id"] for q in await mcp_call("ticket_queue") if q["status"] == "open"]
    else:
        ids = [args.ticket] if args.ticket else []
    for ticket_id in ids:
        await run_ticket(ticket_id)
    if args.followups:
        await run_task(FOLLOW_UPS, "followups")
    if args.end_of_day:
        await run_task(END_OF_DAY, "end_of_day")


if __name__ == "__main__":
    asyncio.run(main())
