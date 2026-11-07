import type { Approval } from '../types'

const KIND: Record<Approval['kind'], string> = {
  invoice_payment: 'Pay a vendor invoice',
  rent_payment: 'Pay rent',
  purchase_order: 'Restock order',
  price_override: 'Discount price',
}
const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

interface Props {
  approvals: Approval[]
  approver: string
  onApprover: (name: string) => void
  onDecide: (id: number, approve: boolean) => void
  busyId: number | null
}

export function ApprovalPanel({ approvals, approver, onApprover, onDecide, busyId }: Props) {
  return (
    <section className="panel panel--approvals">
      <h2 className="panel__title">Needs your OK</h2>
      <label className="approver">
        Approving as
        <input value={approver} onChange={(e) => onApprover(e.target.value)} placeholder="Your name" />
      </label>
      {approvals.length === 0 ? (
        <p className="empty">Nothing waiting. The agents only prepare payments; you approve them here.</p>
      ) : (
        <ul className="approvals">
          {approvals.map((a) => (
            <li key={a.id} className="approval">
              <div className="approval__top">
                <span className="approval__kind">{KIND[a.kind] ?? a.kind}</span>
                <span className="approval__amount">
                  {a.kind === 'price_override' ? `${a.qty} × ${money(a.unit_price ?? 0)}` : money(a.amount)}
                </span>
              </div>
              <p className="approval__meta">
                Request #{a.id}
                {a.ticket_id ? ` · ticket #${a.ticket_id}` : ''} · prepared by {a.requested_by}
              </p>
              <p className="approval__reason">{a.reason}</p>
              <div className="approval__actions">
                <button
                  type="button"
                  className="btn btn--approve"
                  disabled={busyId !== null || !approver.trim()}
                  onClick={() => onDecide(a.id, true)}
                >
                  {busyId === a.id ? 'Working…' : 'Approve'}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={busyId !== null || !approver.trim()}
                  onClick={() => onDecide(a.id, false)}
                >
                  Reject
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
