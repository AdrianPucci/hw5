"""Campus Customs back end (Problem 7): the FastAPI routes the React dashboard (Problem 8) calls.

Every shop read and write goes through MCP: the shop server (`agents.mcp_call`) for the board and cash,
and the human-only server (`human_mcp`) for approvals, which only this back end connects to.

Routes
  GET  /api/tickets                      the 3 tickets, open or resolved (TEST tickets only on request)
  POST /api/tickets/{ticket_id}/run      run the agent team on one ticket (in the background)
  GET  /api/runs/{job_id}, /api/runs     status of a team run
  GET  /api/events                       recent agent events: what each agent said and which tools it used
  GET  /api/approvals                    requests waiting for a human
  POST /api/approvals/{request_id}/approve   the human's Approve click: the only route that changes cash
  POST /api/approvals/{request_id}/reject    the human's Reject click: nothing is paid
  GET  /api/cash                         the checking balance from cash_accounts
  POST /api/reset                        reset the working database to the original (rule 7)

Start it from the backend folder (Adrian, Prompt 98):
    uvicorn main:app --reload --port 8000
PowerShell scripts are disabled on this computer, so use the venv's Python:
    .venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client

import audit_trail
from agents import AGENT_NAMES, human_mcp, mcp_call
from models import ApprovalIn, ReplyIn, RunJob, TicketRow
from run_team import reset_database, run_ticket

app = FastAPI(title="Campus Customs back end", version="1.0")
app.add_middleware(
    # Let the browser call these routes from the dashboard's Vite page (`npm run dev` serves
    # http://localhost:5173; Vite moves to 5174 if 5173 is taken).
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_jobs: dict[str, RunJob] = {}
_run_lock = asyncio.Lock()  # one team run at a time: the agents share one database and one budget


async def _human_call(tool: str, **args: Any) -> Any:
    """Call a human-only MCP tool (approvals). Only this back end is a client of human_mcp."""
    async with Client(human_mcp) as client:
        result = await client.call_tool(tool, args, raise_on_error=False)
    data = result.structured_content
    return data["result"] if isinstance(data, dict) and set(data) == {"result"} else data


def _refused(result: Any) -> None:
    """Turn an MCP tool's refusal into an HTTP 409 with the tool's reason."""
    if isinstance(result, dict) and result.get("ok") is False:
        raise HTTPException(status_code=409, detail=result.get("refused", "Refused"))


# ---------------------------------------------------------------------------
# 1. Tickets
# ---------------------------------------------------------------------------


@app.get("/api/tickets", response_model=list[TicketRow])
async def tickets(include_tests: bool = False) -> list[TicketRow]:
    """The shop's tickets (#101, #102, #103) and whether each is open or resolved."""
    rows = await mcp_call("list_tickets")
    out = []
    for t in rows:
        if not include_tests and str(t["requester"]).startswith("TEST -"):
            continue
        out.append(TicketRow(
            id=t["id"], type=t["type"], requester=t["requester"], subject=t["subject"], status=t["status"],
            is_open=t["status"] != "resolved", status_reason=t.get("status_reason"), assigned_to=t.get("assigned_to"),
        ))
    return out


# ---------------------------------------------------------------------------
# 2. Run the agent team on one ticket
# ---------------------------------------------------------------------------


async def _run_job(job: RunJob) -> None:
    async with _run_lock:
        try:
            record = await run_ticket(job.ticket_id)
            if not record:
                job.status, job.error = "error", "The team is halted; a human must resume it."
            else:
                job.run_id, job.final_report = record["run_id"], record["final_report"]
                job.status, job.error = ("error", record["error"]) if record["error"] else ("done", None)
        except Exception as exc:  # report it to the dashboard instead of losing it
            job.status, job.error = "error", f"{type(exc).__name__}: {exc}"
        job.finished = datetime.now().isoformat(timespec="seconds")


