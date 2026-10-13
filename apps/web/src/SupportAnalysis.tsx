import React, {useEffect, useRef, useState} from 'react';

type SupportResult = {
  fictional: boolean;
  selected_queues: string[];
  answer: {limitations: string[]};
  evidence: {
    input_sha256: string;
    evidence_id: string;
    table: {group: string; count: number; mean: number}[];
    records: {ticket_id: string; queue: string; resolution_hours: number}[];
  };
  markdown: string;
};

const hours = (value: number) => Intl.NumberFormat(undefined, {maximumFractionDigits: 3}).format(value);

export default function SupportAnalysis() {
  const [file, setFile] = useState<File|null>(null);
  const [result, setResult] = useState<SupportResult|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [reportUrl, setReportUrl] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const pending = useRef(false);

  useEffect(() => {
    if (!result) {setReportUrl(''); return;}
    const url = URL.createObjectURL(new Blob([result.markdown], {type: 'text/markdown;charset=utf-8'}));
    setReportUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [result]);

  function choose(next: File|null) {
    setResult(null); setError(''); setFile(next);
    if (next && (next.size === 0 || next.size > 1_048_576)) {
      setFile(null); setError('Choose a nonempty CSV no larger than 1 MB.');
    }
  }

  async function example() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setResult(null); setError('');
    try {
      const response = await fetch('/sample.csv');
      if (!response.ok) throw new Error('The fictional example could not be opened. Choose your own CSV.');
      choose(new File([await response.blob()], 'FictionalSupportTickets.csv', {type: 'text/csv'}));
      if (input.current) input.current.value = '';
    } catch (error) {
      setError(error instanceof Error ? error.message : 'The example could not be opened.');
    } finally {pending.current = false; setBusy(false);}
  }

  async function run(event: React.FormEvent) {
    event.preventDefault();
    if (!file || pending.current) return;
    pending.current = true; setBusy(true); setResult(null); setError('');
    try {
      const response = await fetch('/api/support-check', {method: 'POST', headers: {'Content-Type': 'text/csv'}, body: file});
      const value = await response.json();
      if (!response.ok) throw new Error(value.detail || 'The analysis could not finish. Check the file and try again.');
      setResult(value);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'The analysis could not finish. Try again.');
    } finally {pending.current = false; setBusy(false);}
  }

  return <div className="workspace support-workspace">
    <aside className="sidebar" aria-label="Support check">
      <a className="brand" href="/support">BackIntel<span>Local support analysis</span></a>
      <p>Compare closed-ticket resolution times and inspect the records behind the answer.</p>
      <div className="identity"><span>Processing stays on this computer.</span></div>
    </aside>
    <main>
      <header><div><p className="eyebrow">Support queues</p><h1>Which queue needs attention?</h1></div></header>
      <p>Choose closed support tickets. Review the queue with the longest average resolution time.</p>
      <section aria-labelledby="choose-data">
        <h2 id="choose-data">1. Choose your tickets</h2>
        <form onSubmit={run} aria-busy={busy}>
          <label htmlFor="support-file">Support-ticket file</label>
          <input id="support-file" ref={input} type="file" accept=".csv,text/csv" disabled={busy}
            aria-describedby="file-help" onChange={event => choose(event.target.files?.[0] || null)}/>
          <p id="file-help" className="caveat">CSV with ticket_id, channel, and resolution_time_hours. Use closed tickets from 2–20 queues. Up to 1 MB and 10,000 tickets.</p>
          <div className="actions"><button type="button" disabled={busy} onClick={example}>Use fictional example</button>
            <button type="submit" disabled={!file || busy}>{busy ? 'Checking tickets…' : 'Run analysis'}</button></div>
          {file && <p className="muted">Selected: {file.name}</p>}
        </form>
      </section>
      {busy && <p className="progress" role="status">Checking the selected tickets and their queue averages.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {result && <>
        <section aria-labelledby="answer-heading" aria-live="polite">
          <h2 id="answer-heading">2. Queues to review: {result.selected_queues.join(', ')}</h2>
          <p className="caveat">{result.fictional ? 'Fictional example. These are not customer results.' : 'Uploaded records. The supplied values are not independently verified.'}</p>
          <p>The selected {result.selected_queues.length === 1 ? 'queue has' : 'queues share'} the longest average resolution time among these closed tickets.</p>
          <div className="table-scroll"><table aria-label="Queue comparison">
            <thead><tr><th scope="col">Queue</th><th scope="col">Closed tickets</th><th scope="col">Average hours</th></tr></thead>
            <tbody>{result.evidence.table.map(row => <tr key={row.group}><th scope="row">{row.group}</th><td>{row.count}</td><td>{hours(row.mean)}</td></tr>)}</tbody>
          </table></div>
        </section>
        <section aria-labelledby="evidence-heading" className="evidence">
          <h2 id="evidence-heading">3. Inspect and save the report</h2>
          <details><summary>Supporting tickets</summary>
            <div className="table-scroll"><table aria-label="Supporting tickets">
              <thead><tr><th scope="col">Ticket</th><th scope="col">Queue</th><th scope="col">Resolution hours</th></tr></thead>
              <tbody>{result.evidence.records.filter(row => result.selected_queues.includes(row.queue)).map(row =>
                <tr key={row.ticket_id}><th scope="row">{row.ticket_id}</th><td>{row.queue}</td><td>{hours(row.resolution_hours)}</td></tr>)}</tbody>
            </table></div>
          </details>
          <div className="actions">{reportUrl && <a href={reportUrl} download="support-report.md">Save checked report</a>}</div>
          <details><summary>Report limits and calculation details</summary>
            <ul>{result.answer.limitations.map(text => <li key={text}>{text}</li>)}</ul>
            <p>This comparison covers closed tickets. It does not explain delays or measure the open workload.</p>
            <dl><dt>Input SHA-256</dt><dd>{result.evidence.input_sha256}</dd><dt>Calculation reference</dt><dd>{result.evidence.evidence_id}</dd></dl>
          </details>
        </section>
      </>}
    </main>
  </div>;
}
