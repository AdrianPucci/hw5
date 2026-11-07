import type { Cash } from '../types'

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export function CashCard({ cash, lastChange }: { cash: Cash | null; lastChange: number | null }) {
  return (
    <section className="cash" aria-live="polite">
      <span className="cash__label">Checking balance</span>
      <span className="cash__value" key={cash?.balance}>{cash ? money(cash.balance) : '…'}</span>
      {lastChange !== null && lastChange !== 0 && (
        <span className={`cash__delta ${lastChange < 0 ? 'cash__delta--down' : 'cash__delta--up'}`}>
          {lastChange < 0 ? '▼ ' : '▲ '}
          {money(Math.abs(lastChange))} after your approval
        </span>
      )}
      {cash && cash.pending_requests_total > 0 && (
        <span className="cash__pending">
          {money(cash.pending_requests_total)} waiting for approval · {money(cash.balance_if_all_pending_approved)} if all approved
        </span>
      )}
    </section>
  )
}
