# Homework 5: Campus Customs Multi-Agent Team

Builds on the Campus Customs shop from HMW 3 and HMW 4. The template for the three-unit layout is the Lecture 9 MCP project (`../Lecture 9/yale_som_courses_mcp`): a FastMCP server (HW5 names its folder `mcp_server/`, as the assignment requires; Lecture 9 used `mcp/`), a PydanticAI agent in a FastAPI backend, and a Vite React frontend, with model calls through Portkey.

## What we're building

- **MCP server** (`mcp_server/`): the only unit that touches the database.
- **FastAPI backend** (`backend/`): five agents (Boss, Inventory, Accounting, Facilities, Customer Service). Any agent can delegate to any other agent.
- **React dashboard** (`frontend/`): a ticket board, a live agent activity feed, and a human approval queue.
- Agents only *request* payments, purchase orders and price changes. A human approves them in the dashboard.
- Shop rules, agent responsibilities and guardrails are in `output/harness.md` (sections 3, 4 and 5).

## One tools layer: MCP only (Adrian, Prompt 74)

All shop data goes through the MCP server. The agents' tools are MCP tools (`MCPToolset` over `mcp_server.mcp`), and the backend's own checks use `agents.mcp_call(...)`. Never import shop functions or open the database from `backend/` (except the file-copy reset). Approvals are on the second, human-only MCP server `mcp_server.human_mcp`, which only the dashboard uses. Every agent-loop step is appended to `output/audit_trail.json` by `agents.run_agent` (never wipe it).

## Staffed hours (Adrian, Prompt 89)

Human tools only run Mon–Fri 9:00–5:00 and Sat 10:00–12:00 (closed Sunday), stored in `business_hours`. Agents use `staffing_status`; Customer Service tells customers the next window (no other promises) and uses `list_templates`; the Boss puts `human_queue` in the end-of-day report.

## Efficiency (Adrian, Prompt 95)

Only the agents a ticket needs: the Boss uses the routing table in `backend/prompts/boss.md` (first call by ticket type; add others only when needed), agents delegate only for a missing fact or an action they can't do, never re-verify, handle shared blockers once, and aim for 2–4 delegations (limit 6). Documented in harness section 5 and `output/desk_tickets.html`.

## No invented data (Adrian's rule, Prompt 44)

Tools and agents use **only information from the database**. No made-up numbers, dates, "what-if" orders, customer details or vendor promises. Derived values are fine only when every input comes from the database (for example `unit_cost × qty`, days overdue from `desk.date_today`). Agent prompts (especially Customer Service drafts) must say: state only database facts, and say "I don't know" otherwise.

## Shop rules (the user's; enforce in code, not just prompts)

1. "Today" is `desk.date_today`, not the system clock. Overdue = `due_date` before today.
2. Vendor lead times come from `vendors.lead_days`.
3. A vendor won't ship while it has an `open` invoice. The reorder tool must refuse.
4. **Every payment needs human approval** (points are deducted otherwise). An approved payment updates `payments` (with `approved_by`), `cash_accounts`, and the invoice status or the lease `next_due`, all in one transaction.
5. The pay tool refuses if there isn't enough cash. No negative balances.
6. Cash only goes out (user confirmed in Prompt 23, replacing the Prompt 15 reading). Revenue isn't modeled, so no tool adds cash.

**Adrian's decisions (Prompt 23):** the human decides cash priority, and the Boss recommends an order with its reasons. Purchase orders take cash and need approval when placed. Discounts are at most 15% off list (`MAX_DISCOUNT_PCT`; hoodie floor $49.30). Paying #501 does NOT release the size S tees: it only unblocks Bulldog, and the tee needs a new purchase order (Adrian kept the default, Prompt 39).
7. Reset the database (`scripts/reset_db.py`) before every full run.
8. No real emails or vendor calls. Drafts stay on the board.

## Deliverables (same format as HMW 4)

- **Final outcome: a public GitHub repo** (no `.env`, databases or venvs; see `.gitignore`). **`.mcp.json` IS committed** (Prompt 53): it's the vibe coder's connection to the MCP server, and the assignment wants it at the project root.
- `README.md`: what it is, layout, setup, how to run.
- `AI_prompts.md`: grouped by problem (`## Problem N: <title>` headings the user gives, `### Prompt N` entries numbered across the whole file).
- `output/harness.md` (rules, agents, delegation, database, MCP tools, approval flow, models, safety), `output/design.md` and `output/usability.md`, each with 🛑 Adrian cells.
- `notes/assignment.md`: the assignment instructions, pasted by the user one problem at a time. `notes/database_review.md`: a study sheet, not a submission file.

