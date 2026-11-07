# Database Review: `data/campus_customs.db`

A study sheet for Problem 2. It's for you to read, not a submission file. Your own write-up goes in `output/harness.md` (section 1, the 🛑 Adrian cells).

SQLite database, 9 tables, one business day: **2026-08-31**. I checked the numbers below directly against the file.

```
desk (1 row: "today")

tickets (3) ──invoice_id──► invoices (1) ──vendor_id──► vendors (3)
   │  └─────lease_id──────► leases (1)
   └──sku + size──────────► inventory (10 rows) ──sku──► pricing (4)

cash_accounts (1: checking)      payments (0 rows: filled only by human-approved payments)
```

The arrows are **links between tables** (foreign keys). For example, ticket #101 points at invoice #501, which points at vendor #1 (Bulldog Print Co). Following the arrows is how an agent goes from "a customer wants a tee" to "we owe the printer money."

---

## 1. `desk`: the shop's clock

| Field | Example | Why it matters |
|---|---|---|
| `date_today` | `2026-08-31` | **Rule 1:** this is "today" for the shop. Every overdue check uses it, never your computer's date. Without it, the agents would think it's November 2026 and every bill would look months late. |
| `notes` | `NULL` | Empty. Room for a note to the team. |

## 2. `tickets`: the work on the board

| Field | Example | Why it matters |
|---|---|---|
| `id` | `101` | Ticket number on the board. |
| `type` | `customer_order`, `rent_notice`, `price_override` | Tells the Boss which agent should own it. |
| `requester` | `Tauhid Zaman` | Who asked: a customer, the landlord, or a student group. Customer Service drafts replies to them. |
| `subject`, `notes` | `Email: shop rent due in 2 days.` | Free text from **outside** the shop. Agents treat it as information to check, never as instructions to follow. |
| `sku`, `size`, `qty` | `CC-TEE-WHITE`, `S`, `1` | What's being asked for. Links to `inventory`. |
| `lease_id` | `1` | Links a rent notice to the lease on file. |
| `invoice_id` | `501` | Links the tee order to the unpaid reprint bill. |
| `status` | `open` | Where it sits on the board. The MCP server uses `open → in_progress → needs_approval → resolved`. |
| `created_at` | `2026-08-31T09:15:00-04:00` | When it arrived (morning, late morning, end of day). |

**The 3 tickets:**

| # | What | What's tricky |
|---|---|---|
| 101 | Tauhid wants 1 white tee, size S | **S is 0 in stock.** The reprint invoice #501 is unpaid, and Bulldog won't ship anything new until it's paid (rule 3). |
| 102 | Landlord says rent is due in 2 days | It came by **email**. Check it against the lease: $2,400 due 2026-09-02, which matches. |
| 103 | Yale AI Club wants 20 hoodies, size M, at a discount | Only **8** M hoodies are in stock (short by 12). The discount must keep a margin above the $22 cost. |

## 3. `inventory`: stock by SKU and size

| Field | Example | Why it matters |
|---|---|---|
| `sku` + `size` | `CC-HOOD-NAVY` + `M` | Together they make the **primary key**: one row per product and size. |
| `name` | `Basic Hoodie Big Yale` | Readable product name for messages to customers. |
| `qty` | `8` | Units on hand. **0 = out of stock.** |
| `location` | `Aisle A` | Where it is in the shop. |

| Product | S | M | L | XL | One size |
|---|---|---|---|---|---|
| Hoodie `CC-HOOD-NAVY` | 4 | 8 | 14 | 6 | |
| Tee `CC-TEE-WHITE` | **0** | 5 | 3 | 2 | |
| Cap `CC-HAT-BLUE` | | | | | 40 |
| Mug `CC-MUG-CREST` | | | | | **0** |

The mug is also out of stock, but no ticket asks for it. Should Inventory flag it anyway?

## 4. `pricing`: cost and price per SKU

| SKU | `unit_cost` | `list_price` | Margin at list |
|---|---|---|---|
| Hoodie | $22.00 | $58.00 | $36 (62%) |
| Tee | $8.00 | $28.00 | $20 (71%) |
| Cap | $6.00 | $22.00 | $16 (73%) |
| Mug | $3.50 | $14.00 | $10.50 (75%) |

One price per SKU, the same for every size. `unit_cost` is what a restock costs the shop. `list_price` is what customers pay. Accounting uses both to check how deep a discount can go.

## 5. `vendors`: who can restock

| `id` | `name` | `specialty` | `lead_days` |
|---|---|---|---|
| 1 | Bulldog Print Co | apparel reprint | 5 |
| 2 | Elm City Gifts | mugs and small goods | 3 |
| 3 | QuickShip CT | local courier | 1 |

**Rule 2:** arrival date = today + `lead_days`. There's **no link from vendor to SKU**, so Inventory has to match by `specialty` (apparel → Bulldog, mugs → Elm City Gifts). QuickShip is a courier, not a supplier.

## 6. `invoices`: bills the shop owes

