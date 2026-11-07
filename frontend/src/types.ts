// Shapes returned by the FastAPI back end (backend/main.py, Problem 7).

export const AGENTS = ['Boss', 'Inventory', 'Accounting', 'Facilities', 'Customer Service'] as const
export type AgentName = (typeof AGENTS)[number]

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  is_open: boolean
  status_reason: string | null
  assigned_to: string | null
}

export interface AgentReport {
  agent: AgentName
  summary: string
  database_facts: string[]
  actions_taken: string[]
  approval_requests: number[]
  needs_human_decision: string[]
}

export interface RunJob {
  job_id: string
  ticket_id: number
  status: 'running' | 'done' | 'error'
  started: string
  finished: string | null
  run_id: string | null
  error: string | null
  final_report: AgentReport | null
}

export type EventKind = 'start' | 'model_response' | 'tool_results' | 'final' | 'error'

export interface AgentEvent {
  index: number
  time: string
  run_id: string
  ticket_id: number | null
  agent: AgentName
  chain: AgentName[]
  kind: EventKind
  said: string[]
  tools_called: string[]
  delegations: { to: AgentName; task: string }[]
  tool_results: { tool: string; result: unknown }[]
}

export interface EventsPage {
  next_since: number
  count: number
  events: AgentEvent[]
}

export interface Approval {
  id: number
  kind: 'invoice_payment' | 'rent_payment' | 'purchase_order' | 'price_override'
  ticket_id: number | null
  amount: number
  qty: number | null
  sku: string | null
  size: string | null
  unit_price: number | null
  requested_by: AgentName
  reason: string
  status: string
  created_at: string
}

export interface PurchaseOrder {
  id: number
  ticket_id: number | null
  vendor_id: number
  sku: string
  size: string
  qty: number
  total: number
  status: 'ordered' | 'received'
  ordered_on: string
  expected_on: string
  received_on: string | null
}

export interface Draft {
  id: number
  ticket_id: number
  author: string
  recipient: string
  subject: string
  body: string
  status: 'draft' | 'approved_to_send' | 'rejected'
  created_at: string
}

export interface FollowUp {
  followup_type: 'decision' | 'customer_reply' | 'order_received'
  ticket_id: number
}

export interface TeamState {
  status: { halted: boolean; reason?: string; changed_by?: string }
  staffing: { staffed_now: boolean; next_window_text: string | null; shop_now: string }
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_requests_total: number
  balance_if_all_pending_approved: number
}
