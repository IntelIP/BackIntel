import {useEffect, useState} from 'react';

type Queue = {
  shared_capacity: {active: number; waiting: number; active_limit: number};
  your_usage: {provider_usd: number; reserved_usd: number; budget_usd: number; unresolved_charges: number};
  jobs: {id: string; goal_id: string|null; status: string; state: string; waiting_seconds: number}[];
};

export function QueuePanel({token, goals}: {token: string; goals: {id: string; body: {question: string}}[]}) {
  const [queue, setQueue] = useState<Queue|null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let pending = false;
    setQueue(null);
    async function refresh() {
      if (pending) return;
      pending = true;
      try {
        const response = await fetch('/api/v1/queue', {
          headers: {Authorization: 'Bearer ' + token}, signal: controller.signal,
        });
        if (!response.ok) throw new Error('Work status is unavailable. Refresh your access to try again.');
        const current: Queue = await response.json();
        if (!current?.shared_capacity || !current?.your_usage || !Array.isArray(current.jobs)) throw new Error('Work status is unavailable.');
        if (!controller.signal.aborted) {setQueue(current); setError('');}
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Work status is unavailable.');
      } finally {pending = false;}
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => {controller.abort(); window.clearInterval(timer);};
  }, [token]);
  return <section className="panel" aria-label="Work in progress">
    <h2>Work in progress</h2>
    {error ? <p role="status">{error}</p> : !queue ? <p>Loading work status…</p> : <>
      <p aria-live="polite">Shared service: {queue.shared_capacity.active} running, {queue.shared_capacity.waiting} waiting. Up to {queue.shared_capacity.active_limit} jobs can run at once.</p>
      <p>Your model spending: US${Number(queue.your_usage.provider_usd).toFixed(4)} charged and US${Number(queue.your_usage.reserved_usd).toFixed(4)} reserved, within a US${Number(queue.your_usage.budget_usd).toFixed(2)} user limit.</p>
      {queue.your_usage.unresolved_charges > 0 && <p>Some charges are not settled yet. Reserved amounts still count toward your limit.</p>}
      <p className="muted">Local computer costs have not been measured. Only work you own or can view is listed.</p>
      <ul>{queue.jobs.map(job => <li key={job.id}>{goals.find(goal => goal.id === job.goal_id)?.body.question || 'Source import'} — {job.status}; waited {Math.max(0, Number(job.waiting_seconds)).toFixed(1)} seconds.</li>)}</ul>
      {!queue.jobs.length && <p>No work is available for this account.</p>}
    </>}
  </section>;
}
