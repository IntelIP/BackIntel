export type Decision = 'follow_up' | 'no_action' | 'need_more_information'
export type Review = { decision: Decision; reason: string; revision: number; recorded_at: string }
export type Case = {
  id: string; workflow: 'issues' | 'equipment'; title: string; summary: string;
  created_at: string; source_kind: string; simulated: boolean;
  facts: { label: string; value: string }[];
  finding: { text: string; status: string };
  prediction: { status: string; explanation: string; estimates: Record<string, number> };
  evidence: { text: string; url: string | null; sha256: string; collected_at: string };
  review: Review | null; history: Review[]; outcome: { text: string; available_at: string } | null;
}
export type Workspace = { schema: 'backintel-decision-workspace/v1'; cases: Case[]; source_mode: string }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options)
  const data = await response.json()
  if (!response.ok) throw new ApiError(response.status, data.error ?? 'Request failed. Try again.')
  return data as T
}

export function loadWorkspace(signal?: AbortSignal) { return request<Workspace>('/workspace', { signal }) }
export function saveDecision(id: string, decision: Decision, reason: string, revision: number, sourceSha256: string) {
  return request<Case>(`/cases/${encodeURIComponent(id)}/decision`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason, expected_revision: revision, expected_source_sha256: sourceSha256 }),
  })
}