@app.post("/api/tickets/{ticket_id}/run", response_model=RunJob, status_code=202)
async def run_team_on_ticket(ticket_id: int) -> RunJob:
    """Start the agent team on one ticket. It runs in the background (about 1–3 minutes); poll
    /api/runs/{job_id} and /api/events to watch it. Only one run at a time."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="A team run is already in progress. Wait for it to finish.")
    if not any(t["id"] == ticket_id for t in await mcp_call("list_tickets")):
        raise HTTPException(status_code=404, detail=f"No ticket #{ticket_id}.")
    status = await mcp_call("get_team_status")
    if status.get("halted"):
        raise HTTPException(status_code=409, detail=f"The team is halted: {status.get('reason')}")
    job = RunJob(job_id=uuid4().hex[:12], ticket_id=ticket_id, status="running",
                 started=datetime.now().isoformat(timespec="seconds"))
    _jobs[job.job_id] = job
    asyncio.create_task(_run_job(job))
    return job


@app.get("/api/runs", response_model=list[RunJob])
async def runs() -> list[RunJob]:
    """Team runs started since the server started, newest first."""
    return sorted(_jobs.values(), key=lambda j: j.started, reverse=True)


@app.get("/api/runs/{job_id}", response_model=RunJob)
async def run_status(job_id: str) -> RunJob:
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"No run {job_id}.")
    return _jobs[job_id]


# ---------------------------------------------------------------------------
# 3. Recent agent events (from the append-only audit trail)
# ---------------------------------------------------------------------------


def _event(entry: dict[str, Any], index: int) -> dict[str, Any]:
    """One audit step, trimmed for the board: who, what they said, which tools they used."""
    said = entry.get("text") or []
    if entry.get("kind") == "final" and isinstance(entry.get("output"), dict):
        said = [entry["output"].get("summary", "")]
    elif entry.get("kind") == "start":
        said = [entry.get("input", "")]
    elif entry.get("kind") == "error":
        said = [entry.get("error", "")]
    return {
        "index": index,
        "time": entry.get("logged_at"),
        "run_id": entry.get("run_id"),
        "ticket_id": entry.get("ticket_id"),
        "agent": entry.get("agent"),
        "chain": entry.get("chain"),
        "kind": entry.get("kind"),
        "said": [s for s in said if s],
        "tools_called": [c.get("tool") for c in entry.get("tool_calls") or []],
        "delegations": [
            {"to": (c.get("args") or {}).get("to_agent"), "task": (c.get("args") or {}).get("task")}
            for c in entry.get("tool_calls") or [] if c.get("tool") == "delegate"
        ],
        "tool_results": [{"tool": r.get("tool"), "result": r.get("result")} for r in entry.get("results") or []],
    }


@app.get("/api/events")
async def events(limit: int = Query(50, ge=1, le=500), since: int | None = None,
                 ticket_id: int | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Recent agent-loop steps from output/audit_trail.json, newest last. Pass `since` (the
    `next_since` from the last call) to get only new events when the board refreshes."""
    try:
        rows = json.loads(audit_trail.AUDIT_PATH.read_text(encoding="utf-8")) if audit_trail.AUDIT_PATH.exists() else []
    except json.JSONDecodeError:
        rows = []
    items = [(i, e) for i, e in enumerate(rows)
             if (since is None or i >= since)
             and (ticket_id is None or e.get("ticket_id") == ticket_id)
             and (run_id is None or e.get("run_id") == run_id)]
    items = items[-limit:]
    return {"next_since": len(rows), "count": len(items), "events": [_event(e, i) for i, e in items]}


# ---------------------------------------------------------------------------
# 4. Human approval: the only route that changes cash
# ---------------------------------------------------------------------------


@app.get("/api/approvals")
async def approvals(status: str = "pending") -> list[dict[str, Any]]:
    """Requests the agents prepared (payments, purchase orders, prices), waiting for a human."""
    return await mcp_call("list_approval_requests", status=status)


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, body: ApprovalIn) -> dict[str, Any]:
    """A human clicked Approve. The agents only prepared the request; this is what pays: in one
    transaction it adds the payment (with approved_by), lowers cash, and marks the invoice paid, moves
    the lease's next due date, or places the purchase order. Refused if cash would go negative."""
    if body.approved_by.strip() in AGENT_NAMES:
        raise HTTPException(status_code=403, detail="Approvals must come from a human, not an agent.")
    result = await _human_call("approve_request", request_id=request_id, approved_by=body.approved_by, note=body.note)
    _refused(result)
    return result


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, body: ApprovalIn) -> dict[str, Any]:
    """A human clicked Reject. Nothing is paid or changed."""
    result = await _human_call("reject_request", request_id=request_id, decided_by=body.approved_by,
                               reason=body.note or "Rejected on the dashboard")
    _refused(result)
    return result


