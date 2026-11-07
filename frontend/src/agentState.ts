// Turns the audit-trail events of one team run into what each agent card shows.
import { AGENTS, type AgentEvent, type AgentName } from './types'

export type AgentStatus = 'idle' | 'working' | 'waiting' | 'reported' | 'resolved' | 'not_needed' | 'error'

export interface AgentView {
  name: AgentName
  status: AgentStatus
  saying: string // the latest thing the agent said
  doing: string // what it's doing right now (tools, delegation)
  tools: string[] // every MCP tool it used in this run, in order
  summary: string | null // its final report's summary
  asked: string | null // the task it was given
  steps: number
}

const clip = (s: string, n = 220) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)
const nice = (tool: string) => tool.replaceAll('_', ' ')

export function deriveAgents(events: AgentEvent[], runFinished: boolean): Record<AgentName, AgentView> {
  const views = Object.fromEntries(
    AGENTS.map((name) => [
      name,
      { name, status: 'idle', saying: '', doing: '', tools: [], summary: null, asked: null, steps: 0 } as AgentView,
    ]),
  ) as Record<AgentName, AgentView>

  for (const e of events) {
    const v = views[e.agent]
    if (!v) continue
    v.steps += 1
    switch (e.kind) {
      case 'start':
        v.status = 'working'
        v.asked = e.said[0] ? clip(e.said[0], 260) : null
        v.doing = 'Reading the task'
        break
      case 'model_response':
        if (e.said.length) v.saying = clip(e.said.join(' '))
        // final_result is PydanticAI's internal "hand in my report" step, not an MCP tool.
        for (const t of e.tools_called) if (t !== 'delegate' && t !== 'final_result' && !v.tools.includes(t)) v.tools.push(t)
        if (e.delegations.length) {
          v.status = 'waiting'
          v.doing = e.delegations.map((d) => `Asked ${d.to}: ${clip(d.task ?? '', 140)}`).join(' · ')
        } else if (e.tools_called.length) {
          v.status = 'working'
          v.doing = `Using ${e.tools_called.map(nice).join(', ')}`
        } else {
          v.doing = 'Writing the report'
        }
        break
      case 'tool_results':
        v.status = 'working'
        v.doing = `Got results: ${e.tool_results.map((r) => nice(r.tool)).join(', ')}`
        break
      case 'final':
        v.status = 'reported'
        v.summary = e.said[0] ?? null
        v.saying = v.summary ?? v.saying
        v.doing = 'Reported back'
        break
      case 'error':
        v.status = 'error'
        v.doing = clip(e.said[0] ?? 'Error')
        break
    }
  }

  if (runFinished) {
    for (const v of Object.values(views)) {
      if (v.status === 'idle') v.status = 'not_needed'
      else if (v.status !== 'error') v.status = 'resolved'
    }
  }
  return views
}

/** The events of the most recent run in a list (a ticket can have many runs). */
export function latestRun(events: AgentEvent[]): AgentEvent[] {
  if (!events.length) return []
  const runId = events[events.length - 1].run_id
  return events.filter((e) => e.run_id === runId)
}

export const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: 'Standing by',
  working: 'Working',
  waiting: 'Waiting on a teammate',
  reported: 'Reported back',
  resolved: 'Resolved',
  not_needed: 'Not needed',
  error: 'Error',
}
