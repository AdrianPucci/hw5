# Campus Customs Agent Dashboard Design

> What was built for Problem 8 and why (written with the AI assistant). 🛑 **Adrian:** marks my own notes.
> The dashboard is **"The Bulldog Desk"**: `frontend/` (React + Vite + TypeScript). Start it with `npm run dev` (http://localhost:5173); it calls the back end at http://localhost:8000.

---

## 1. The idea in one line

**A control desk where you watch five agents work a ticket in real time, and nothing touches money until you press Approve.** The design makes the agents' work easy to follow and the human's job (approve or reject) impossible to miss.

🛑 **Adrian:**

---

## 2. Brand and colors

| Color | Where | Why |
|---|---|---|
| **Yale blue** `#00356b` (deep `#001f42`) | Masthead, headings, agent avatars, ticket numbers | The anchor: it says Yale and Campus Customs at a glance, the same blue as the HW4 shop |
| **Bright yellow** `#ffd400` | The "Start the team" button, anything **in progress**, the approvals panel's top edge | Yellow means "happening now / your attention": it pulls the eye to live work and to decisions waiting for you |
| **Dark green** `#0f5a32` (Adrian's change, Prompt 106) | The cash card, **Resolved** agents, the Approve button, the Boss's recommendation | Green means "done / money / go": a finished agent and a safe approval read the same way |
| **Greys** `#f1f3f6` to `#1e2430` | Page background, ticket cards, "Not needed" agents, secondary text | A calm neutral base so the yellow and green carry the meaning |
| **Deep slate-navy** `#142035` to `#0a111d` (Adrian's change, Prompt 107) | The page background and the live feed | A darker, cooler night-desk look; the light cards pop forward against it, and the feed reads like a console |
| **Red** (used sparingly) | Errors, and the cash drop arrow after a payment | Only for "something went wrong" or "money left" |

**Fonts:** *Bungee* (a bold, blocky display font) for the wordmark and panel titles gives a pennant, game-day feel; *Open Sans* for everything you read (the same body font as the HW4 shop).

🛑 **Adrian:**

---

## 3. Layout

```
┌──────────────────────────── Masthead (Yale blue, yellow underline) ────────────────────────────┐
│  [Y] CAMPUS CUSTOMS · THE BULLDOG DESK                           Shop date    $ Checking balance │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
┌ Open tickets ┐ ┌──────────── Ticket #101: Bulldog tee ──── [TEAM WORKING] ──┐ ┌ Needs your OK ┐
│ #101  open   │ │ Boss │ Inventory │ Accounting │ Facilities │ Customer Svc    │ │ Pay rent      │
│ #102  needs  │ │ (5 agent cards: status, what they're doing, what they said, │ │ $2,400        │
│ #103  open   │ │  tools used, then "What I did" when finished)               │ │ [Approve][Rej]│
│ [Start team] │ │ The Boss's recommendation (after the run)                   │ ├ House rules ──┤
│ [Reset]      │ │ Live feed (newest first)                                     │ │               │
└──────────────┘ └──────────────────────────────────────────────────────────────┘ └───────────────┘
```

- **Left: the tickets** (requirement 1). One card per ticket with its number, subject, requester and status chip. Click one to select it, then **Start the team on #___** (requirement 2). Reset sits below, quieter, so it isn't hit by accident (it also asks to confirm).
- **Center: the agents** (requirements 3–5). The five agents always sit in the same order (Boss first), so your eye learns where each one lives. Under them: the Boss's recommendation and the live feed.
- **Right: the human's column** (requirement 6). Approvals first, with your name ("Approving as Adrian"), then the house rules as a reminder.
- **Top right: cash** (requirement 7). Always visible, so you see the balance drop the moment you approve.
- **Responsive:** 3 columns on a wide screen, 2 on a laptop (the approvals column moves below), 1 on a phone.

🛑 **Adrian:**

---

## 4. How each agent reads differently

Each agent is a card with an avatar (**B**, **In**, **$**, **F**, **CS**), its job in a few words, and a status pill. The **left edge and background color** tell you the state before you read a word:

| State | Looks like | When |
|---|---|---|
| Standing by | Grey edge | Before a run |
| **Working** | **Yellow edge, soft yellow glow that pulses** | The agent is reading or calling MCP tools ("Doing: Using check stock, restock options") |
| **Waiting on a teammate** | Yellow card | It delegated: "Asked Accounting: prepare the payment for invoice #501…" |
| Reported back | Green edge | It handed its report to whoever asked |
| **Resolved ✓** | **Green edge and green wash** | The run finished (requirement 4) |
| **Not needed** | Faded, dashed edge | The Boss didn't call it: the efficiency rule made visible (for example Facilities on a tee order) |
| Error | Red | Something broke |

While working, a card shows **Doing** (its latest action), **what it said** (in quotes), and chips for every **MCP tool** it used. When it finishes, the card switches to **"What I did"**: its own one-paragraph summary (requirement 5).

🛑 **Adrian:**

---

## 5. How resolved tickets and cash show up

- **Tickets:** the status chip changes color by stage: blue *open*, yellow *needs approval / blocked / waiting on customer*, green *resolved*. While the team works, the chip says **Running…**.
- **Run state:** a pill next to the ticket title: grey *No run yet*, yellow pulsing **Team working**, green **Run finished**.
- **Cash:** a white card with a green edge and a big dark-green number. After you approve, it **pops** (a quick yellow flash and scale), shows **▼ $2,400 after your approval** in red, and the line under it shows what's still waiting ("$2,400 waiting for approval · $1,000 if all approved"). Rejecting changes nothing, and the card stays still.
- **Approvals:** each request shows what it is (*Pay rent*, *Restock order*…), the amount, the ticket, who prepared it, and why. Green **Approve**, grey **Reject**. Approving is the only thing on the page that moves money.

🛑 **Adrian:**

---

## 6. The creative choices that make it feel special

- **The "Y" tile and Bungee type:** a varsity feel without using any official logo.
- **Night-desk mood:** a deep slate-navy page with a faint dot grid, so the bright cards stand out, and a dark "console" live feed with agent names in yellow.
- **Game-day texture:** a grey caution stripe under the yellow masthead border, like a sideline.
- **Living cards:** working agents glow yellow, finished ones turn green. You can tell who's doing what from across the room, which makes watching the agents fun instead of reading logs.
- **"Not needed" is shown, not hidden:** you can see the team being efficient, which builds trust in the routing.
- **The human is always in charge, visibly:** the approvals panel has its own yellow top edge, and the toast confirms "Request #1 approved and paid." When cash drops, you see exactly why.
- **Friendly copy:** "Needs your OK", "What I did", "Waiting on a teammate", "Fresh start". Plain words, no jargon.
- **Kind to everyone:** keyboard focus rings in yellow, `aria-live` updates on agent cards and cash, and animations switch off for people who prefer reduced motion.

🛑 **Adrian:**

---

## 7. How it works (for the curious)

- `src/api.ts` calls the Problem 7 routes at http://localhost:8000 (the back end's CORS allows http://localhost:5173).
- While a run is going, the page pulls new events every 1.5 seconds (`/api/events?since=…`) and the run's status every 2.5 seconds; `src/agentState.ts` turns the events into each agent card.
- When the run finishes, the page refreshes tickets, approvals and cash, and marks every agent Resolved or Not needed.
- Picking a ticket shows its most recent run, so the board is never empty after a refresh.

🛑 **Adrian:**
