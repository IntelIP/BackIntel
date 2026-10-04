import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Principal = {id: string; role: string; domains: string[]};
type Source = {id: string; domain: string; latest_snapshot: string|null; body: {name: string; question: string; caveat: string; terms_acknowledged: boolean; license: string; kaggle: string; competition?: boolean}};
type Goal = {id: string; domain: string; version: number; confirmed: boolean; paused: boolean; freshness: string; last_success: string|null; active_model: string|null; body: {question: string; definitions: Record<string,string>; notification_delta: number; budget_usd?: number}};
type TableRow = {group: string; count: number; labeled: number; mean: number|null};
type Finding = {claim: string; kind: string; evidence_ids: string[]};
type Result = {summary: string; findings?: Finding[]; limitations?: string[]; tables?: {title: string; rows: TableRow[]; evidence_id: string}[]; usage: {provider_usd: number; charge_status: string}; candidate_id?: string};
type Run = {id: string; goal_id: string; status: string; created_at: string; snapshot_id: string; error?: string; result?: Result; body: {operation: string; question: string}};
type Model = {id: string; promoted: boolean; body: {methods: {route: string; features?: string; metrics: Record<string,unknown>}[]}};
type Review = {id: number; actor: string; body: {text: string; kind: string}};
const format = (n: number|null|undefined) => n == null ? 'Unavailable' : Intl.NumberFormat(undefined,{maximumFractionDigits:3}).format(n);

