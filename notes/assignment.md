# Homework 5 Assignment Instructions

> Paste the Canvas instructions here, one problem at a time. CP uses this file to check each deliverable.

---

## Problem 1: Vibe Coder Prompts ✅ Done

From Adrian (Prompt 22): create the `AI_prompts.md` file, then work the problems systematically, **one problem at a time**, logging each problem with its title.

Project overview (from chat): build a multi-agent team that runs Campus Customs, in three units that talk to each other: an MCP server, a FastAPI backend with the agent team, and a React dashboard where a human watches the agents and approves requests. Every AI call uses `gpt-6-luna` through Portkey. The final outcome is a **public GitHub repo**.

## Problem 2: Study the campus database ✅ Done

From Adrian (Prompt 24):

- **Part 1:** open `data/campus_customs.db` and look at the tables.
- **Part 2:** copy the original file to `data/campus_customs_new.db`, because later problems update that working copy. ✅ Done (Prompt 24; the two files are byte-for-byte identical).
- Study the **3 open tickets** and how they link to the other tables. See `notes/database_review.md`, "How the 3 open tickets link to the other tables".
- **Part B:** start `output/harness.md`. For each table, list its fields and leave a space for Adrian to say why the table matters for the agents. ✅ Set up (Prompt 25, harness section 1).

## Problem 3: Build the MCP server

From Adrian (Prompt 42): build the MCP server. _Full instructions not pasted yet._ The server was built early (Prompts 16 and 23); compare it against the instructions once they're pasted.

## Problem 4: Add the MCP server to the vibe coder and test each tool

From Adrian (Prompt 58): add the MCP server to the vibe coder and test each tool. Save the connection JSON in `.mcp.json` at the project root (or wherever the vibe coder keeps its local MCP server list).

## Problem 5: Build the agent team and grow the MCP tools

From Adrian (Prompt 62): build the agent team and grow the MCP tools. _Instructions not pasted yet._

- **Part A (Prompt 63):** build the team with PydanticAI: Boss, Inventory, Accounting, Facilities, Customer Service, with prompts, models and agent loops so they can delegate to each other with full connectivity. ✅ Built and run.
- **Part B (Prompt 68):** add any tools the agents need to the MCP server so they can work on open tickets. Question: what process gaps in the ticket system and the agent workflow should we address?

## Problem 6: Plan the 3 tickets

From Adrian (Prompt 90): plan the 3 tickets.

- Prompts 91–93: summarize our open-ticket process for Adrian to approve, in `output/desk_tickets.html`: a page you can double-click, with one tab per ticket (101, 102, 103), each with an **Expected** section filled in now and an **Actual** section left for after the agents run, plus empty **Cash** and **Reflection** tabs for later problems. ✅ Built; awaiting Adrian's approval.

## Problem 7: Back-End Routes

From Adrian (Prompts 96–98): in `backend/main.py`, use FastAPI routes the React dashboard (Problem 8) can call: 1) the 3 tickets, open or resolved; 2) run the agent team on a ticket id; 3) recent agent events (what each agent said, the tools used); 4) approve a payment or purchase after a human clicks Approve (the only route that changes cash); 5) the checking balance from `cash_accounts`; 6) reset the database to the original values. Start it from `backend`: `uvicorn main:app --reload --port 8000`. ✅ Built and running at http://localhost:8000.

## Problem 8: Agent Dashboard

From Adrian (Prompts 101–103): React + Vite + TypeScript in `frontend/`, calling the Problem 7 routes at http://localhost:8000 (the back end allows http://localhost:5173). At minimum: list the 3 tickets; pick one and start the team; show each agent and what it's saying/doing; mark agents resolved when the run finishes; a short summary per agent; human approval of payments/purchases; the checking balance (it drops after an approved payment). Bright yellow, grey and green, Yale touches, a Boola Boola vibe. Start with `npm run dev`. Then `output/design.md`. ✅ Built and running.

## Problem 9: Resolve the tickets

From Adrian (Prompts 111–113): reset the working database, note the starting checking balance (**$3,400**), then run tickets 101, 102 and 103 on the board until each is resolved; fill each ticket's Actual section in `output/desk_tickets.html` next to its Expected plan. Status: all 3 runs done, Actual sections filled; waiting for Adrian's approvals and other human steps on the dashboard, then follow-up runs.

---

## Shop rules (given)

See `output/harness.md` section 3.
