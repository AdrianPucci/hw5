import type { Ticket } from '../types'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Discount request',
}

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  onSelect: (id: number) => void
  onRun: () => void
  canRun: boolean
  followupIds: number[]
}

export function TicketList({ tickets, selectedId, runningId, onSelect, onRun, canRun, followupIds }: Props) {
  return (
    <section className="panel">
      <h2 className="panel__title">Open tickets</h2>
      <ul className="tickets" role="listbox" aria-label="Tickets">
        {tickets.map((t) => (
          <li key={t.id}>
            <button
              type="button"
              role="option"
              aria-selected={t.id === selectedId}
              className={`ticket ${t.id === selectedId ? 'ticket--selected' : ''}`}
              onClick={() => onSelect(t.id)}
            >
              <span className="ticket__id">#{t.id}</span>
              <span className="ticket__body">
                <span className="ticket__subject">{t.subject}</span>
                <span className="ticket__meta">
                  {TYPE_LABEL[t.type] ?? t.type} · {t.requester}
                </span>
              </span>
              <span className={`status status--${t.is_open ? t.status : 'resolved'}`}>
                {runningId === t.id ? 'Running…' : t.is_open ? t.status.replaceAll('_', ' ') : 'resolved'}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn--go" onClick={onRun} disabled={!canRun}>
        {runningId !== null
          ? 'Team is working…'
          : selectedId
            ? followupIds.includes(selectedId)
              ? `Run #${selectedId} again to follow up`
              : `Start the team on #${selectedId}`
            : 'Pick a ticket'}
      </button>
      <p className="hint">Runs take about 1–3 minutes. Nothing is paid until you approve it.</p>
    </section>
  )
}
