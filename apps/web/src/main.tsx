import React, { useEffect, useRef, useState } from 'react';
import './style.css';
import {ObjectiveForm, emptyObjective, type Objective} from './ObjectiveForm';
import {MethodStudyPanel, type MethodResult} from './MethodStudyPanel';
import {WorkflowTriggerPanel} from './WorkflowTriggerPanel';
import {WorkflowUpdateStatus, type WorkflowUpdateState} from './WorkflowUpdateStatus';
type Plan = {summary: string; mode: string; plan: {data_needs: string[]; steps: {action: string; purpose: string; expected_result: string}[]; assumptions: string[]; open_questions: string[]}};

type Principal = {id: string; role: string; domains: string[]; budget: {suite_usd: number}};
type Source = {id: string; domain: string; latest_snapshot: string|null; body: {name: string; question: string; caveat: string; terms_acknowledged: boolean; source_spec_sha256: string; license: string; kaggle: string; competition?: boolean}};
type Discovery = {summary: string; observed_at: string; fields: {schema: string; table: string; column: string; type: string}[]; limitations: string[]};
type Collection = {summary: string; coverage: {expected_rows: number; collected_rows: number; pending_rows: number}; limitations: string[]};
type Interpretation = {summary: string; mode: string; interpretation: {tables: {schema_name: string; table_name: string; grain: string; fields: {name: string; meaning: string; confidence: string; unit: string|null; limitations: string[]}[]}[]; unresolved: string[]}};
type Preparation = {summary: string; mode: string; coverage: {processed_rows: number; expected_rows: number; pending_rows: number}; unresolved_rows: number; repaired: boolean; limitations: string[]};
type Validation = {status: string; summary: string; source_rows?: number; candidate_rows?: number; failure_groups?: {reason:string}[]};
type ConnectedCalculation = {currency:string;period_start:string;period_end:string;coverage:{processed_rows:number;expected_rows:number};totals:{net_invoice_value:string;signed_cancellation_value:string;cancellation_reduction:string};dimensions:{label:string;field:string;groups:{value:string|number|null;row_count:number;net_value:string;signed_cancellation_value:string}[]}[]};
type Goal = {interpretation?: Interpretation|null; source_access?: boolean; collection?: Collection|null; discovery?: Discovery|null; plan?: Plan|null; id: string; domain: string; version: number; confirmed: boolean; paused: boolean; freshness: string; last_success: string|null; active_model: string|null; body: {question: string; definitions: Record<string,string>; notification_delta: number; budget_usd?: number; objective?: Objective}} & {preparation?: Preparation|null} & {validation?: Validation|null;workflows?:WorkflowVersion[]} & {update_status?:WorkflowUpdateState}
type TableRow = {group: string; count: number; labeled: number; mean: number|null};
type Finding = {claim: string; kind: string; evidence_ids: string[]};
type Result = {summary: string; findings?: Finding[]; limitations?: string[]; tables?: {title: string; rows: TableRow[]; evidence_id: string}[]; usage: {provider_usd: number; charge_status: string}; candidate_id?: string} & {calculation?:ConnectedCalculation;mode?:string} & MethodResult
type Run = {id: string; goal_id: string; status: string; created_at: string; snapshot_id: string|null; error?: string; result?: Result; body: {operation: string; question: string}} & {coverage?: {processed_rows:number;expected_rows:number|null;pending_rows:number|null}}
type Model = {id: string; promoted: boolean; body: {methods: {route: string; features?: string; metrics: Record<string,unknown>; calibration_metrics?: Record<string,unknown>}[]}};
type Review = {id: number; actor: string; body: {text: string; kind: string}};
const format = (n: number|null|undefined) => n == null ? 'Unavailable' : Intl.NumberFormat(undefined,{maximumFractionDigits:3}).format(n);

type WorkflowVersion = {version:string;created_at:number;mode:string;goal_version:number;question:string};

