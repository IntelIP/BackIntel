import React, {useEffect, useRef, useState} from 'react';

type Trigger = {id:string;state:string;workflow_version:string;next_due:string|null;expires_at:string;accepted_count:number;timer_error?:string;cron_id?:string|null;
  body:{event_source:string;timezone:string;max_runs:number;max_spend_usd:number};
  attempts:{sequence:number;created_at:string;occurrence:string;status:string;reason:string;run_id:string|null;run_status:string|null}[]};
type Api = <T>(path:string,method?:string,body?:unknown)=>Promise<T>;

export function WorkflowTriggerPanel({goalId,versions,api,canCreate}:{goalId:string;versions:{version:string;question:string}[];api:Api;canCreate:boolean}) {
  const [triggers,setTriggers]=useState<Trigger[]>([]);
  const [version,setVersion]=useState('');
  const [source,setSource]=useState('');
  const [runAt,setRunAt]=useState('');
  const [expires,setExpires]=useState('');
  const [maxRuns,setMaxRuns]=useState(2);
  const [refreshSource,setRefreshSource]=useState(true);
  const [refreshMessage,setRefreshMessage]=useState('');
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const currentApi=useRef(api);currentApi.current=api;
  const timezone=Intl.DateTimeFormat().resolvedOptions().timeZone;
  useEffect(()=>{
    let active=true;
    const refresh=()=>currentApi.current<Trigger[]>('/goals/'+goalId+'/triggers').then(value=>{if(active)setTriggers(value);}).catch(reason=>{if(active)setError(reason instanceof Error?reason.message:'Could not read triggers');});
    void refresh();const timer=setInterval(refresh,5000);
    return ()=>{active=false;clearInterval(timer);};
  },[goalId]);
  async function action(work:()=>Promise<{timer_error?:string}>) {
    setBusy(true);setError('');
    try {
      const value=await work();
      if(value.timer_error)setError('Schedule setup or cleanup needs attention: '+value.timer_error);
      setTriggers(await api<Trigger[]>('/goals/'+goalId+'/triggers'));
    } catch(reason) {setError(reason instanceof Error?reason.message:'Trigger change failed');}
    finally {setBusy(false);}
  }
  return <section aria-label="Automatic workflow starts"><h3>Start this work automatically</h3>
    <p>Collect current information and run the saved analysis without new model calls. The last accepted answer stays available while updates are checked.</p>
    {canCreate&&<div>
      <label>Workflow to refresh<select aria-label="Workflow to refresh" style={{width:'100%',minWidth:0}} value={version} onChange={event=>setVersion(event.target.value)}><option value="">Choose a saved workflow</option>{versions.map(item=><option key={item.version} value={item.version}>{item.question} · {item.version.slice(0,12)}</option>)}</select></label>
      <button type="button" disabled={busy||!version} onClick={()=>void action(async()=>{
        const result=await api<{timer_error?:string}>('/workflows/'+version+'/refresh','POST',{request_id:crypto.randomUUID()});
        setRefreshMessage('Refresh queued. Check the answer update status for progress.');return result;
      })}>Refresh from source</button>
      {refreshMessage&&<p role="status">{refreshMessage}</p>}
    </div>}
    {error&&<p role="alert">{error}</p>}
    {canCreate&&<form onSubmit={event=>{event.preventDefault();void action(()=>api<Trigger>('/workflows/'+version+'/triggers','POST',{
      event_source:source,timezone,run_at:runAt?new Date(runAt).toISOString():null,expires_at:new Date(expires).toISOString(),max_runs:maxRuns,max_spend_usd:0,refresh_source:refreshSource
    }));}}>
      <label>Saved workflow<select style={{width:"100%",minWidth:0}} value={version} required onChange={event=>setVersion(event.target.value)}><option value="">Choose a saved workflow</option>{versions.map(item=><option key={item.version} value={item.version}>{item.question} · {item.version.slice(0,12)}</option>)}</select></label>
      <label>Permitted event source<input required maxLength={160} value={source} onChange={event=>setSource(event.target.value)}/></label>
      <label>Run once at ({timezone}, optional)<input type="datetime-local" value={runAt} onChange={event=>setRunAt(event.target.value)}/></label>
      <label>Authority expires at ({timezone})<input type="datetime-local" required value={expires} onChange={event=>setExpires(event.target.value)}/></label>
      <label>Maximum accepted starts<input type="number" required min={1} max={100} value={maxRuns} onChange={event=>setMaxRuns(Number(event.target.value))}/></label>
      <label><input type="checkbox" checked={refreshSource} onChange={event=>setRefreshSource(event.target.checked)}/>Collect current source changes before each automatic start</label>
      <p>Model spending limit: $0. Duplicate event identities reuse accepted work.</p>
      <button disabled={busy||!version}>Create bounded trigger</button>
    </form>}
    {triggers.map(trigger=><article key={trigger.id}><h4>{trigger.body.event_source}</h4>
      <p>Status: {trigger.state}. Accepted starts: {trigger.accepted_count} of {trigger.body.max_runs}.</p>
      {trigger.timer_error&&<p role="alert">Schedule needs attention: {trigger.timer_error}</p>}
      <p>Next run: {trigger.next_due?new Date(trigger.next_due).toLocaleString(undefined,{timeZone:trigger.body.timezone}):'No pending scheduled run'} · {trigger.body.timezone}. Expires: {new Date(trigger.expires_at).toLocaleString(undefined,{timeZone:trigger.body.timezone})}.</p>
      <p>Event address: <code>/api/v1/triggers/{trigger.id}/events</code>. The owner’s access credential is required.</p>
      {trigger.state==='active'&&<button disabled={busy} onClick={()=>void action(()=>api<Trigger>('/triggers/'+trigger.id,'PATCH',{state:'paused'}))}>Pause trigger</button>}
      {trigger.state==='paused'&&<button disabled={busy} onClick={()=>void action(()=>api<Trigger>('/triggers/'+trigger.id,'PATCH',{state:'active'}))}>Resume trigger</button>}
      {trigger.state!=='removed'&&<button disabled={busy} onClick={()=>void action(()=>api<Trigger>('/triggers/'+trigger.id,'PATCH',{state:'removed'}))}>Remove schedule and trigger</button>}
      {trigger.state==='removed'&&(trigger.cron_id||trigger.timer_error)&&<button disabled={busy} onClick={()=>void action(()=>api<Trigger>('/triggers/'+trigger.id,'PATCH',{state:'removed'}))}>Retry schedule cleanup</button>}
      <details><summary>Run and attempt history</summary>{trigger.attempts.length===0?<p>No attempts yet.</p>:<ol>{trigger.attempts.map(attempt=><li key={attempt.sequence}>
        {new Date(attempt.created_at).toLocaleString()} · {attempt.status}{attempt.run_status&&' · Work '+attempt.run_status}: {attempt.reason}<br/>
        <small>{attempt.occurrence}{attempt.run_id&&' · Run '+attempt.run_id.slice(0,12)}</small>
      </li>)}</ol>}</details>
    </article>)}
  </section>;
}