## Problems so far

1. **Vibe Coder Prompts** ✅ done: create `AI_prompts.md`, then work **one problem at a time**, logging each problem's title as a `## Problem N` heading. (The MCP server was built early, during Problem 1. It's kept, but from now on only build what the current problem asks for.)
2. **Study the campus database** ✅ done (Prompt 41; all 10 Adrian cells answered): `notes/database_review.md` written. Adrian writes his own answers in harness section 1 (Database: field lists plus a 🛑 Adrian cell per table, Prompt 25).

## Model (user's rule)

- **Every agent uses `gpt-6-luna` through Portkey. No other model or provider.** Read the model from `PORTKEY_MODEL` in `.env`, with `gpt-6-luna` as the default.
- `PORTKEY_API_KEY` comes from the **Windows user environment variable**, not `.env` (the HMW 4 and Lecture 9 `.env` keys are empty). Load `.env` without overriding existing variables (`load_dotenv(override=False)`, the default), and never print the key.
- Reuse `build_portkey_model()` from `../HMW 4/backend/agent.py`, including the `x-portkey-cache-force-refresh: true` header (it fixes the cached-response id bug from HW4).

## Databases: original vs. working copy

- `data/campus_customs.db` is the **original. Never write to it or point any code at it.** It's the reset point.
- `data/campus_customs_new.db` is the **working copy**. The MCP server and the backend read the path from `CAMPUS_DB_PATH` in `.env` (default `data/campus_customs_new.db`, relative to the HMW 5 folder).
- To start the tickets over: stop the servers, then run `python scripts/reset_db.py` from `HMW 5`.

## Prompt log (required for the assignment)

`AI_prompts.md` must record every prompt the user enters for this homework.

- After each user prompt, append a new `## Prompt N` entry (next number in sequence) with:
  - **User prompt:** the user's text verbatim (typos included). For screenshots, describe them in brackets, e.g. `[Screenshot of Problem 3 instructions]`. Messages the user sends mid-turn count as their own prompt.
  - **Assistant response:** a short summary (1–3 sentences) of what was explained or changed, naming any files edited.
- Never renumber, delete, or rewrite earlier entries. If later work corrects something from an earlier prompt, add a line to that earlier entry: `**Later correction (Prompt N):** <what changed>`.
- Never invent a prompt that wasn't actually entered. Mark unknown entries as not recorded.

## Working style

The user is learning. Explain the reasoning behind a change, not just the change. Assignment screenshots are sometimes cut off on purpose; don't ask for the rest. Build one unit at a time and explain each one before moving on.

## AV style for answer files (`output/harness.md`)

- Every answer the user writes is marked `🛑 **Adrian:**`; empty answer cells keep that marker so they know where to type.
- Make answers quick to read with headers, `---` dividers and **bold** key phrases. Formatting only: never change the user's words (typos stay).
- Keep the file UTF-8; Notepad/Word may re-save it as Windows-1252 or UTF-16, so check and convert back after the user edits.
- **Readable view (Prompt 35):** Adrian reads the harness as `output/harness_view.html` (Calibri, bold headers, indented sections, 🛑 cells highlighted). After every harness edit, run `python scripts/harness_view.py` to refresh it. A `.md` file can't store a font.
- On 2026-11-03 the harness was found saved as UTF-16 and locked (open in Word). Convert it back to UTF-8 once Word closes it.

## Running the app (Windows notes)

- PowerShell script execution is disabled: use `npm.cmd` and `.\.venv\Scripts\python.exe -m ...` instead of activating venvs.
- HMW 4 and Lecture 9 may already be using ports 5173, 8000, 8001 and 8010. Check which ports are free before starting servers.

## To-do list (keep updated)

