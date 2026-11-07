import type { AgentEvent } from '../types'

function line(e: AgentEvent): string {
  switch (e.kind) {
    case 'start':
      return `started: ${e.said[0] ?? ''}`
    case 'model_response':
      if (e.delegations.length) return e.delegations.map((d) => `asked ${d.to}: ${d.task}`).join(' · ')
      if (e.tools_called.length) return `called ${e.tools_called.join(', ')}`
      return e.said.join(' ') || 'thinking…'
    case 'tool_results':
      return `got results from ${e.tool_results.map((r) => r.tool).join(', ')}`
    case 'final':
      return `reported: ${e.said[0] ?? ''}`
    case 'error':
      return `error: ${e.said[0] ?? ''}`
  }
}

export function ActivityFeed({ events }: { events: AgentEvent[] }) {
  const recent = events.slice(-40).reverse()
  return (
    <section className="panel panel--feed">
      <h2 className="panel__title">Live feed</h2>
      {recent.length === 0 ? (
        <p className="empty">Start the team on a ticket to watch the agents work.</p>
      ) : (
        <ol className="feed">
          {recent.map((e) => (
            <li key={e.index} className={`feed__item feed__item--${e.kind}`}>
              <time>{e.time?.slice(11, 19)}</time>
              <strong>{e.agent}</strong>
              <span>{line(e)}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
