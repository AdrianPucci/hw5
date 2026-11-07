# Campus Customs: Multi-Agent Shop Team

Homework 5 (AI class). Five AI agents run the Campus Customs shop together, and a human approves anything that moves money:

- **MCP server** (`mcp_server/`, FastMCP): the only unit that reads or writes the shop's SQLite database. It enforces the shop rules in code.
- **FastAPI backend** (`backend/`, PydanticAI): the agent team, **Boss, Inventory, Accounting, Facilities and Customer Service**. Any agent can delegate to any other. Every agent uses OpenAI `gpt-6-luna` through Portkey.
- **React dashboard** (`frontend/`, Vite + TypeScript): the ticket board, a live feed of the agents at work, and the approval queue.

> Status: the MCP server, the 5-agent team and the FastAPI back end (http://localhost:8000) are built and tested. The React dashboard is built (http://localhost:5173).

## Project layout

```
mcp_server/
  README.md           what the server is for, its database file and Adrian's 3 tools
  server.py           FastMCP servers: campus-customs (48 shop tools) + campus-customs-human (8 human-only tools)
  requirements.txt
backend/
  agents.py           the 5 PydanticAI agents, their MCP tool lists, delegate() with guardrails, run_agent() step audit
  audit_trail.py      append-only output/audit_trail.json (every agent-loop step)
  models.py           data types (AgentReport, TeamDeps, TeamRun) + the gpt-6-luna Portkey model
  prompts/            team.md (rules for everyone) + one prompt file per agent
  run_team.py         run the team on a ticket or all tickets -> output/team_runs/
  main.py             FastAPI back end for the dashboard (Problem 7): uvicorn main:app --reload --port 8000
  requirements.txt
frontend/             React dashboard (to build)
scripts/
  reset_db.py         restore the working database from the original (rule 7)
  add_test_tickets.py add labeled TEST tickets 901-906 (red-team) to the working copy only
  mcp_smoke.py        smoke-test Adrian's 3 tools through .mcp.json -> output/mcp_smoke.json
  harness_view.py     readable Calibri view of output/harness.md
  cash_tab.py         fill the Cash tab of output/desk_tickets.html; checks it matches cash_accounts
notes/
  assignment.md       the assignment instructions
  database_review.md  study sheet for the shop database
output/
  harness.md          design notes: shop rules, agents, delegation, database, tools, models, safety
  design.md           dashboard look and layout
  usability.md        usability features and why
  mcp_smoke.json      evidence: Adrian's 3 MCP tools called through .mcp.json, matched to the database
  desk_tickets.html   Problem 6: one tab per ticket (Expected plan / Actual), Cash and Reflection tabs
  team_runs/          one JSON activity log per ticket run (tool calls, delegations, reports)
  audit_trail.json    every agent-loop step from every run, appended (never wiped)
  Campus Customs Agents Analysis.docx   study/analysis doc: Problem 5 numbers + editable safety rules
  Agent-Rules.av.docx agent rules and process flows for Adrian to review
AI_prompts.md         log of every prompt given to the AI coding assistant
.env.example          settings to copy into .env
```

Not in this repo on purpose (see `.gitignore`): `data/` (the `campus_customs.db` database and its working copy) and `.env` (settings). The Portkey key is never stored in the repo.

## Setup

1. Put the original `campus_customs.db` in `data/`, then make the working copy:
   `python scripts/reset_db.py`
2. Copy `.env.example` to `.env`. Set `PORTKEY_API_KEY` there or as an environment variable.
3. MCP server:
   ```
   cd mcp
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe server.py --http      # http://127.0.0.1:8002/mcp
   ```

## Shop rules

1. "Today" is `desk.date_today`. 2. Lead times come from `vendors`. 3. No shipments from a vendor with an open invoice. 4. **Every payment needs human approval.** 5. No negative balances. 6. Cash only, no revenue. 7. Reset the database before a full run. 8. No real emails or vendor calls: drafts stay on the board.

Details, and where each rule is enforced, are in `output/harness.md`.