- [x] Agent responsibilities written (`output/harness.md` section 4).
- [ ] Confirm with the user whether Canvas gives a starter repo or required stack.
- [x] Working database copy `data/campus_customs_new.db`, `CAMPUS_DB_PATH` in `.env` / `.env.example`, `scripts/reset_db.py`.
- [x] Shop rules recorded (harness section 3, and above).
- [x] Model settled: `gpt-6-luna` through Portkey for every agent. The key is the Windows user environment variable.
- [ ] Answers to the 4 open rule questions (invoice #501 reprint, cash priority, purchase orders, discount floor). The rule 6 wording is settled (Prompt 15).
- [x] MCP server built (`mcp_server/mcp_server.py`, 25 tools at the time, venv in `mcp_server/.venv`; the folder was renamed from `mcp/` in Prompt 50; 24-check rule test passed). Documented in harness section 6.
- [x] Problem 3: Adrian's 3 tools added (`ticket_brief`, `cash_plan`, `audit_check`; read-only, database facts only). 28 tools, all 39 checks pass (Prompts 45–47).
- [x] MCP decisions confirmed (Prompt 23). The 15% discount cap is in `mcp_server.py`, and 26 checks pass.
- [x] Invoice #501 question settled (Prompt 39): keep the default.
- [ ] Boss prompt (backend): when cash can't cover everything, recommend a priority order with reasons, and ask the human.
- [ ] `git init` and publish the public GitHub repo (`gh` must be signed in; the user runs `gh auth login`).
- [x] Problem 5: agent team built (`backend/agents.py`, `models.py`, `prompts/`, `run_team.py`; venv `backend/.venv`). Full run: all 3 tickets handled, requests #1–#3 pending (Prompts 63–64).
- [x] Adrian's reviewed rules folded into `backend/prompts/` + 10 new tools (Prompt 66).
- [x] Part B: 6 workflow tools (queue, timeline, blockers, statuses, stock holds, follow-ups); records use the shop date (Prompt 69). 46 tools.
- [x] Approvals dashboard-only (Prompt 71): `approve_request`/`reject_request`/`resume_team` are plain functions, not MCP tools. Tests call them directly.
- [x] Prompt 74: no bypass of MCP (backend checks via `mcp_call`; approvals on `human_mcp`), append-only per-step `output/audit_trail.json`.
- [x] Prompt 75: harness §6b agent/tool tables with live use counts, §9 Safety; editable safety rules in `output/Campus Customs Agents Analysis.docx` (backup copy kept for diffing). Prompt 77: Adrian approved all 20 as written; built into `prompts/` (team, customer_service, inventory, accounting) and `save_draft` card-number block. Process-issue analysis (10 issues; decisions needed on 2, 3, 4, 5, 9) in the analysis doc.
- [x] Prompt 82: issues 2–5 and 9 built as proposed (human MCP: receive_purchase_order, approve/reject_draft, record_customer_reply; rent request only at 7 days or less; partial-order rule in prompts; scripts/add_test_tickets.py, TEST tickets 901–906). 15 new checks pass.
- [x] Prompt 89: staffed hours built everywhere (business_hours, staffing_status, human_queue, list_templates, human approve_template; prompts, end of day, harness, READMEs, both Word docs). 48 shop tools + 8 human tools; red-team TEST tickets 901–906 all behaved correctly.
- [x] Problem 6 (Prompts 90–93): `output/desk_tickets.html` built: tabs #101/#102/#103 (Expected filled, Actual blank until the agents run), empty Cash and Reflection tabs, and the 10-step process in a fold-out. Awaiting Adrian's approval ("approve 101/102/103/process").
- [x] Prompt 110: Adrian approved the open-ticket process and the 3 plans; C4 = keep the backorder on #103; the 3 templates approved (seeded as approved). Still open: which adjustments (A1–A3, B1–B3, C1–C3) to apply; he chose to pick by ID.
- [ ] After the agents run: fill each ticket's Actual section from `output/team_runs/` and `audit_trail.json`. Fill Cash and Reflection only when a later problem asks.
- [ ] MORNING REVIEW with Adrian (asked Prompt 71): walk through Part B tools, the approvals change and the live run; confirm he's on board. Open questions: the #103 price for the AI Club; whether test-only tickets are OK.
- [ ] FastAPI endpoints for the dashboard (run a ticket, stream activity, approve/reject).
- [ ] Build the React dashboard (board, activity feed, approval queue).
- [x] 🛑 Adrian cells in harness section 1 (database) answered and formatted (Prompt 41).
- [ ] Ask the user to paste the Canvas instructions into `notes/assignment.md` (requested at Prompt 20).
- [ ] Harness sections 7–9 (approval flow, models, safety).

## Open Items checklist

`output/HMW5 Open Items.xlsx` (Prompt 56; same format as HW6). Add housekeeping items as they come up, update the "Now on:" line when the problem changes, and only check off Adrian's items when he decides or confirms in chat. If Excel has it open (locked), retry later and say so.

## Before submitting (zip checklist)

- Delete `output/Adrians_Next_Steps.docx` (temporary, Prompt 26) before publishing the repo, if Adrian hasn't already.

- Make sure `AI_prompts.md` and any `.md` outputs are UTF-8 (Word re-saves them as UTF-16 or Windows-1252).
- Don't include `.env` (API keys); include `.env.example` instead.
