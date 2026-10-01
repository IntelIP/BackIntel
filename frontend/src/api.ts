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
export type Demo = {
  title: string; persona: string; problem: string; today: string[]; status: string; jev_mode: string;
  demo_id: string; captured_at: string; actual_provider_calls: number | null; error?: string;
  stages: { id: string; title: string; technology: string; count: number; status: string; explanation: string }[];
  comparisons: { route: string; feature_set: string; metrics: Record<string, number | null>; selected: boolean; train_count: number; holdout_count: number }[];
  comparison_basis?: string;
  live_attempt?: { request_attempts: number; unknown_request_cost_count: number; total_provider_charge_usd: number | null };
  workflow_rehearsal?: { status: string; scope_boundary: string; technology: string; pending_triggers: number; replay_unchanged: boolean; evidence_records: number; scenarios: { name: string; completed_jobs: number; simulated_predictions: number; delivery_records: number; simulated_model_updates: number }[] };
  local_rehearsal?: { scope_boundary: string; train_count: number; holdout_count: number; selected_route: string; methods: { route: string; estimates: { entity: string; value: number; cutoff: number; target_at: number }[] }[] };
  value: { assumptions: Record<string, number>; capacity_hours_per_week: number; capacity_value_usd_per_week: number; provider_usd: number | null; compute_usd: number | null; net_benefit_usd: number | null; explanation: string };
  stack: { name: string; role: string }[]; boundaries: string[];
}
export type Workspace = { schema: 'backintel-decision-workspace/v1'; cases: Case[]; source_mode: string; demo?: Demo }

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