function App() {
  const [token,setToken] = useState(() => new URLSearchParams(location.hash.slice(1)).get('access') || sessionStorage.getItem('backintel-access') || '');
  const [entry,setEntry] = useState('');
  const [me,setMe] = useState<Principal|null>(null);
  const [sources,setSources] = useState<Source[]>([]);
  const [goals,setGoals] = useState<Goal[]>([]);
  const [notifications,setNotifications]=useState<{id:number;goal_id:string;domain:string;body:{message:string}}[]>([]);
  const [domain,setDomain] = useState('commerce');
  const [goalId,setGoalId] = useState('');
  const [question,setQuestion] = useState('');
  const [followup,setFollowup] = useState('');
  const [runs,setRuns] = useState<Run[]>([]);
  const [importRun,setImportRun] = useState<Run|null>(null);
  const [models,setModels] = useState<Model[]>([]);
  const [reviews,setReviews] = useState<Review[]>([]);
  const [view,setView] = useState('analysis');
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [evidence,setEvidence] = useState<unknown>(null);
  const [note,setNote] = useState('');
  const [editQuestion,setEditQuestion] = useState('');
  const [correctionId,setCorrectionId] = useState('');
  const [correctionTarget,setCorrectionTarget] = useState('');
  const [progress,setProgress] = useState('');
  const manager = me?.role === 'manager';
  const canAnalyze = manager || me?.role === 'analyst';
  const selected = goals.find(g => g.id === goalId);
  const source = sources.find(s => s.domain === domain);
  const current = runs.find(r => r.id === selected?.last_success && r.status === 'succeeded');
  const pending = runs.find(r => r.status === 'queued' || r.status === 'running') || importRun;

  async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const r = await fetch('/api/v1'+path,{method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body === undefined ? undefined : JSON.stringify(body)});
    const value = await r.json();
    if (!r.ok) throw new Error(value.detail || 'Request failed');
    return value as T;
  }
  async function refresh() {
    const [p,s,g] = await Promise.all([api<Principal>('/me'),api<Source[]>('/sources'),api<Goal[]>('/goals')]);
    setMe(p); setSources(s); setGoals(g);
    setNotifications(await api('/notifications'));
  }
  async function details(id = goalId) {
    if (!id) return;
    const [r,m,v] = await Promise.all([api<Run[]>('/runs?goal_id='+id),api<Model[]>('/goals/'+id+'/models'),api<Review[]>('/goals/'+id+'/reviews')]);
    setRuns(r); setModels(m); setReviews(v);
  }
  async function action(fn: () => Promise<void>) {
    setError('');setBusy(true);
    try {await fn();await refresh();await details();} catch(e) {setError(e instanceof Error ? e.message : 'Request failed');}
    finally {setBusy(false);}
  }
  useEffect(() => {
    history.replaceState(null,'',location.pathname);
    if (token) {sessionStorage.setItem('backintel-access',token);refresh().catch(e=>setError(e.message));}
  },[token]);
  useEffect(() => {setRuns([]);setModels([]);setReviews([]);setEvidence(null);if(goalId) details().catch(e=>setError(e.message));},[goalId]);
  useEffect(()=>{if(!token)return;const timer=setInterval(()=>{refresh().then(()=>details()).catch(e=>setError(e.message));},30000);return()=>clearInterval(timer);},[token,goalId]);
  useEffect(() => {setQuestion(source?.body.question || '');},[domain,source?.body.question]);
  useEffect(() => {setEditQuestion(selected?.body.question || '');},[goalId,selected?.version]);
  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    async function listen() {
      try {
        while (!controller.signal.aborted) {
        const response = await fetch('/api/v1/runs/'+pending!.id+'/events',{headers:{Authorization:'Bearer '+token},signal:controller.signal});
        if (!response.ok) throw new Error('Progress access denied');
        const reader = response.body!.getReader();const decoder = new TextDecoder();let buffer = '';
        for (;;) {
          const {value,done} = await reader.read(); if(done) break;
          buffer += decoder.decode(value,{stream:true});
          const chunks = buffer.split('\n\n');buffer = chunks.pop() || '';
          for (const chunk of chunks) {
            const event = chunk.split('\n').find(line=>line.startsWith('event:'))?.slice(7) || 'progress';
            setProgress(event.replaceAll('_',' '));
          }
        }
        await details();await refresh();
        const state=await api<Run>('/runs/'+pending!.id);
        if (state.status!=='queued' && state.status!=='running') { if (importRun) setImportRun(null); if (state.error) setError(state.error); await refresh();await details(); return; }
        }
      } catch(e) {if(!controller.signal.aborted)setError(e instanceof Error ? e.message : 'Progress disconnected');}
    }
    listen();return()=>controller.abort();
  },[pending?.id,token]);

  if (!me) return <main className="login"><p className="eyebrow">BackIntel</p><h1>Your analysis workspace</h1><p>Use your local access credential. Your role determines the sources and actions available.</p><form onSubmit={e=>{e.preventDefault();setToken(entry);}}><label htmlFor="credential">Access credential</label><input id="credential" type="password" value={entry} onChange={e=>setEntry(e.target.value)} autoComplete="off" required/><button>Open workspace</button></form>{error&&<p role="alert" className="error">{error}</p>}<p className="muted">Open securely with <code>python -m scripts.analysis_demo open --role manager</code>.</p></main>;
  return <div className="workspace">
    <aside className="sidebar"><a className="brand" href="/">BackIntel<span>Analysis workspace</span></a><p className="eyebrow">Sources</p><nav aria-label="Data domains">{sources.map(s=><button className={domain===s.domain?'selected':''} key={s.id} onClick={()=>{setDomain(s.domain);setGoalId('');}}>{s.domain[0].toUpperCase()+s.domain.slice(1)}<span className="source-state">{s.latest_snapshot?'Ready':'Awaiting data'}</span></button>)}</nav><p className="eyebrow">Saved goals</p><nav aria-label="Saved goals">{goals.filter(g=>g.domain===domain).map(g=><button className={goalId===g.id?'selected':''} key={g.id} onClick={()=>setGoalId(g.id)}>{g.body.question}<span className="source-state">{g.paused?'Paused':g.freshness}</span></button>)}</nav><div className="identity"><strong>{me.role}</strong><button onClick={()=>{sessionStorage.removeItem('backintel-access');setToken('');setMe(null);}}>Sign out</button></div></aside>
    <main><header><div><p className="eyebrow">{domain} / {view}</p><h1>{source?.body.name || 'Select a source'}</h1></div><span className="model-label">GPT-6.1 Sol · hosted analyst</span></header>
      {error&&<div className="error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}>×</button></div>}
      <nav className="tabs" aria-label="Workspace views">{['analysis','sources','goals','conversation','review','history'].map(v=><button key={v} aria-current={view===v?'page':undefined} onClick={()=>setView(v)}>{v[0].toUpperCase()+v.slice(1)}</button>)}</nav>
      <p className="caveat">{source?.body.caveat}</p>{notifications.map(n=><div role="status" className="progress" key={n.id}>{n.body.message} <button onClick={()=>{setDomain(n.domain);setGoalId(n.goal_id);setView('analysis');}}>Inspect updated answer</button></div>)}
      {importRun&&<p role="status" className="progress">Source import: {progress || "queued"}</p>}
      {view==='sources'&&source&&<section><h2>Source readiness</h2><dl><dt>Snapshot</dt><dd>{source.latest_snapshot||'No data imported'}</dd><dt>Source terms</dt><dd>{source.body.license} · {source.body.terms_acknowledged?'Confirmed':'Confirmation required'}</dd></dl><a href={'https://www.kaggle.com/'+(source.body.competition?'competitions/':'datasets/')+source.body.kaggle} target="_blank" rel="noreferrer">Review original source and terms</a>{manager&&<div className="actions"><button disabled={busy} onClick={()=>action(async()=>{await api('/sources/'+domain+'/terms','POST',{acknowledged:true});})}>Confirm source access and terms</button><button disabled={busy||!source.body.terms_acknowledged} onClick={()=>action(async()=>{setImportRun(await api<Run>('/sources/'+domain+'/refresh','POST',{}));})}>Import or check for updates</button></div>}<p className="muted">Original files stay outside Git. A changed snapshot refreshes saved goals.</p></section>}
      {view==='goals'&&<section><h2>Save a question</h2>{manager?<form onSubmit={e=>{e.preventDefault();action(async()=>{const g=await api<Goal>('/goals','POST',{domain,question});setGoalId(g.id);});}}><label htmlFor="question">Question to monitor</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={2000} required/><button disabled={busy}>Propose goal</button></form>:<p>Managers configure standing questions. Select a permitted goal to investigate.</p>}{selected&&<div className="definitions"><h3>Confirm business meaning</h3><dl>{Object.entries(selected.body.definitions).map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl>{manager&&<><form key={selected.id+':'+selected.version} onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);action(async()=>{await api('/goals/'+goalId,'PATCH',{threshold:Number(data.get('threshold')),budget_usd:Number(data.get('budget'))});});}}><label htmlFor="threshold">Notify when a group mean changes by at least</label><input id="threshold" name="threshold" type="number" min="0" max="100000" step="any" defaultValue={selected.body.notification_delta} required/><label htmlFor="budget">Maximum frontier cost per run (USD)</label><input id="budget" name="budget" type="number" min="0.01" max="1" step="0.01" defaultValue={selected.body.budget_usd||1} required/><button disabled={busy}>Save goal limits</button></form><label htmlFor="edit-question">Standing question</label><textarea id="edit-question" value={editQuestion} onChange={e=>setEditQuestion(e.target.value)}/><div className="actions"><button disabled={busy||editQuestion===selected.body.question} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{question:editQuestion});})}>Save revised question</button><button disabled={busy||selected.confirmed} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{confirmed:true});})}>Confirm definitions</button><button disabled={busy} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{paused:!selected.paused});})}>{selected.paused?'Resume goal':'Pause goal'}</button></div></>}</div>}</section>}
      {view==='analysis'&&<section><div className="section-heading"><h2>{selected?.body.question||'Choose a saved goal'}</h2>{selected&&canAnalyze&&<button disabled={busy||!selected.confirmed||selected.paused} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{});})}>Run analysis</button>}</div>{pending&&<p role="status" className="progress">{pending.body.operation==='training'?'Comparing prediction methods':'Analysis in progress'} · {progress||pending.status}</p>}{selected&&<p className="muted">Answer status: {selected.freshness} · Goal version {selected.version}</p>}{current?.result?<><p className="answer">{current.result.summary}</p>{current.result.findings?.map((f,i)=><article className="finding" key={i}><span className="tag">{f.kind}</span><p>{f.claim}</p>{f.evidence_ids.map(id=><button className="text-button" key={id} onClick={()=>action(async()=>{setEvidence(await api('/evidence/'+id));})}>Inspect calculation</button>)}</article>)}{current.result.tables?.map((t,i)=><div key={i}><h3>{t.title}</h3><div className="table-scroll"><table><thead><tr><th>Group</th><th>Records</th><th>Known values</th><th>Mean</th></tr></thead><tbody>{t.rows.map(row=><tr key={row.group}><td>{row.group}</td><td>{format(row.count)}</td><td>{format(row.labeled)}</td><td>{format(row.mean)}</td></tr>)}</tbody></table></div><figure aria-label={t.title+' mean comparison'}>{t.rows.filter(r=>r.mean!==null).map(row=><div className="chart-row" key={row.group}><span>{row.group}</span><meter min={0} max={Math.max(1,...t.rows.map(r=>r.mean||0))} value={Math.max(0,row.mean||0)} aria-label={row.group+' mean'}/><span>{format(row.mean)}</span></div>)}<figcaption>Calculated values for the displayed groups.</figcaption></figure></div>)}{current.result.limitations?.map((s,i)=><p className="caveat" key={i}>{s}</p>)}<p className="muted">Measured inference: ${format(current.result.usage.provider_usd)} · {current.result.usage.charge_status}</p></>:<div className="empty"><h3>No completed answer yet</h3><p>Select a goal, confirm its definitions, and run the analysis. Partial runs remain in history.</p></div>}</section>}
      {view==='conversation'&&<section><h2>Ask a follow-up</h2><p>The standing goal changes only when a manager saves a revision.</p><form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/goals/'+goalId+'/runs','POST',{question:followup});setFollowup('');});}}><label htmlFor="followup">Follow-up question</label><textarea id="followup" value={followup} onChange={e=>setFollowup(e.target.value)} required maxLength={2000}/><button disabled={busy||!canAnalyze||!selected?.confirmed}>Investigate</button></form>{runs.filter(r=>r.body.operation==='analysis'&&r.body.question!==selected?.body.question).map(r=><article className="finding" key={r.id}><h3>{r.body.question}</h3><p className="muted">{r.status}</p>{r.result&&<><p className="answer">{r.result.summary}</p>{r.result.findings?.map((f,i)=><div key={i}><p>{f.claim}</p>{f.evidence_ids.map(id=><button className="text-button" key={id} onClick={()=>action(async()=>{setEvidence(await api('/evidence/'+id));})}>Inspect calculation</button>)}</div>)}{r.result.limitations?.map((text,i)=><p className="muted" key={i}>{text}</p>)}</>}</article>)}</section>}
      {view==='review'&&<section><h2>Prediction candidates</h2><p>Training can run automatically. A manager approves each replacement.</p>{manager&&selected&&<button disabled={busy||!selected.confirmed||selected.paused} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'training'});})}>Compare real predictors</button>}{models.map(m=><article className="finding" key={m.id}><p className="muted">Candidate {m.id.slice(0,12)} · {m.promoted?'Approved':'Awaiting manager'}</p><div className="table-scroll"><table><thead><tr><th>Method</th><th>Features</th><th>Measured result</th></tr></thead><tbody>{m.body.methods.map((method,i)=><tr key={i}><td>{method.route}</td><td>{method.features||'Baseline'}</td><td>{Object.entries(method.metrics).filter(([,v])=>typeof v==='number').map(([k,v])=>k+': '+format(v as number)).join(' · ')}</td></tr>)}</tbody></table></div>{manager&&!m.promoted&&m.body.methods.filter(method=>['catboost','tabiclv2'].includes(method.route)).map(method=><button key={method.route+'-'+method.features} disabled={busy} onClick={()=>action(async()=>{await api('/models/'+m.id+'/promote','POST',{route:method.route+'-'+(method.features||'facts')});})}>Approve {method.route} ({method.features||'facts'})</button>)}</article>)}<h2>Review notes and corrections</h2>{canAnalyze&&selected&&<form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/goals/'+goalId+'/reviews','POST',{text:note,kind:'correction'});setNote('');});}}><label htmlFor="review-note">Explain the finding to review</label><textarea id="review-note" value={note} onChange={e=>setNote(e.target.value)} required/><button disabled={busy}>Save review note</button></form>}{reviews.map(v=><article className="finding" key={v.id}><span className="tag">{v.body.kind}</span><p>{v.body.text}</p><small>{v.actor}</small></article>)}{manager&&<details><summary>Apply a source target correction</summary><form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/sources/'+domain+'/corrections','POST',{record_id:correctionId,target:Number(correctionTarget),explanation:note||'Manager correction'});});}}><label htmlFor="record-id">Record identifier</label><input id="record-id" value={correctionId} onChange={e=>setCorrectionId(e.target.value)} required/><label htmlFor="corrected-target">Corrected target value</label><input id="corrected-target" type="number" step="any" value={correctionTarget} onChange={e=>setCorrectionTarget(e.target.value)} required/><button disabled={busy}>Apply correction and invalidate affected findings</button></form></details>}</section>}
      {view==='history'&&<section><h2>Run history</h2>{runs.length?runs.map(r=><article className="finding" key={r.id}><div className="section-heading"><span className="tag">{r.status}</span><time>{new Date(r.created_at).toLocaleString()}</time></div><p>{r.body.question}</p><p className="muted">{r.body.operation} · Snapshot {r.snapshot_id.slice(0,12)}</p>{r.error&&<p className="error">{r.error}</p>}{r.result&&<p>{r.result.summary}</p>}{manager&&(r.status==='queued'||r.status==='running')&&<button disabled={busy} onClick={()=>action(async()=>{await api('/runs/'+r.id+'/cancel','POST',{});})}>Cancel run</button>}</article>):<p className="empty">No runs for the selected goal.</p>}</section>}
      {evidence!==null&&<section className="evidence"><div className="section-heading"><h2>Source and calculation evidence</h2><button onClick={()=>setEvidence(null)}>Close evidence</button></div><pre>{JSON.stringify(evidence,null,2)}</pre></section>}
      <footer>Local demonstration · $25 total frontier budget · No automated lending decisions</footer>
    </main>
  </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
