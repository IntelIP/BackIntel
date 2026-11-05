export type Coordination = {
  run_id: string;
  goal_version: number;
  source_version: string | null;
  status: string;
  policy: {request_id: string; max_model_calls: number; max_spend_usd: number};
  usage: {provider_calls: number; provider_usd: number; reserved_usd: number; charge_status: string};
  agents: {
    role: string;
    responsibility: string;
    status: string;
    mode?: string;
    input_version?: string;
    observations_version?: string;
    error?: string | null;
    evidence_id?: string;
    contribution?: unknown;
    usage: Coordination['usage'];
  }[];
};

export function CoordinationPanel({value,allowed,busy,budget,onStart}: {
  value?: Coordination;
  allowed: boolean;
  busy: boolean;
  budget: number;
  onStart: (requestId: string, limit: number) => void;
}) {
  const running = value && ['queued','running'].includes(value.status);
  const resume = value && ['partial','cancelled','failed'].includes(value.status);
  const cap = resume ? value.policy.max_spend_usd : Math.min(0.5, budget);
  return <section className="coordination" aria-label="Specialist coordination">
    <h2>Let specialists answer together</h2>
    <p>BackIntel collects the permitted data, interprets its fields, prepares it, calculates the answer, and checks it against the original records.</p>
    <p>The specialists share one limit of six model requests and ${cap.toFixed(2)}. Source values and business definitions stay protected.</p>
    {allowed && <button disabled={busy || !!running || budget <= 0 || cap > budget}
      onClick={() => onStart(resume ? value.policy.request_id : crypto.randomUUID(), cap)}>
      {running ? 'Specialists are working' : resume ? 'Resume specialist work' : 'Start specialist analysis'}
    </button>}
    {allowed && budget <= 0 && <p>Set a model-spending allowance for this objective before starting.</p>}
    {value && <>
      <p>Shared plan: {value.status}. Objective version {value.goal_version}.</p>
      {value.source_version && <details><summary>Inspect source version</summary><code>{value.source_version}</code></details>}
      {value.agents.map(item => <article key={item.role} aria-label={`${item.role} specialist`}>
        <h3>{item.role === 'data' ? 'Understand and prepare the data' : item.role === 'analysis' ? 'Choose the calculation' : 'Check the finding'}</h3>
        <p>{item.responsibility}</p><p>Status: {item.status}.</p>
        {item.mode === 'fixture' && <p>This specialist used a simulated response.</p>}
        {item.error && <p role="alert">{item.error}</p>}
        <p>{item.usage.provider_calls} requests · ${item.usage.provider_usd.toFixed(4)} measured cost.</p>
        {item.usage.charge_status === 'unknown' && <p>Charges need reconciliation before another paid request. Reserved: ${item.usage.reserved_usd.toFixed(4)}.</p>}
        {item.contribution !== undefined && <details><summary>Inspect contribution and evidence</summary>
          <p>Input version: <code>{item.input_version}</code></p>
          <p>Observed evidence version: <code>{item.observations_version}</code></p>
          {item.evidence_id && <p>Retained evidence: <code>{item.evidence_id}</code></p>}
          <pre>{JSON.stringify(item.contribution,null,2)}</pre>
        </details>}
      </article>)}
      <p>Total measured model cost: ${value.usage.provider_usd.toFixed(4)} across {value.usage.provider_calls} requests.</p>
      <p>A rejected or interrupted attempt keeps the last accepted answer available.</p>
    </>}
  </section>;
}
