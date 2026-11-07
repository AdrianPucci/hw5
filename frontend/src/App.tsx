import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { deriveAgents, latestRun } from './agentState'
import { ActivityFeed } from './components/ActivityFeed'
import { AgentCard } from './components/AgentCard'
import { ApprovalPanel } from './components/ApprovalPanel'
import { CashCard } from './components/CashCard'
import { HumanSteps } from './components/HumanSteps'
import { TicketList } from './components/TicketList'
import {
  AGENTS, type AgentEvent, type Approval, type Cash, type Draft, type FollowUp, type PurchaseOrder, type RunJob, type TeamState, type Ticket,
} from './types'

const EVENTS_EVERY_MS = 1500
const JOB_EVERY_MS = 2500

function readApprover(): string {
  try {
    return localStorage.getItem('desk.approver') ?? 'Adrian'
  } catch {
    return 'Adrian'
  }
}

export default function App() {
  const [shopDate, setShopDate] = useState<string>('')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [job, setJob] = useState<RunJob | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([]) // the shown run's events
  const [runFinished, setRunFinished] = useState(false)
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [team, setTeam] = useState<TeamState | null>(null)
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [followups, setFollowups] = useState<FollowUp[]>([])
  const [stepBusy, setStepBusy] = useState(false)
  const [lastChange, setLastChange] = useState<number | null>(null)
  const [approver, setApprover] = useState(readApprover)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [message, setMessage] = useState<{ kind: 'error' | 'ok'; text: string } | null>(null)
  const cursor = useRef(0)

  const running = job?.status === 'running'

  const refreshBoard = useCallback(async () => {
    try {
      const [t, a, c, tm, o, d, f] = await Promise.all([
        api.tickets(), api.approvals(), api.cash(), api.team(), api.purchaseOrders(), api.drafts(), api.followups(),
      ])
      setTickets(t)
      setApprovals(a)
      setCash(c)
      setTeam(tm)
      setOrders(o)
      setDrafts(d)
      setFollowups(f)
    } catch (err) {
      setMessage({ kind: 'error', text: `Can't reach the back end at http://localhost:8000 (${(err as Error).message}).` })
    }
  }, [])

  // First load: shop date, board, and the first ticket's last run.
  useEffect(() => {
    api.health().then((h) => setShopDate(h.shop_date)).catch(() => undefined)
    refreshBoard()
  }, [refreshBoard])
  useEffect(() => {
    if (selectedId !== null || !tickets.length) return
    // ?ticket=102 opens that ticket (used for the resolved-board screenshots); otherwise the first one.
    const wanted = Number(new URLSearchParams(window.location.search).get('ticket'))
    setSelectedId(tickets.some((t) => t.id === wanted) ? wanted : tickets[0].id)
  }, [tickets, selectedId])

  // Picking a ticket (when nothing is running) shows its most recent run.
  useEffect(() => {
    if (selectedId === null || running) return
    let cancelled = false
    api.events({ ticketId: selectedId, limit: 500 }).then((page) => {
      if (cancelled) return
      setEvents(latestRun(page.events))
      setRunFinished(page.events.length > 0)
    })
    return () => {
      cancelled = true
    }
  }, [selectedId, running])

  // While a run is going: new events every 1.5 s, the run's status every 2.5 s.
  useEffect(() => {
    if (!running || !job) return
    const pullEvents = async () => {
      const page = await api.events({ since: cursor.current, ticketId: job.ticket_id, limit: 500 })
      cursor.current = page.next_since
      if (page.events.length) setEvents((prev) => [...prev, ...page.events])
    }
    const pullJob = async () => {
      const latest = await api.run(job.job_id)
      if (latest.status !== 'running') {
        await pullEvents()
        setJob(latest)
        setRunFinished(true)
        await refreshBoard()
        setMessage(
          latest.status === 'done'
            ? { kind: 'ok', text: `The team finished ticket #${latest.ticket_id}. Check "Needs your OK" for anything to approve.` }
            : { kind: 'error', text: latest.error ?? 'The run stopped with an error.' },
        )
      }
    }
    const e = setInterval(() => pullEvents().catch(() => undefined), EVENTS_EVERY_MS)
    const j = setInterval(() => pullJob().catch(() => undefined), JOB_EVERY_MS)
    return () => {
      clearInterval(e)
      clearInterval(j)
    }
  }, [running, job, refreshBoard])

  const startRun = async () => {
    if (selectedId === null) return
    setMessage(null)
    try {
      const head = await api.events({ limit: 1 })
      cursor.current = head.next_since
      setEvents([])
      setRunFinished(false)
      setJob(await api.runTicket(selectedId))
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    }
  }

  const decide = async (id: number, approve: boolean) => {
    setBusyId(id)
    setMessage(null)
    const before = cash?.balance ?? null
    try {
      if (approve) await api.approve(id, approver.trim(), 'Approved on the dashboard')
      else await api.reject(id, approver.trim(), 'Rejected on the dashboard')
      await refreshBoard()
      const after = (await api.cash()).balance
      setLastChange(before !== null && approve ? after - before : null)
      setMessage({ kind: 'ok', text: approve ? `Request #${id} approved and paid.` : `Request #${id} rejected. Nothing was paid.` })
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    } finally {
      setBusyId(null)
    }
  }

  const reset = async () => {
    if (!window.confirm('Reset the shop to the original data? Tickets, requests and cash go back to the start.')) return
    try {
      await api.reset()
      setJob(null)
      setEvents([])
      setRunFinished(false)
      setLastChange(null)
      await refreshBoard()
      setMessage({ kind: 'ok', text: 'Fresh start: the shop is back to its original data.' })
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    }
  }

  // The other human steps: receive an order, review a draft, record a reply, resume the team.
  const humanStep = async (label: string, action: () => Promise<unknown>) => {
    setStepBusy(true)
    setMessage(null)
    try {
      await action()
      await refreshBoard()
      setMessage({ kind: 'ok', text: label })
    } catch (err) {
      setMessage({ kind: 'error', text: (err as Error).message })
    } finally {
      setStepBusy(false)
    }
  }

  const saveApprover = (name: string) => {
    setApprover(name)
    try {
      localStorage.setItem('desk.approver', name)
    } catch {
      /* private window: keep it in memory */
    }
  }

  const agents = useMemo(() => deriveAgents(events, runFinished && !running), [events, runFinished, running])
  const shownTicket = tickets.find((t) => t.id === (running ? job?.ticket_id : selectedId))
  const bossFinal = [...events].reverse().find((e) => e.kind === 'final' && e.agent === 'Boss')
  const needsHuman = running ? [] : (job?.final_report?.needs_human_decision ?? [])

  return (
    <div className="app">
      <header className="masthead">
        <div className="masthead__brand">
          <span className="ymark" aria-hidden="true">Y</span>
          <div>
            <p className="masthead__kicker">Campus Customs · New Haven</p>
            <h1 className="masthead__title">The Bulldog Desk</h1>
          </div>
        </div>
        <div className="masthead__right">
          <div className="shopdate">
            <span>Shop date</span>
            <strong>{shopDate || '…'}</strong>
          </div>
          <CashCard cash={cash} lastChange={lastChange} />
        </div>
      </header>

      {message && (
        <div className={`toast toast--${message.kind}`} role="status">
          {message.text}
          <button type="button" onClick={() => setMessage(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <main className="layout">
        <aside className="layout__left">
          <TicketList
            tickets={tickets}
            selectedId={selectedId}
            runningId={running ? job!.ticket_id : null}
            onSelect={(id) => !running && setSelectedId(id)}
            onRun={startRun}
            canRun={!running && selectedId !== null}
            followupIds={followups.map((f) => f.ticket_id)}
          />
          <button type="button" className="btn btn--reset" onClick={reset} disabled={running}>
            Reset to the original shop data
          </button>
        </aside>

        <section className="layout__center">
          <div className="board__head">
            <h2>
              {shownTicket ? `Ticket #${shownTicket.id}: ${shownTicket.subject}` : 'The agent team'}
            </h2>
            <span className={`runstate runstate--${running ? 'running' : runFinished ? 'done' : 'idle'}`}>
              {running ? 'Team working' : runFinished ? 'Run finished' : 'No run yet'}
            </span>
          </div>
          <div className="agents">
            {AGENTS.map((name) => (
              <AgentCard key={name} view={agents[name]} />
            ))}
          </div>

          {!running && bossFinal && (
            <section className="panel panel--summary">
              <h2 className="panel__title">The Boss's recommendation</h2>
              <p>{bossFinal.said[0]}</p>
              {needsHuman.length > 0 && (
                <ul className="needs">
                  {needsHuman.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              )}
            </section>
          )}
          <ActivityFeed events={events} />
        </section>

        <aside className="layout__right">
          <ApprovalPanel approvals={approvals} approver={approver} onApprover={saveApprover} onDecide={decide} busyId={busyId} />
          <HumanSteps
            approver={approver}
            team={team}
            orders={orders}
            drafts={drafts}
            followups={followups}
            waiting={tickets.filter((t) => t.status === 'waiting_on_customer')}
            busy={stepBusy || running}
            onReceive={(id) => humanStep(`Order #${id} received: the stock is in. Run the ticket again to finish it.`, () => api.receive(id, approver.trim()))}
            onDraft={(id, ok) => humanStep(ok ? `Draft #${id} approved (send it yourself).` : `Draft #${id} rejected.`, () => api.decideDraft(id, approver.trim(), ok))}
            onReply={(tid, text) => humanStep(`Reply recorded on #${tid}. Run the ticket again so the team acts on it.`, () => api.reply(tid, approver.trim(), text))}
            onResume={() => humanStep('The team is back on.', () => api.resume(approver.trim()))}
          />
          <section className="panel panel--rules">
            <h2 className="panel__title">House rules</h2>
            <ul>
              <li>Agents only <strong>prepare</strong> payments. Your Approve is what moves cash.</li>
              <li>Facts come from the shop database only.</li>
              <li>Nothing is shipped, emailed or charged for real.</li>
              <li>People are in Mon–Fri 9–5, Sat 10–12.</li>
            </ul>
          </section>
        </aside>
      </main>

      <footer className="footer">
        <span>Campus Customs · HMW 5 · five agents on gpt-6-luna, one human in charge</span>
        <span className="footer__tag">Go Bulldogs!</span>
      </footer>
    </div>
  )
}
