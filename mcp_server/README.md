# Campus Customs MCP Server

## What it's for

The MCP server is the **only part of the system that reads or writes the shop's database**. The five agents (Boss, Inventory, Accounting, Facilities and Customer Service) never open the database themselves. They call this server's tools, and the server enforces the shop rules in code:

- "Today" is `desk.date_today`.
- A vendor with an open invoice can't get a new order.
- Every payment needs a human's approval.
- Cash can never go below $0.
- Messages to customers are saved as drafts only.

## Staffed hours

Human tools only run when a person is in: **Mon–Fri 9:00–5:00, Sat 10:00–12:00, closed Sunday** (table `business_hours`, Prompt 89). Agents use `staffing_status` to tell customers when a person will review, and the Boss lines up `human_queue` for the next window.

## Database file

- **Uses:** `data/campus_customs_new.db`, the **working copy**. The path is set by `CAMPUS_DB_PATH` in `.env`.
- **Never touches:** `data/campus_customs.db`, the **original**. The server refuses to start if it's pointed at it, and `audit_check` only reads it, for the starting cash.
- **To reset** the working copy to the original tickets, run `python scripts/reset_db.py` from the `HMW 5` folder.

## Adrian's three tools (Problem 3)

All three are **read-only** and use **only facts from the database**.

| Tool | What it does | Tables it reads |
|---|---|---|
| `ticket_brief(ticket_id)` | Everything about one ticket in one call: the ticket plus its stock (with held units), price (with the 15% discount floor), invoice and days overdue, whether the vendor can ship, and the lease and days until rent is due. | `desk`, `tickets`, `inventory`, `stock_holds`, `pricing`, `invoices`, `vendors`, `leases`, `approval_requests` |
| `cash_plan()` | Every bill in the database (open invoices, the next rent, requested orders) in due-date order, with the cash left after each one and any rent earmarks, so the Boss can recommend what to pay first. | `desk`, `cash_accounts`, `invoices`, `vendors`, `leases`, `approval_requests`, `cash_earmarks` |
| `audit_check()` | Proves the money adds up and that no payment skipped human approval: starting cash − payments = balance, no negative balance, and a human approver and an approved request behind every payment. | `cash_accounts` (original and working copy), `payments`, `approval_requests`, `purchase_orders`, `invoices` |

## All tools

The file defines **two MCP servers**:

- **`campus-customs`**: 48 tools. The five agents and the vibe coder (`.mcp.json`) connect here.
- **`campus-customs-human`**: 8 human-only tools. Only the dashboard connects here, so no agent or coding assistant can approve, receive or resume anything.

Agents: **B** = Boss, **I** = Inventory, **A** = Accounting, **F** = Facilities, **CS** = Customer Service. "All" = every agent.

### `campus-customs`: board and tickets

