import { STATUS_LABEL, type AgentView } from '../agentState'
import type { AgentName } from '../types'

const ROLE: Record<AgentName, string> = {
  Boss: 'Reads, assigns, decides',
  Inventory: 'Stock, sizes, vendors',
  Accounting: 'Cash, bills, prices',
  Facilities: 'Lease and rent',
  'Customer Service': 'Drafts for customers',
}
const INITIALS: Record<AgentName, string> = {
  Boss: 'B',
  Inventory: 'In',
  Accounting: '$',
  Facilities: 'F',
  'Customer Service': 'CS',
}

export function AgentCard({ view }: { view: AgentView }) {
  const done = view.status === 'resolved' || view.status === 'reported'
  return (
    <article className={`agent agent--${view.status}`} aria-live="polite">
      <header className="agent__head">
        <span className="agent__avatar" aria-hidden="true">{INITIALS[view.name]}</span>
        <div>
          <h3 className="agent__name">{view.name}</h3>
          <p className="agent__role">{ROLE[view.name]}</p>
        </div>
        <span className={`pill pill--${view.status}`}>
          {view.status === 'resolved' && '✓ '}
          {STATUS_LABEL[view.status]}
        </span>
      </header>

      {view.status === 'not_needed' ? (
        <p className="agent__quiet">Not called on this ticket (only the agents a ticket needs).</p>
      ) : view.status === 'idle' ? (
        <p className="agent__quiet">Waiting for a ticket.</p>
      ) : (
        <>
          {done && view.summary ? (
            <div className="agent__summary">
              <span className="label">What I did</span>
              <p>{view.summary}</p>
            </div>
          ) : (
            <>
              {view.doing && (
                <p className="agent__doing">
                  <span className="label">Doing</span> {view.doing}
                </p>
              )}
              {view.saying && <blockquote className="agent__saying">“{view.saying}”</blockquote>}
            </>
          )}
          {view.tools.length > 0 && (
            <div className="agent__tools" aria-label="MCP tools used">
              {view.tools.map((t) => (
                <span key={t} className="tool">{t}</span>
              ))}
            </div>
          )}
        </>
      )}
    </article>
  )
}
