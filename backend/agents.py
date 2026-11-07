"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities and Customer Service.

Each agent is a PydanticAI agent with:
  - its own prompt: prompts/team.md (rules for everyone) + prompts/<role>.md
  - the same model: gpt-6-luna through Portkey (models.build_portkey_model)
  - its own slice of the MCP server's tools (TOOLS below); the human-only approval tools are on a
    separate MCP server (human_mcp) that no agent is connected to
  - a `delegate(to_agent, task)` tool, so any agent can hand work to any other (full connectivity)

All shop data comes from the MCP server (mcp_server/server.py, database data/campus_customs_new.db).
There is no second tools layer: the agents' tools are MCP tools, and the backend's own checks (team
status, ticket queue, today's date) are MCP calls too (`mcp_call`).

The agent loop is PydanticAI's: the model calls tools until it can return an AgentReport. `run_agent`
walks that loop step by step and appends every step to output/audit_trail.json. `delegate` starts
another agent's loop inside that tool call, with these guardrails:
  - a delegation budget per ticket (MAX_DELEGATIONS)
  - no ping-pong: an agent can't delegate to itself or to anyone already in the current chain
  - one shared model-call budget for the whole ticket (MAX_MODEL_REQUESTS)
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from typing import Any

from fastmcp import Client
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ThinkingPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import RunUsage, UsageLimits

import audit_trail
from models import AGENT_NAMES, ROOT, AgentName, AgentReport, TeamDeps, build_portkey_model

sys.path.insert(0, str(ROOT / "mcp_server"))
from server import DB_PATH as WORKING_DB  # noqa: E402  (the database the MCP server uses)
from server import ORIGINAL_DB, human_mcp  # noqa: E402
from server import mcp as shop_mcp  # noqa: E402

PROMPTS = ROOT / "backend" / "prompts"
MODEL_LABEL = "gpt-6-luna (Portkey)"
MAX_DELEGATIONS = 6        # per ticket, across the whole team
MAX_MODEL_REQUESTS = 60    # per ticket, across every agent's loop

# Tools every agent can use to read the board and leave notes.
BOARD = (
    "get_today", "list_tickets", "get_ticket", "ticket_brief", "add_ticket_note", "list_approval_requests",
    "flag_for_human", "list_inbox", "save_report", "list_reports", "get_team_status",
    "ticket_timeline", "ticket_queue", "blockers", "set_blocker", "staffing_status",
)

TOOLS: dict[AgentName, tuple[str, ...]] = {
    "Boss": BOARD + (
        "assign_ticket", "update_ticket_status", "cash_plan", "audit_check", "get_cash_balance", "halt_team",
        "tickets_ready_for_followup", "mark_followed_up", "mark_handled", "list_purchase_orders", "human_queue",
    ),
    "Inventory": BOARD + (
        "check_stock", "list_inventory", "list_shortfalls", "list_vendors", "restock_options",
        "hold_stock", "release_stock_hold", "list_purchase_orders",
    ),
    "Accounting": BOARD + (
        "get_cash_balance", "cash_plan", "audit_check", "list_invoices", "list_payments", "check_margin",
        "request_invoice_payment", "request_rent_payment", "request_purchase_order", "request_price_override",
        "earmark_rent_funds", "rent_check", "list_purchase_orders", "list_vendors",
    ),
    "Facilities": BOARD + ("list_leases", "rent_check", "cash_plan"),
    "Customer Service": BOARD + (
        "check_stock", "check_margin", "save_draft", "list_drafts", "customer_history", "list_templates",
    ),
}
PROMPT_FILES: dict[AgentName, str] = {
    "Boss": "boss.md",
    "Inventory": "inventory.md",
    "Accounting": "accounting.md",
    "Facilities": "facilities.md",
    "Customer Service": "customer_service.md",
}
# Arguments that name who did something. They're always set to the calling agent, so no agent can
# sign as another one.
SIGNATURE_ARGS = ("author", "requested_by", "assigned_by")


async def mcp_call(tool: str, **args: Any) -> Any:
    """Call one shop tool through the MCP server (for the backend's own checks, outside an agent)."""
    async with Client(shop_mcp) as client:
        result = await client.call_tool(tool, args)
    data = result.structured_content
    return data["result"] if isinstance(data, dict) and set(data) == {"result"} else data


async def _check_tool_lists() -> None:
    """Every name in TOOLS must be a real shop MCP tool, and none may be a human-only tool."""
    async with Client(shop_mcp) as shop, Client(human_mcp) as human:
        shop_names = {t.name for t in await shop.list_tools()}
        human_names = {t.name for t in await human.list_tools()}
    for agent, names in TOOLS.items():
        assert set(names) <= shop_names, f"{agent}: not MCP tools: {set(names) - shop_names}"
        assert not set(names) & human_names, f"{agent} must never get human-only tools"


async def _log_and_sign(ctx: RunContext[TeamDeps], call_tool, name: str, args: dict[str, Any]):
    """Runs around every MCP tool call: signs it with the calling agent's name and logs it."""
    for key in SIGNATURE_ARGS:
        if key in args:
            args[key] = ctx.deps.me
    result = await call_tool(name, args)
    ctx.deps.run.log("tool", ctx.deps.me, tool=name, args=args, result=result)
    return result


_shop_tools = MCPToolset(shop_mcp, process_tool_call=_log_and_sign)


def _tools_for(name: AgentName):
    allowed = frozenset(TOOLS[name])
    return _shop_tools.filtered(lambda ctx, tool_def: tool_def.name in allowed)


def _audit_entry(deps: TeamDeps, step: int, kind: str, usage: RunUsage | None, **details: Any) -> dict[str, Any]:
    run = deps.run
    return {
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        "shop_date": run.shop_date,
        "run_id": run.run_id,
        "task": run.task,
        "ticket_id": run.ticket_id,
        "agent": deps.me,
        "chain": list(deps.chain),
        "step": step,
        "kind": kind,
        "model": MODEL_LABEL,
        "usage_so_far": (
            {"requests": usage.requests, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
            if usage else None
        ),
        **details,
    }


async def run_agent(name: AgentName, task: str, deps: TeamDeps, usage: RunUsage | None = None):
    """Run one agent's loop, appending every step to output/audit_trail.json as it happens.

    Steps: start (the task) -> model_response (the model's tool calls / text) -> tool_results (what the
    MCP tools returned) -> ... -> final (the AgentReport). An error is logged before it is raised."""
    step = 0
    audit_trail.append([_audit_entry(deps, step, "start", usage, input=task)])
    try:
        async with AGENTS[name].iter(
            task, deps=deps, usage=usage, usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS)
        ) as agent_run:
            async for node in agent_run:
                if Agent.is_call_tools_node(node):
                    step += 1
                    parts = node.model_response.parts
                    audit_trail.append([_audit_entry(
                        deps, step, "model_response", agent_run.usage,
                        tool_calls=[{"tool": p.tool_name, "call_id": p.tool_call_id, "args": p.args_as_dict()}
                                    for p in parts if isinstance(p, ToolCallPart)],
                        text=[p.content for p in parts if isinstance(p, TextPart) and p.content],
                        reasoning=[p.content for p in parts if isinstance(p, ThinkingPart) and p.content],
                        finish_reason=node.model_response.finish_reason,
                    )])
                elif Agent.is_model_request_node(node):
                    returns = [p for p in node.request.parts if isinstance(p, (ToolReturnPart, RetryPromptPart))]
                    if returns:
                        audit_trail.append([_audit_entry(
                            deps, step, "tool_results", agent_run.usage,
                            results=[{
                                "tool": p.tool_name, "call_id": p.tool_call_id,
                                "retry": isinstance(p, RetryPromptPart),
                                "result": audit_trail.preview(p.content),
                            } for p in returns],
                        )])
            result = agent_run.result
    except Exception as exc:
        audit_trail.append([_audit_entry(deps, step, "error", usage, error=f"{type(exc).__name__}: {exc}")])
        raise
    audit_trail.append([_audit_entry(deps, step, "final", result.usage, output=result.output.model_dump())])
    return result


async def delegate(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> dict[str, Any]:
    """Ask another agent to do part of the work, and get their report back.

    Use it when the work belongs to another agent's job. Say exactly what you need back.
    Refused if the team's delegation budget for this ticket is used up, or if that agent is
    already working on this chain (no ping-pong)."""
    run, me = ctx.deps.run, ctx.deps.me
    status = await mcp_call("get_team_status")
    if status.get("halted"):
        return {"refused": f"The team is halted by {status.get('changed_by')}: {status.get('reason')}. Stop and report."}
    if to_agent == me:
        return {"refused": "You can't delegate to yourself. Do this part yourself."}
    if to_agent in ctx.deps.chain:
        chain = " -> ".join(ctx.deps.chain)
        return {"refused": f"{to_agent} is already working on this ({chain}). No ping-pong: finish with what you have."}
    if run.delegations >= run.max_delegations:
        return {"refused": f"The team used all {run.max_delegations} delegations for this ticket. Finish with what you have."}

    run.delegations += 1
    run.log("delegate", me, to=to_agent, task=task, chain=list(ctx.deps.chain))
    # ctx.usage is shared, so the whole ticket stays inside one model-call budget.
    result = await run_agent(to_agent, task, replace(ctx.deps, chain=ctx.deps.chain + (to_agent,)), ctx.usage)
    report = result.output.model_dump()
    run.log("report", to_agent, to=me, report=report)
    return report


def _build(name: AgentName) -> Agent[TeamDeps, AgentReport]:
    instructions = (PROMPTS / "team.md").read_text(encoding="utf-8") + "\n\n" + (
        PROMPTS / PROMPT_FILES[name]
    ).read_text(encoding="utf-8")
    agent = Agent(
        build_portkey_model(),
        name=name,
        deps_type=TeamDeps,
        output_type=AgentReport,
        instructions=instructions,
        toolsets=[_tools_for(name)],
    )

    @agent.instructions
    def who_and_what(ctx: RunContext[TeamDeps]) -> str:
        others = ", ".join(a for a in AGENT_NAMES if a != name)
        ticket = ctx.deps.run.ticket_id
        return (
            f"Your agent name is {name}. Your teammates are {others}. "
            f"Chain so far: {' -> '.join(ctx.deps.chain)}. "
            + (f"You are working on ticket #{ticket}." if ticket else "")
        )

    # sequential: one delegation at a time, so agents wait their turn (Adrian's rule)
    agent.tool(delegate, sequential=True)
    return agent


AGENTS: dict[AgentName, Agent[TeamDeps, AgentReport]] = {name: _build(name) for name in AGENT_NAMES}