function SavedWorkflows({versions,inputs,canSave,canRun,disabled,onSave,onInspect,onDownload,onRun}:{versions:WorkflowVersion[];inputs:{id:string;created_at:string}[];canSave:boolean;canRun:boolean;disabled:boolean;onSave:()=>void;onInspect:(version:string)=>void;onDownload:(version:string)=>void;onRun:(version:string,inputRef?:string)=>void}) {
  const [inputRef,setInputRef]=useState('');
  return <div><h3>Reuse this procedure</h3>
    <p>Save the accepted steps, checks, and source references for another permitted run.</p>
    {canSave&&<button disabled={disabled} onClick={onSave}>Save checked workflow</button>}
    {canRun&&versions.length>0&&<label>Inputs for saved workflow<select value={inputRef} onChange={event=>setInputRef(event.target.value)} disabled={disabled}>
      <option value="">Original accepted collection</option>
      {inputs.map(item=><option key={item.id} value={item.id}>Collected {new Date(item.created_at).toLocaleString()} · {item.id.slice(0,12)}</option>)}
    </select></label>}
    {versions.map(item=><article key={item.version}><p>Workflow {item.version.slice(0,12)} · Goal version {item.goal_version}</p>
      {item.mode==='fixture'&&<p>This version contains a simulated method.</p>}
      <button disabled={disabled} onClick={()=>onInspect(item.version)}>Inspect saved workflow {item.version.slice(0,12)}</button>
      <button disabled={disabled} onClick={()=>onDownload(item.version)}>Download workflow {item.version.slice(0,12)}</button>
      {canRun&&<button disabled={disabled} onClick={()=>onRun(item.version,inputRef||undefined)}>Run saved workflow {item.version.slice(0,12)}</button>}
    </article>)}
  </div>;
}

function PreparationStatus({value,canRun,disabled,onRun}:{value?:Preparation|null;canRun:boolean;disabled:boolean;onRun:()=>void}) {
  return <div><h4>Prepare the collected data</h4>
    {canRun&&<button disabled={disabled} onClick={onRun}>Prepare source data</button>}
    {value&&<><p>{value.summary}</p>
      {value.mode==='fixture'&&<p>This preparation used a simulated field interpretation.</p>}
      <p>Prepared {format(value.coverage.processed_rows)} of {format(value.coverage.expected_rows)} rows. Pending: {format(value.coverage.pending_rows)}.</p>
      <p>Rows with unresolved conversions: {format(value.unresolved_rows)}.</p>
      {value.repaired&&<p>A failed conversion was repaired by preserving the original value and marking it unresolved.</p>}
      <ul>{value.limitations.map((item,i)=><li key={i}>{item}</li>)}</ul></>}
  </div>;
}

function ValidationStatus({value,canRun,disabled,onRun}:{value?:Validation|null;canRun:boolean;disabled:boolean;onRun:()=>void}) {
  return <div><h4>Check preparation meaning</h4>
    {canRun&&<button disabled={disabled} onClick={onRun}>Check prepared data</button>}
    {value&&<><p>Meaning check: {value.status}.</p><p>{value.summary}</p>
      <p>Source rows: {format(value.source_rows)}. Prepared rows: {format(value.candidate_rows)}.</p>
      {!!value.failure_groups?.length&&<><p>A checked answer is blocked. Affected source references are retained with the check evidence.</p>
        <ul>{value.failure_groups.slice(0,5).map((failure,i)=><li key={i}>{failure.reason}</li>)}</ul></>}
    </>}
  </div>;
}

function ConnectedAnswer({value,mode}:{value:ConnectedCalculation;mode?:string}) {
  return <section><h3>Complete source answer</h3>
    {mode==='fixture'&&<p>Simulated analysis method. Live agent method generation has not been verified.</p>}
    <p>Recorded period: {value.period_start} through {value.period_end}.</p>
    <p>Processed {format(value.coverage.processed_rows)} of {format(value.coverage.expected_rows)} rows.</p>
    <p>Net invoice value: {value.currency} {value.totals.net_invoice_value}. Signed cancellation value: {value.currency} {value.totals.signed_cancellation_value}.</p>
    {value.dimensions.map(dimension=>{
      const cutoff = dimension.groups[9]?.net_value;
      const shown = dimension.groups.filter((group,index)=>index<10||group.net_value===cutoff);
      return <div key={dimension.field}><h4>Net invoice value by {dimension.label}</h4>
        <p>Showing {shown.length} of {dimension.groups.length} groups, including every tie at the display cutoff. All groups are retained in the calculation evidence.</p>
        <table aria-label={'Net invoice value by '+dimension.field}><thead><tr><th>Group</th><th>Value ({value.currency})</th><th>Rows</th></tr></thead>
          <tbody>{shown.map((group,index)=><tr key={index}><td>{group.value===null?'Missing value':group.value===''?'Empty value':group.value}</td><td>{group.net_value}</td><td>{format(group.row_count)}</td></tr>)}</tbody>
        </table></div>;
    })}
  </section>;
}