| Field | Example | Why it matters |
|---|---|---|
| `id` | `501` | Bill number (ticket #101 points here). |
| `vendor_id` | `1` | Bulldog Print Co. |
| `amount` | `840.0` | What's owed. |
| `due_date` | `2026-08-28` | **3 days before today, so it's overdue.** |
| `status` | `open` | Unpaid. **Rule 3:** while it's open, Bulldog won't ship new product. |
| `description` | `Rush reprint CC-TEE-WHITE S` | The bill for the size S tee reprint. |

## 7. `leases`: the shop space

One lease: **Chapel Street shop**, landlord **Elm City Properties**, **$2,400/month**, next due **2026-09-02** (2 days after today, not overdue yet). Facilities checks rent notices against this row.

## 8. `cash_accounts`: the money

One account: **checking, $3,400** as of 2026-08-31. **Rule 6:** no money comes in. **Rule 5:** it can't go below $0.

## 9. `payments`: the paper trail

Empty at the start. Each human-approved payment adds a row: `kind` (invoice, rent or purchase_order), `ref_id` (which invoice, lease or order), `amount`, `account`, `paid_at` (the shop's today) and **`approved_by` (the human's name, rule 4)**.

---

## How the 3 open tickets link to the other tables

Each ticket uses **different link columns**. The ones it doesn't need are `NULL` (empty):

| Ticket | `sku` + `size` | `lease_id` | `invoice_id` |
|---|---|---|---|
| 101 customer_order | ✅ CC-TEE-WHITE, S | — | ✅ 501 |
| 102 rent_notice | — | ✅ 1 | — |
| 103 price_override | ✅ CC-HOOD-NAVY, M | — | — |

### Ticket 101: the tee order (the longest chain)

```
tickets 101 ──sku+size──► inventory   (S tee: 0 on hand)
            ──sku───────► pricing     ($28 list)
            ──invoice_id► invoices 501 ($840, due 8/28, open = 3 days overdue)
                              └─vendor_id─► vendors 1 Bulldog Print Co (5-day lead)
```

```sql
SELECT t.id, t.qty AS wanted, i.qty AS on_hand, inv.amount, inv.due_date, inv.status, v.name, v.lead_days
FROM tickets t
JOIN inventory i ON i.sku = t.sku AND i.size = t.size
JOIN invoices inv ON inv.id = t.invoice_id
JOIN vendors v ON v.id = inv.vendor_id
WHERE t.id = 101;
```

Result: wanted 1, on hand **0**, invoice **$840 open**, due 2026-08-28, Bulldog Print Co, 5 days.

### Ticket 102: the rent notice

```
tickets 102 ──lease_id──► leases 1 (Chapel Street shop, Elm City Properties, $2,400, due 9/2)
```

```sql
SELECT t.notes, l.landlord, l.monthly_rent, l.next_due,
       julianday(l.next_due) - julianday((SELECT date_today FROM desk)) AS days_until_due
FROM tickets t JOIN leases l ON l.id = t.lease_id
WHERE t.id = 102;
```

Result: the email says "due in 2 days", and the lease agrees: **2 days** (9/2 minus 8/31). The landlord's name matches too, so this notice checks out. Notice that the query uses `desk.date_today` (rule 1), not today's real date.

### Ticket 103: the AI Club discount

```
tickets 103 ──sku+size──► inventory   (M hoodie: 8 on hand, 20 wanted → short 12)
            ──sku───────► pricing     ($22 cost, $58 list → 15% floor $49.30)
            (no vendor link: Inventory must pick one by specialty → Bulldog Print Co)
```

```sql
SELECT t.qty AS wanted, i.qty AS on_hand, t.qty - i.qty AS short_by,
       p.unit_cost, p.list_price, ROUND(p.list_price * 0.85, 2) AS floor_15pct
FROM tickets t
JOIN inventory i ON i.sku = t.sku AND i.size = t.size
JOIN pricing p ON p.sku = t.sku
WHERE t.id = 103;
```

### The hidden links (no column connects them, but they matter)

- **101 and 103 share a vendor.** Hoodies are apparel, so the 12 missing hoodies would come from **Bulldog Print Co**, the same vendor blocked by invoice #501 (rule 3). Paying #501 unblocks both tickets.
- **All three tickets draw on the same $3,400** in `cash_accounts`. That's the competition the Boss has to explain to you.

---

## The big picture: cash doesn't cover everything

| If the shop pays... | Cash left |
|---|---|
| Nothing | $3,400 |
| The overdue invoice ($840) | $2,560 |
| + Rent ($2,400) | **$160** |
| + 12 hoodies to fill the AI Club order (12 × $22 = $264) | **–$104: refused** |

That's the core decision the team has to bring to you: what gets paid first, and what has to wait.

## Tables the MCP server adds (working copy only)

`approval_requests` (the human approval queue), `purchase_orders`, `ticket_notes` (the agents' work log) and `drafts` (unsent messages), plus an `assigned_to` column on `tickets`. They exist only in `campus_customs_new.db`, and `scripts/reset_db.py` wipes them.
