import { useState } from 'react'
import type { Draft, FollowUp, PurchaseOrder, TeamState, Ticket } from '../types'

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

interface Props {
  approver: string
  team: TeamState | null
  orders: PurchaseOrder[]
  drafts: Draft[]
  followups: FollowUp[]
  waiting: Ticket[] // tickets waiting on the customer
  busy: boolean
  onReceive: (id: number) => void
  onDraft: (id: number, approve: boolean) => void
  onReply: (ticketId: number, reply: string) => void
  onResume: () => void
}

/** Everything besides payments that only a person can do: the steps that let tickets resolve. */
export function HumanSteps({ approver, team, orders, drafts, followups, waiting, busy, onReceive, onDraft, onReply, onResume }: Props) {
  const [replies, setReplies] = useState<Record<number, string>>({})
  const [openDraft, setOpenDraft] = useState<number | null>(null)
  const toReceive = orders.filter((o) => o.status === 'ordered')
  const toReview = drafts.filter((d) => d.status === 'draft')
  const followTickets = [...new Set(followups.map((f) => f.ticket_id))]
  const noName = !approver.trim()
  const nothing = !team?.status.halted && !toReceive.length && !toReview.length && !waiting.length && !followTickets.length

  return (
    <section className="panel panel--human">
      <h2 className="panel__title">Your other steps</h2>
      {team && !team.staffing.staffed_now && (
        <p className="hours">Outside staffed hours · next window {team.staffing.next_window_text}</p>
      )}
      {nothing && <p className="empty">Nothing else waiting for a person.</p>}

      {team?.status.halted && (
        <div className="step step--stop">
          <strong>The Boss halted the team.</strong>
          <p>{team.status.reason}</p>
          <button type="button" className="btn btn--approve" disabled={busy || noName} onClick={onResume}>Resume the team</button>
        </div>
      )}

      {followTickets.length > 0 && (
        <div className="step step--follow">
          <strong>Ready for follow-up:</strong> ticket{followTickets.length > 1 ? 's' : ''} {followTickets.map((t) => `#${t}`).join(', ')}.
          <p>Run the ticket again so the team finishes what your decision unlocked.</p>
        </div>
      )}

      {toReceive.map((o) => (
        <div key={o.id} className="step">
          <div className="step__top">
            <strong>Order #{o.id}: {o.qty} × {o.sku} {o.size}</strong>
            <span>{money(o.total)}</span>
          </div>
          <p>Ticket #{o.ticket_id} · ordered {o.ordered_on} · expected {o.expected_on}</p>
          <button type="button" className="btn btn--approve" disabled={busy || noName} onClick={() => onReceive(o.id)}>
            Mark received
          </button>
        </div>
      ))}

      {toReview.map((d) => (
        <div key={d.id} className="step">
          <div className="step__top">
            <strong>Draft #{d.id} to {d.recipient}</strong>
            <span>#{d.ticket_id}</span>
          </div>
          <p className="step__subject">{d.subject}</p>
          {openDraft === d.id ? (
            <pre className="draft">{d.body}</pre>
          ) : (
            <button type="button" className="linkish" onClick={() => setOpenDraft(d.id)}>Read the draft</button>
          )}
          <div className="approval__actions">
            <button type="button" className="btn btn--approve" disabled={busy || noName} onClick={() => onDraft(d.id, true)}>Approve wording</button>
            <button type="button" className="btn btn--ghost" disabled={busy || noName} onClick={() => onDraft(d.id, false)}>Reject</button>
          </div>
          <p className="hint">Approved drafts are still never sent by the system; you send them yourself.</p>
        </div>
      ))}

      {waiting.map((t) => (
        <div key={t.id} className="step">
          <strong>#{t.id} is waiting on {t.requester}</strong>
          {t.status_reason && <p>{t.status_reason}</p>}
          <textarea
            rows={3}
            placeholder="Type what the customer answered…"
            value={replies[t.id] ?? ''}
            onChange={(e) => setReplies((r) => ({ ...r, [t.id]: e.target.value }))}
          />
          <button
            type="button"
            className="btn btn--approve"
            disabled={busy || noName || !(replies[t.id] ?? '').trim()}
            onClick={() => {
              onReply(t.id, replies[t.id].trim())
              setReplies((r) => ({ ...r, [t.id]: '' }))
            }}
          >
            Record the reply
          </button>
        </div>
      ))}
    </section>
  )
}