export default function App() {
  const [token,setToken] = useState(() => new URLSearchParams(location.hash.slice(1)).get('access') || sessionStorage.getItem('backintel-access') || '');
  const [accessError,setAccessError] = useState('');
  function changeAccess(value: string, reason = '') {
    sessionStorage.removeItem('backintel-access');
    setAccessError(reason);setToken(value);
  }
  return <Workspace key={token} token={token} changeAccess={changeAccess} accessError={accessError}/>;
}

function Workspace({token,changeAccess,accessError}: {token: string; changeAccess: (token: string, reason?: string) => void; accessError: string}) {
  const active = useRef(true);
  const selection = useRef('');
  const detailRequest = useRef(0);
  const refreshRequest = useRef(0);
  const [entry,setEntry] = useState('');
  const [me,setMe] = useState<Principal|null>(null);
  const [sources,setSources] = useState<Source[]>([]);
  const [goals,setGoals] = useState<Goal[]>([]);
  const [notifications,setNotifications]=useState<{id:number;goal_id:string;domain:string;body:{message:string}}[]>([]);
  const [domain,setDomain] = useState('commerce');
  const [goalId,updateGoalId] = useState('');
  const [question,setQuestion] = useState('');
  const [draftObjective,setDraftObjective] = useState<Objective|null>(null);
  const [planFeedback,setPlanFeedback] = useState('');
  const [followup,setFollowup] = useState('');
  const [runs,setRuns] = useState<Run[]>([]);
  const [savedFinding,setCurrent] = useState<Run|null>(null);
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
  const current = savedFinding?.id === selected?.last_success ? savedFinding : null;
  const source = sources.find(s => s.domain === domain);
  const pending = runs.find(r => r.status === 'queued' || r.status === 'running') || importRun;

  function setGoalId(id: string) {
    selection.current=id;detailRequest.current++;
    updateGoalId(id);setRuns([]);setCurrent(null);setModels([]);setReviews([]);setEvidence(null);setProgress('');
  }
  function signOut(reason = '') {
    active.current=false;changeAccess('',reason);
  }
  function showError(error: unknown) {
    if (active.current && !(error instanceof DOMException && error.name === 'AbortError')) setError(error instanceof Error ? error.message : 'Request failed');
  }
  async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    if (!active.current) throw new DOMException('Workspace closed', 'AbortError');
    const r = await fetch('/api/v1'+path,{method,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body === undefined ? undefined : JSON.stringify(body)});
    const value = await r.json();
    if (!active.current) throw new DOMException('Workspace closed', 'AbortError');
    if (r.status===401 || r.status===403) signOut(value.detail || 'Access denied');
    if (!r.ok) throw new Error(value.detail || 'Request failed');
    return value as T;
  }
  async function refresh() {
    const generation = ++refreshRequest.current;
    const [p,s,g,n] = await Promise.all([api<Principal>('/me'),api<Source[]>('/sources'),api<Goal[]>('/goals'),api<typeof notifications>('/notifications')]);
    if (!active.current || generation!==refreshRequest.current) return;
    setMe(p); setSources(s); setGoals(g);
    setNotifications(n);
    if (selection.current && !g.some(goal=>goal.id===selection.current)) setGoalId('');
  }
  async function downloadWorkflow(version:string) {
    const packageValue=await api('/workflows/'+version+'/export');
    const url=URL.createObjectURL(new Blob([JSON.stringify(packageValue,null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='workflow-'+version+'.json';link.click();URL.revokeObjectURL(url);
  }
  async function details(id = goalId) {
    if (!id || id!==selection.current || !active.current) return;
    const generation=++detailRequest.current;
    const [r,m,v,f] = await Promise.all([api<Run[]>('/runs?goal_id='+id),api<Model[]>('/goals/'+id+'/models'),api<Review[]>('/goals/'+id+'/reviews'),api<Run|null>('/goals/'+id+'/findings')]);
    if (!active.current || id!==selection.current || generation!==detailRequest.current) return;
    setRuns(r); setModels(m); setReviews(v); setCurrent(f);
  }
  async function action(fn: () => Promise<void>) {
    setError('');setBusy(true);
    try {await fn();await refresh();await details();} catch(e) {showError(e);}
    finally {if(active.current)setBusy(false);}
  }
  useEffect(()=>{active.current=true;return()=>{active.current=false;};},[]);
  useEffect(() => {
    history.replaceState(null,'',location.pathname);
    if (token) {sessionStorage.setItem('backintel-access',token);refresh().catch(showError);}
  },[token]);
  useEffect(() => {if(goalId) details().catch(showError);},[goalId]);
  useEffect(()=>{if(!token)return;const timer=setInterval(()=>{refresh().then(()=>details()).catch(showError);},30000);return()=>clearInterval(timer);},[token,goalId]);
  useEffect(() => {setQuestion(source?.body.question || '');},[domain,source?.body.question]);
  useEffect(() => {setEditQuestion(selected?.body.question || '');},[goalId,selected?.version]);
  useEffect(() => {
    if (!pending) return;
    const controller = new AbortController();
    async function listen() {
      try {
        while (!controller.signal.aborted) {
        const response = await fetch('/api/v1/runs/'+pending!.id+'/events',{headers:{Authorization:'Bearer '+token},signal:controller.signal});
        if (!active.current || controller.signal.aborted) return;
        if (response.status===401 || response.status===403) signOut('Progress access denied');
        if (!response.ok) throw new Error('Progress access denied');
        const reader = response.body!.getReader();const decoder = new TextDecoder();let buffer = '';
        for (;;) {
          const {value,done} = await reader.read(); if (!active.current || controller.signal.aborted) return; if(done) break;
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
      } catch(e) {if(!controller.signal.aborted)showError(e);}
    }
    listen();return()=>controller.abort();
  },[pending?.id,token]);

  if (!me) return <main className="login"><p className="eyebrow">BackIntel</p><h1>Your analysis workspace</h1><p>Use your local access credential. Your role determines the sources and actions available.</p><form onSubmit={e=>{e.preventDefault();changeAccess(entry);}}><label htmlFor="credential">Access credential</label><input id="credential" type="password" value={entry} onChange={e=>setEntry(e.target.value)} autoComplete="off" required/><button>Open workspace</button></form>{(error||accessError)&&<p role="alert" className="error">{error||accessError}</p>}<p className="muted">Open securely with <code>python -m scripts.analysis_demo open --role manager</code>.</p></main>;
  return <div className="workspace">
    <aside className="sidebar"><a className="brand" href="/">BackIntel<span>Analysis workspace</span></a><p className="eyebrow">Sources</p><nav aria-label="Data domains">{sources.map(s=><button className={domain===s.domain?'selected':''} key={s.id} onClick={()=>{setDomain(s.domain);setGoalId('');}}>{s.domain[0].toUpperCase()+s.domain.slice(1)}<span className="source-state">{s.latest_snapshot?'Ready':'Awaiting data'}</span></button>)}</nav><p className="eyebrow">Saved goals</p><nav aria-label="Saved goals">{goals.filter(g=>g.domain===domain).map(g=><button className={goalId===g.id?'selected':''} key={g.id} onClick={()=>setGoalId(g.id)}>{g.body.question}<span className="source-state">{g.paused?'Paused':g.freshness}</span></button>)}</nav><div className="identity"><strong>{me.role}</strong><button onClick={()=>{signOut();}}>Sign out</button></div></aside>
    <main><header><div><p className="eyebrow">{domain} / {view}</p><h1>{selected?.body.objective ? 'Connected data analysis' : (source?.body.name || 'Select a source')}</h1></div><span className="model-label">GPT-6.1 Sol · hosted analyst</span></header>
      {error&&<div className="error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}>×</button></div>}
      <nav className="tabs" aria-label="Workspace views">{['analysis','sources','goals','conversation','review','history'].map(v=><button key={v} aria-current={view===v?'page':undefined} onClick={()=>setView(v)}>{v[0].toUpperCase()+v.slice(1)}</button>)}</nav>
      <><p className="caveat">{selected?.body.objective?.freshness || source?.body.caveat}</p>{view==='sources'&&selected?.body.objective&&<section><h2>Source connection</h2><dl><dt>Connection</dt><dd>{selected.body.objective.source_ref}</dd><dt>Read access</dt><dd>{selected.source_access?'Allowed':'Unavailable'}</dd><dt>Permitted schemas</dt><dd>{selected.body.objective.allowed_schemas.join(', ')}</dd><dt>Retained rows</dt><dd>{format(selected.collection?.coverage.collected_rows)}</dd></dl><p>{selected.body.objective.freshness}</p></section>}</>{notifications.map(n=><div role="status" className="progress" key={n.id}>{n.body.message} <button onClick={()=>{setDomain(n.domain);setGoalId(n.goal_id);setView('analysis');}}>Inspect updated answer</button></div>)}
      {importRun&&<p role="status" className="progress">Source import: {progress || "queued"}</p>}
      {view==='sources' && source && !selected?.body.objective && <section><h2>Source readiness</h2><dl><dt>Snapshot</dt><dd>{source.latest_snapshot||'No data imported'}</dd><dt>Source terms</dt><dd>{source.body.license} · {source.body.terms_acknowledged?'Confirmed':'Confirmation required'}</dd></dl><a href={'https://www.kaggle.com/'+(source.body.competition?'competitions/':'datasets/')+source.body.kaggle} target="_blank" rel="noreferrer">Review original source and terms</a>{manager&&<div className="actions"><button disabled={busy} onClick={()=>action(async()=>{await api('/sources/'+domain+'/terms','POST',{acknowledged:true,source_spec_sha256:source.body.source_spec_sha256});})}>Confirm source access and terms</button><button disabled={busy||!source.body.terms_acknowledged} onClick={()=>action(async()=>{setImportRun(await api<Run>('/sources/'+domain+'/refresh','POST',{}));})}>Import or check for updates</button></div>}<p className="muted">Original files stay outside Git. A changed snapshot refreshes saved goals.</p></section>}
      {view==='goals'&&<section><h2>Save a question</h2>{manager&&<div className="actions"><button disabled={busy} onClick={()=>setDraftObjective({...emptyObjective})}>Connect a business data source</button><button disabled={busy||domain!=='commerce'} onClick={()=>action(async()=>{const sample=await api<{question:string;objective:Objective}>('/reference-scenarios/online-retail');setQuestion(sample.question);setDraftObjective(sample.objective);})}>Use historical retail demo</button></div>}{manager&&draftObjective?<><p>Saving this objective starts with a zero model-spending limit. Planning is a separate action.</p><ObjectiveForm key={draftObjective.source_ref} question={question} objective={draftObjective} busy={busy} onSave={value=>action(async()=>{const g=await api<Goal>('/goals','POST',{domain,...value});setGoalId(g.id);setDraftObjective(null);})}/><button disabled={busy} onClick={()=>setDraftObjective(null)}>Use a registered dataset instead</button></>:manager?<form onSubmit={e=>{e.preventDefault();action(async()=>{const g=await api<Goal>('/goals','POST',{domain,question});setGoalId(g.id);});}}><label htmlFor="question">Question to monitor</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={2000} required/><button disabled={busy}>Propose goal</button></form>:<p>Managers configure standing questions. Select a permitted goal to investigate.</p>}{selected&&<div className="definitions"><h3>Confirm business meaning</h3>{selected.body.objective&&<><p>This goal uses the saved connection {selected.body.objective.source_ref}. Confirm the objective to discover the permitted tables and fields.</p>{canAnalyze&&<button disabled={busy||!!pending||!selected.source_access} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'discovery'});})}>Discover connected data</button>}{canAnalyze&&<button disabled={busy||!!pending||!selected.source_access||!selected.discovery} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'collection'});})}>Collect complete source</button>}{manager&&<button disabled={busy||!!pending||!selected.source_access||!selected.collection||!(selected.body.budget_usd&&selected.body.budget_usd>0)} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'interpretation'});})}>Interpret source fields</button>}{selected.interpretation&&<div><h3>Proposed field meanings</h3><p>{selected.interpretation.summary}</p>{selected.interpretation.mode==='fixture'&&<p>Simulated interpretation. Live field interpretation has not been verified.</p>}{selected.interpretation.interpretation.tables.map(table=><div key={table.schema_name+'.'+table.table_name}><h4>{table.schema_name}.{table.table_name}</h4><p>{table.grain}</p><ul>{table.fields.map(field=><li key={field.name}><strong>{field.name}</strong>: {field.meaning} · {field.confidence}{field.unit&&' · '+field.unit}{field.limitations.map((item,i)=><p key={i}>{item}</p>)}</li>)}</ul></div>)}<h4>Unresolved meaning</h4><ul>{selected.interpretation.interpretation.unresolved.map((item,i)=><li key={i}>{item}</li>)}</ul><><p>{selected.preparation ? 'Preparation is available; analysis has not run.' : 'No preparation or analysis has run.'}</p><><PreparationStatus value={selected.preparation} canRun={manager} disabled={busy||!!pending||!selected.source_access||!selected.interpretation} onRun={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'preparation'});})}/>{selected.preparation&&<><ValidationStatus value={selected.validation} canRun={manager} disabled={busy||!!pending||!selected.source_access} onRun={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'validation'});})} />{manager&&<button disabled={busy||!!pending||!selected.source_access||selected.validation?.status!=='passed'||!(selected.body.budget_usd&&selected.body.budget_usd>0)} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'answer'});})}>Answer saved question</button>}</>}</></></div>}{selected.collection&&<div><h3>Retained source data</h3><p>{selected.collection.summary}</p><p>Collected {format(selected.collection.coverage.collected_rows)} of {format(selected.collection.coverage.expected_rows)} rows. Pending: {format(selected.collection.coverage.pending_rows)}.</p>{selected.collection.limitations.map((item,i)=><p className="caveat" key={i}>{item}</p>)}</div>}<p>Discovery checks access and field names. It makes no model call and does not yet collect or analyze records.</p>{selected.discovery&&<div><h3>Discovered source structure</h3><p>{selected.discovery.summary}</p><p>Observed: {selected.discovery.observed_at}</p><div className="table-scroll"><table><caption>Permitted source fields</caption><thead><tr><th>Schema</th><th>Table</th><th>Field</th><th>Storage type</th></tr></thead><tbody>{selected.discovery.fields.map(field=><tr key={[field.schema,field.table,field.column].join('.')}><td>{field.schema}</td><td>{field.table}</td><td>{field.column}</td><td>{field.type}</td></tr>)}</tbody></table></div>{selected.discovery.limitations.map((item,i)=><p key={i} className="caveat">{item}</p>)}</div>}{manager&&<details><summary>Revise the business objective</summary><ObjectiveForm key={selected.id+':objective:'+selected.version} question={selected.body.question} objective={selected.body.objective} busy={busy} onSave={value=>action(async()=>{await api('/goals/'+goalId,'PATCH',value);})}/></details>}{selected.plan&&<div><h3>Saved agent proposal</h3><p>{selected.plan.summary}</p>{selected.plan.mode==='fixture'&&<p>Simulated provider response. This does not prove live agent planning.</p>}<p>This proposal has not connected to the source or executed an analysis.</p><h4>Information needed</h4><ul>{selected.plan.plan.data_needs.map((item,i)=><li key={i}>{item}</li>)}</ul><ol>{selected.plan.plan.steps.map((step,i)=><li key={i}><strong>{step.purpose}</strong><p>{step.expected_result}</p></li>)}</ol><h4>Assumptions and unresolved questions</h4><ul>{[...selected.body.objective.open_questions,...selected.plan.plan.assumptions,...selected.plan.plan.open_questions].map((item,i)=><li key={i}>{item}</li>)}</ul></div>}{manager&&<><label htmlFor="plan-feedback">Plan revision request, if needed</label><textarea id="plan-feedback" value={planFeedback} maxLength={2000} onChange={e=>setPlanFeedback(e.target.value)}/><button disabled={busy||selected.paused||!!pending||!(selected.body.budget_usd&&selected.body.budget_usd>0)} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'planning',question:planFeedback||null});})}>Generate agent plan</button><p>Requires a positive model-spending limit. Repeating the same request reuses its saved result.</p></>}</>}<dl>{Object.entries(selected.body.definitions).map(([k,v])=><React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl>{manager&&<><form key={selected.id+':'+selected.version} onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);action(async()=>{await api('/goals/'+goalId,'PATCH',{threshold:Number(data.get('threshold')),budget_usd:Number(data.get('budget'))});});}}><label htmlFor="threshold">Notify when a group mean changes by at least</label><input id="threshold" name="threshold" type="number" min="0" max="100000" step="any" defaultValue={selected.body.notification_delta} required/><label htmlFor="budget">Maximum frontier cost per run (USD)</label><input id="budget" name="budget" type="number" min="0" max="1" step="0.01" defaultValue={selected.body.budget_usd??1} required/><button disabled={busy}>Save goal limits</button></form><label htmlFor="edit-question">Standing question</label><textarea id="edit-question" value={editQuestion} onChange={e=>setEditQuestion(e.target.value)}/><div className="actions"><button disabled={busy||editQuestion===selected.body.question} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{question:editQuestion});})}>Save revised question</button><button disabled={busy||selected.confirmed} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{confirmed:true});})}>Confirm definitions</button><button disabled={busy} onClick={()=>action(async()=>{await api('/goals/'+goalId,'PATCH',{paused:!selected.paused});})}>{selected.paused?'Resume goal':'Pause goal'}</button></div></>}</div>}</section>}
      {view==='analysis'&&<section><div className="section-heading"><h2>{selected?.body.question||'Choose a saved goal'}</h2>{selected && canAnalyze && !selected.body.objective && <button disabled={busy||!selected.confirmed||selected.paused} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{});})}>Run analysis</button>}</div>{pending&&<p role="status" className="progress">{pending.body.operation==='training'?'Comparing prediction methods':'Analysis in progress'} · {progress||pending.status}</p>}{selected&&<p className="muted">Answer status: {selected.freshness} · Goal version {selected.version}</p>}{current?.result?<><><p className="answer">{current.result.summary}</p>{current.result.calculation&&<> <><ConnectedAnswer value={current.result.calculation} mode={current.result.mode} /><MethodStudyPanel key={goalId} runs={runs} canStart={!!manager && !!selected?.source_access && selected.confirmed && !selected.paused} disabled={busy||!!pending} onStart={policy=>action(async()=>{await api("/runs/"+current.id+"/method-studies","POST",policy);})} onSave={identity=>action(async()=>{setEvidence(await api("/runs/"+identity+"/workflow","POST"));})} onInspect={identity=>action(async()=>{setEvidence(await api("/runs/"+identity));})}/></>{selected&&<><SavedWorkflows versions={selected.workflows||[]} canSave={!!manager && !!selected.source_access && current.body.operation==='answer'} disabled={busy||!!pending} onSave={()=>action(async()=>{setEvidence(await api('/runs/'+current.id+'/workflow','POST'));})} onInspect={version=>action(async()=>{setEvidence(await api('/workflows/'+version));})} onDownload={version=>action(()=>downloadWorkflow(version))} key={goalId} inputs={runs.filter(run=>run.body.operation==='collection'&&run.status==='succeeded')} canRun={!!manager && !!selected.source_access && selected.confirmed && !selected.paused} onRun={(version,inputRef)=>action(async()=>{await api('/workflows/'+version+'/runs','POST',{input_ref:inputRef});})} />{manager&&<><WorkflowUpdateStatus value={selected.update_status}/><WorkflowTriggerPanel key={goalId} goalId={goalId} versions={selected.workflows||[]} api={api} canCreate={!!selected.source_access&&!selected.paused} /></>}</>} </>}</>{current.result.findings?.map((f,i)=><article className="finding" key={i}><span className="tag">{f.kind}</span><p>{f.claim}</p>{f.evidence_ids.map(id=><button className="text-button" key={id} onClick={()=>action(async()=>{setEvidence(await api('/evidence/'+id));})}>Inspect calculation</button>)}</article>)}{current.result.tables?.map((t,i)=><div key={i}><h3>{t.title}</h3><div className="table-scroll"><table><thead><tr><th>Group</th><th>Records</th><th>Known values</th><th>Mean</th></tr></thead><tbody>{t.rows.map(row=><tr key={row.group}><td>{row.group}</td><td>{format(row.count)}</td><td>{format(row.labeled)}</td><td>{format(row.mean)}</td></tr>)}</tbody></table></div><figure aria-label={t.title+' mean comparison'}>{t.rows.filter(r=>r.mean!==null).map(row=><div className="chart-row" key={row.group}><span>{row.group}</span><meter min={0} max={Math.max(1,...t.rows.map(r=>r.mean||0))} value={Math.max(0,row.mean||0)} aria-label={row.group+' mean'}/><span>{format(row.mean)}</span></div>)}<figcaption>Calculated values for the displayed groups.</figcaption></figure></div>)}{current.result.limitations?.map((s,i)=><p className="caveat" key={i}>{s}</p>)}<p className="muted">Measured inference: ${format(current.result.usage.provider_usd)} · {current.result.usage.charge_status}</p></>:<div className="empty"><h3>No completed answer yet</h3><p>Select a goal, confirm its definitions, and run the analysis. Partial runs remain in history.</p></div>}</section>}
      {view==='conversation'&&<section><h2>Ask a follow-up</h2><p>The standing goal changes only when a manager saves a revision.</p><form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/goals/'+goalId+'/runs','POST',{question:followup});setFollowup('');});}}><label htmlFor="followup">Follow-up question</label><textarea id="followup" value={followup} onChange={e=>setFollowup(e.target.value)} required maxLength={2000}/><button disabled={busy||!canAnalyze||!selected?.confirmed}>Investigate</button></form>{runs.filter(r=>r.body.operation==='analysis'&&r.body.question!==selected?.body.question).map(r=><article className="finding" key={r.id}><h3>{r.body.question}</h3><p className="muted">{r.status}</p>{r.result&&<><p className="answer">{r.result.summary}</p>{r.result.findings?.map((f,i)=><div key={i}><p>{f.claim}</p>{f.evidence_ids.map(id=><button className="text-button" key={id} onClick={()=>action(async()=>{setEvidence(await api('/evidence/'+id));})}>Inspect calculation</button>)}</div>)}{r.result.limitations?.map((text,i)=><p className="muted" key={i}>{text}</p>)}</>}</article>)}</section>}
      {view==='review'&&<section><h2>Prediction candidates</h2><p>Training can run automatically. A manager approves each replacement.</p>{manager&&selected&&<button disabled={busy||!selected.confirmed||selected.paused} onClick={()=>action(async()=>{await api('/goals/'+goalId+'/runs','POST',{operation:'training'});})}>Compare real predictors</button>}{models.map(m=><article className="finding" key={m.id}><p className="muted">Candidate {m.id.slice(0,12)} · {m.promoted?'Approved':'Awaiting manager'}</p><div className="table-scroll"><table><thead><tr><th>Method</th><th>Features</th><th>{m.promoted?'Held-out evaluation':'Calibration for selection'}</th></tr></thead><tbody>{m.body.methods.map((method,i)=><tr key={i}><td>{method.route}</td><td>{method.features||'Baseline'}</td><td>{Object.entries((m.promoted?method.metrics:method.calibration_metrics)||{}).filter(([,v])=>typeof v==='number').map(([k,v])=>k+': '+format(v as number)).join(' · ')}</td></tr>)}</tbody></table></div>{manager&&!m.promoted&&m.body.methods.filter(method=>['catboost','tabiclv2'].includes(method.route)).map(method=><button key={method.route+'-'+method.features} disabled={busy} onClick={()=>action(async()=>{await api('/models/'+m.id+'/promote','POST',{route:method.route+'-'+(method.features||'facts')});})}>Approve {method.route} ({method.features||'facts'})</button>)}</article>)}<h2>Review notes and corrections</h2>{canAnalyze&&selected&&<form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/goals/'+goalId+'/reviews','POST',{text:note,kind:'correction'});setNote('');});}}><label htmlFor="review-note">Explain the finding to review</label><textarea id="review-note" value={note} onChange={e=>setNote(e.target.value)} required/><button disabled={busy}>Save review note</button></form>}{reviews.map(v=><article className="finding" key={v.id}><span className="tag">{v.body.kind}</span><p>{v.body.text}</p><small>{v.actor}</small></article>)}{manager&&<details><summary>Apply a source target correction</summary><form onSubmit={e=>{e.preventDefault();action(async()=>{await api('/sources/'+domain+'/corrections','POST',{record_id:correctionId,target:Number(correctionTarget),explanation:note||'Manager correction'});});}}><label htmlFor="record-id">Record identifier</label><input id="record-id" value={correctionId} onChange={e=>setCorrectionId(e.target.value)} required/><label htmlFor="corrected-target">Corrected target value</label><input id="corrected-target" type="number" step="any" value={correctionTarget} onChange={e=>setCorrectionTarget(e.target.value)} required/><button disabled={busy}>Apply correction and invalidate affected findings</button></form></details>}</section>}
      {view==='history'&&<section><h2>Run history</h2>{runs.length?runs.map(r=><article className="finding" key={r.id}><div className="section-heading"><span className="tag">{r.status}</span><time>{new Date(r.created_at).toLocaleString()}</time></div><><p>{r.body.question}</p>{r.coverage&&<p>Prepared {format(r.coverage.processed_rows)} of {format(r.coverage.expected_rows)} rows. Pending: {format(r.coverage.pending_rows)}.</p>}</><p className="muted">{r.body.operation} · Snapshot {(r.snapshot_id?.slice(0,12)||'connected source')}</p>{r.error&&<p className="error">{r.error}</p>}{r.result&&<p>{r.result.summary}</p>}{manager&&(r.status==='queued'||r.status==='running')&&<button disabled={busy} onClick={()=>action(async()=>{await api('/runs/'+r.id+'/cancel','POST',{});})}>Cancel run</button>}</article>):<p className="empty">No runs for the selected goal.</p>}</section>}
      {evidence!==null&&<section className="evidence"><div className="section-heading"><h2>Source and calculation evidence</h2><button onClick={()=>setEvidence(null)}>Close evidence</button></div><pre>{JSON.stringify(evidence,null,2)}</pre></section>}
      <footer>Local demonstration · ${format(me.budget.suite_usd)} total frontier budget · No automated lending decisions</footer>
    </main>
  </div>;
}
