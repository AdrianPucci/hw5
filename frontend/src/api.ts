// Calls to the FastAPI back end (Problem 7), directly at http://localhost:8000.
// The back end's CORS settings allow this page's origin (http://localhost:5173).
import type { Approval, Cash, Draft, EventsPage, FollowUp, PurchaseOrder, RunJob, TeamState, Ticket } from './types'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ ok: boolean; shop_date: string }>('/api/health'),
  tickets: () => request<Ticket[]>('/api/tickets'),
  runTicket: (id: number) => request<RunJob>(`/api/tickets/${id}/run`, { method: 'POST' }),
  run: (jobId: string) => request<RunJob>(`/api/runs/${jobId}`),
  events: (params: { since?: number; ticketId?: number; limit?: number }) => {
    const q = new URLSearchParams()
    if (params.since !== undefined) q.set('since', String(params.since))
    if (params.ticketId !== undefined) q.set('ticket_id', String(params.ticketId))
    q.set('limit', String(params.limit ?? 200))
    return request<EventsPage>(`/api/events?${q}`)
  },
  approvals: () => request<Approval[]>('/api/approvals'),
  approve: (id: number, approvedBy: string, note = '') =>
    request<Record<string, unknown>>(`/api/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy, note }),
    }),
  reject: (id: number, approvedBy: string, note = '') =>
    request<Record<string, unknown>>(`/api/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: approvedBy, note }),
    }),
  cash: () => request<Cash>('/api/cash'),
  purchaseOrders: () => request<PurchaseOrder[]>('/api/purchase-orders'),
  receive: (id: number, by: string) =>
    request<Record<string, unknown>>(`/api/purchase-orders/${id}/receive`, { method: 'POST', body: JSON.stringify({ approved_by: by }) }),
  drafts: () => request<Draft[]>('/api/drafts'),
  decideDraft: (id: number, by: string, approve: boolean) =>
    request<Record<string, unknown>>(`/api/drafts/${id}/${approve ? 'approve' : 'reject'}`, {
      method: 'POST',
      body: JSON.stringify({ approved_by: by, note: approve ? 'Approved on the dashboard' : 'Rejected on the dashboard' }),
    }),
  reply: (ticketId: number, by: string, reply: string) =>
    request<Record<string, unknown>>(`/api/tickets/${ticketId}/reply`, { method: 'POST', body: JSON.stringify({ approved_by: by, reply }) }),
  team: () => request<TeamState>('/api/team'),
  resume: (by: string) => request<Record<string, unknown>>('/api/team/resume', { method: 'POST', body: JSON.stringify({ approved_by: by }) }),
  followups: () => request<FollowUp[]>('/api/followups'),
  reset: () => request<{ ok: boolean; cash: number; open_tickets: number[] }>('/api/reset', { method: 'POST' }),
}