# ---------------------------------------------------------------------------
# Other human steps (Problem 9): what a person must do so tickets can resolve
# ---------------------------------------------------------------------------


@app.get("/api/purchase-orders")
async def purchase_orders(status: str | None = None) -> list[dict[str, Any]]:
    """Approved restock orders (ordered) and received ones."""
    return await mcp_call("list_purchase_orders", **({"status": status} if status else {}))


@app.post("/api/purchase-orders/{purchase_order_id}/receive")
async def receive(purchase_order_id: int, body: ApprovalIn) -> dict[str, Any]:
    """A human confirms the order arrived: the stock goes up and the ticket goes on the follow-up list."""
    result = await _human_call("receive_purchase_order", purchase_order_id=purchase_order_id,
                               received_by=body.approved_by, note=body.note)
    _refused(result)
    return result


@app.get("/api/drafts")
async def drafts() -> list[dict[str, Any]]:
    """Customer messages the agents drafted (never sent by the system)."""
    return await mcp_call("list_drafts")


@app.post("/api/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, body: ApprovalIn) -> dict[str, Any]:
    """A human approves a draft's wording; the person sends it outside the system."""
    result = await _human_call("approve_draft", draft_id=draft_id, approved_by=body.approved_by, note=body.note)
    _refused(result)
    return result


@app.post("/api/drafts/{draft_id}/reject")
async def reject_draft(draft_id: int, body: ApprovalIn) -> dict[str, Any]:
    result = await _human_call("reject_draft", draft_id=draft_id, decided_by=body.approved_by,
                               reason=body.note or "Rejected on the dashboard")
    _refused(result)
    return result




@app.post("/api/tickets/{ticket_id}/reply")
async def customer_reply(ticket_id: int, body: ReplyIn) -> dict[str, Any]:
    """A human types in what the customer answered (stored as untrusted text for the agents to check)."""
    result = await _human_call("record_customer_reply", ticket_id=ticket_id, reply=body.reply,
                               recorded_by=body.approved_by)
    _refused(result)
    return result


@app.get("/api/team")
async def team() -> dict[str, Any]:
    """Whether the team is halted, and staffed hours."""
    return {"status": await mcp_call("get_team_status"), "staffing": await mcp_call("staffing_status")}


@app.post("/api/team/resume")
async def resume(body: ApprovalIn) -> dict[str, Any]:
    """A human restarts the team after the Boss halted it."""
    result = await _human_call("resume_team", resumed_by=body.approved_by, note=body.note)
    _refused(result)
    return result


@app.get("/api/followups")
async def followups() -> list[dict[str, Any]]:
    """Human actions the team hasn't acted on yet; running the ticket again finishes them."""
    return await mcp_call("tickets_ready_for_followup")


# ---------------------------------------------------------------------------
# 5. Cash
# ---------------------------------------------------------------------------


@app.get("/api/cash")
async def cash() -> dict[str, Any]:
    """The checking balance from cash_accounts, plus what's waiting for approval."""
    return await mcp_call("get_cash_balance")


# ---------------------------------------------------------------------------
# 6. Reset (rule 7)
# ---------------------------------------------------------------------------


@app.post("/api/reset")
async def reset() -> dict[str, Any]:
    """Reset the working database to the original values for a fresh run. Refused while a team run is
    going. The audit trail is kept (append-only)."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="A team run is in progress. Reset after it finishes.")
    reset_database()
    # Remember when this fresh start happened, so reports (scripts/resolved_report.py) only count runs after it.
    (audit_trail.AUDIT_PATH.parent / "last_reset.json").write_text(
        json.dumps({"reset_at": datetime.now().isoformat(timespec="seconds")}) + "\n", encoding="utf-8")
    open_tickets = [t["id"] for t in await mcp_call("list_tickets") if t["status"] != "resolved"]
    return {"ok": True, "cash": (await mcp_call("get_cash_balance"))["balance"], "open_tickets": open_tickets,
            "team_halted": (await mcp_call("get_team_status")).get("halted", False)}


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "shop_date": (await mcp_call("get_today"))["date_today"]}
