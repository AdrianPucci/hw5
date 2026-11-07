"""Data types for the Campus Customs agent team, plus the one model every agent uses."""

from __future__ import annotations

import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # never overrides PORTKEY_API_KEY from the Windows environment

AgentName = Literal["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"]
AGENT_NAMES: tuple[AgentName, ...] = ("Boss", "Inventory", "Accounting", "Facilities", "Customer Service")


def build_portkey_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey, the only model any agent uses (Adrian's rule).

    The key comes from PORTKEY_API_KEY (a Windows user environment variable), never from a file."""
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it as a Windows user environment variable.")
    base_url = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").strip()
    model_name = os.getenv("PORTKEY_MODEL", "gpt-6-luna").strip() or "gpt-6-luna"
    headers = {
        "x-portkey-api-key": api_key,
        # From HW4: a cached reply came back with a "portkey_cache_..." id the next step couldn't use.
        "x-portkey-cache-force-refresh": "true",
    }
    virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY", "").strip()
    if virtual_key:
        headers["x-portkey-virtual-key"] = virtual_key
    # A stalled connection once hung a ticket for 10 minutes: give up on a call after 90s and retry.
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, default_headers=headers, timeout=90, max_retries=3)
    return OpenAIResponsesModel(model_name, provider=OpenAIProvider(openai_client=client))


class AgentReport(BaseModel):
    """What every agent hands back when it finishes (to the Boss, to another agent, or to the human)."""

    agent: AgentName
    summary: str = Field(description="Two or three sentences: what you found and did.")
    database_facts: list[str] = Field(
        default_factory=list, description="The facts you relied on, each one from a tool result."
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="What you changed: notes, assignments, drafts, approval requests (with their numbers).",
    )
    approval_requests: list[int] = Field(
        default_factory=list, description="Ids of approval requests you created. Empty if none."
    )
    needs_human_decision: list[str] = Field(
        default_factory=list, description="Decisions only the human can make, with your recommendation."
    )


class ApprovalIn(BaseModel):
    """Body of POST /api/approvals/{id}/approve or /reject: the human who clicked the button."""

    approved_by: str = Field(min_length=1, description="The human's name (agent names are refused).")
    note: str = ""


class ReplyIn(ApprovalIn):
    """Body of POST /api/tickets/{id}/reply: what the customer answered, typed in by a human."""

    reply: str = Field(min_length=1)


class TicketRow(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    status: str
    is_open: bool
    status_reason: str | None = None
    assigned_to: str | None = None


class RunJob(BaseModel):
    """A team run started from the dashboard (one at a time)."""

    job_id: str
    ticket_id: int
    status: Literal["running", "done", "error"]
    started: str
    finished: str | None = None
    run_id: str | None = None
    error: str | None = None
    final_report: dict[str, Any] | None = None


@dataclass
class TeamRun:
    """Shared by every agent working on one ticket: the delegation budget and the activity log."""

    ticket_id: int | None
    max_delegations: int
    task: str = ""
    shop_date: str | None = None  # desk.date_today, read through MCP at the start of the run
    run_id: str = field(default_factory=lambda: uuid4().hex[:12])
    delegations: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)

    def log(self, kind: str, agent: str, **details: Any) -> None:
        self.events.append(
            {"time": datetime.now().isoformat(timespec="seconds"), "kind": kind, "agent": agent, **details}
        )


@dataclass
class TeamDeps:
    """Passed to every agent run. `chain` is who is working right now, outermost first
    (for example Boss -> Inventory -> Accounting); the last name is the agent running."""

    run: TeamRun
    chain: tuple[AgentName, ...]

    @property
    def me(self) -> AgentName:
        return self.chain[-1]