| Tool | What it does | Agents |
|---|---|---|
| `get_today` | The shop's "today" (`desk.date_today`), used for every date check | All |
| `list_tickets` | Tickets on the board, optionally by status | All |
| `get_ticket` | One ticket with its notes, drafts and approval requests | All |
| `ticket_brief` | Everything about one ticket in one call (Adrian's tool) | All |
| `ticket_timeline` | Everything already done on a ticket, in order | All |
| `ticket_queue` | Open tickets in work order: overdue money, nearest due date, oldest | All |
| `assign_ticket` | Assign a ticket to the agent who owns it | B |
| `update_ticket_status` | Move a ticket: open, in_progress, needs_approval, blocked, waiting_on_customer, resolved (not while a request is pending) | B |
| `add_ticket_note` | Add a finding or progress note | All |
| `set_blocker` / `blockers` | Record what blocks a ticket; group tickets by blocker | All |
| `tickets_ready_for_followup` | Human decisions, customer replies and received orders nobody has acted on | B |
| `mark_followed_up` / `mark_handled` | Mark a decision, reply or received order as acted on | B |

### `campus-customs`: inventory and vendors

| Tool | What it does | Agents |
|---|---|---|
| `check_stock` | Stock for a SKU (or one size), with held and available units | I, CS |
| `list_inventory` | Every SKU and size on hand | I |
| `list_shortfalls` | Items at 0, and open tickets wanting more than is on hand | I |
| `hold_stock` / `release_stock_hold` | Hold units for a ticket (nothing sold, no money) / release them | I |
| `list_vendors` | Vendors, lead times, and whether an open invoice blocks them | I, A |
| `restock_options` | Compare vendors for a restock: cost, arrival date, blocked or not | I |
| `list_purchase_orders` | Orders a human approved (ordered) or marked received | B, I, A |

### `campus-customs`: cash, invoices and requests

| Tool | What it does | Agents |
|---|---|---|
| `get_cash_balance` | Cash on hand, pending requests, and cash left if all are approved | B, A |
| `cash_plan` | Bills in due-date order with a running balance (Adrian's tool) | B, A, F |
| `audit_check` | Proves the money adds up and every payment had a human approver (Adrian's tool) | B, A |
| `list_invoices` | Vendor invoices with days overdue | A |
| `list_payments` | Payments made, each with its human approver | A |
| `check_margin` | Margin at a proposed price; lowest allowed price (15% off list) | A, CS |
| `request_invoice_payment` | Ask a human to approve paying an invoice (amount from the invoice) | A |
| `request_rent_payment` | Ask a human to approve rent (amount from the lease; only at 7 days or less before it's due) | A |
| `request_purchase_order` | Ask a human to approve a restock order (refused while the vendor has an open invoice) | A |
| `request_price_override` | Ask a human to approve a discount (never below the 15% floor) | A |
| `list_approval_requests` | Requests waiting for a human (or decided ones) | All |
| `rent_check` | The 2-week rent check: days until due, inside 14 days?, already earmarked? | A, F |
| `earmark_rent_funds` | Set cash aside for the next rent (no money moves) | A |

### `campus-customs`: facilities, customers, inbox and team

| Tool | What it does | Agents |
|---|---|---|
| `list_leases` | Leases with rent, landlord, next due date, days until due | F |
| `save_draft` / `list_drafts` | Save a customer message as a draft (never sent; refuses card numbers) / list drafts | CS |
| `customer_history` | A customer's tickets, and how many times they asked the same thing | CS |
| `flag_for_human` / `list_inbox` | Put an issue in the human's one inbox (duplicates refused) / list it | All |
| `save_report` / `list_reports` | Daily, weekly or monthly reports with database metrics | All |
| `halt_team` | Stop switch: only when something tries to make agents pay or break rules | B |
| `get_team_status` | Whether the team is running or halted | All |
| `staffing_status` | Is a person in now? Business hours and the next staffed window | All |
| `human_queue` | Everything waiting for a person, in order, with deadlines before the next window marked | B |
| `list_templates` | Message templates (acknowledgment, after_hours, backorder) | CS |

### `campus-customs-human` (dashboard only)

Every tool here needs a named human; agent names are refused.

| Tool | What it does |
|---|---|
| `approve_request` / `reject_request` | Decide a payment, purchase order or price. Approving pays in one transaction and never overdraws. |
| `receive_purchase_order` | Confirm an order arrived: adds the stock and puts it on the follow-up list |
| `approve_draft` / `reject_draft` | Review a customer message (approved drafts are still never sent by the system) |
| `record_customer_reply` | Type in a customer's answer (stored as untrusted text; goes on the follow-up list) |
| `resume_team` | Restart the team after a halt |
| `approve_template` | Sign off a message template's wording once |

## Use it from a vibe coder (Claude Code)

The connection is saved in **`.mcp.json` at the project root** (`HMW 5/.mcp.json`), under the server name `campus-customs`. Claude Code reads it when a session starts **in the `HMW 5` folder** and asks once to approve the project's MCP server. After that, the coder can call the tools directly, for example "use ticket_brief on ticket 101".

The paths in `.mcp.json` are absolute (for this computer). On another computer, change them to that computer's `HMW 5` folder.

## Run it

From this folder:

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe server.py           # stdio
.venv\Scripts\python.exe server.py --http    # http://127.0.0.1:8002/mcp
```
