import { useEffect, useRef, useState, type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import { ArrowLeft, ArrowSquareOut, CaretDown, CheckCircle, Clock, FileText, Funnel, GearSix, Tray as Inbox, Info, MagnifyingGlass, Plus, SealCheck, SidebarSimple, Sparkle, Tray, X } from '@phosphor-icons/react'
import { ApiError, loadWorkspace, saveDecision, type Case, type Decision, type Workspace } from './api'
import { Button } from './ui'
import { DemoOverview } from './DemoOverview'

const decisions: { value: Decision; label: string }[] = [
  { value: 'follow_up', label: 'Follow up' }, { value: 'no_action', label: 'No action' }, { value: 'need_more_information', label: 'Need more info' },
]

function Evidence({ item, children }: { item: Case; children: ReactNode }) {
  return <Dialog.Root><Dialog.Trigger asChild>{children}</Dialog.Trigger><Dialog.Portal>
    <Dialog.Overlay className="drawer-overlay" />
    <Dialog.Content className="evidence-drawer">
      <header><div><Dialog.Title>Source evidence</Dialog.Title><Dialog.Description>Original record used for this finding.</Dialog.Description></div><Dialog.Close asChild><Button aria-label="Close evidence"><X size={20} /></Button></Dialog.Close></header>
      <div className="drawer-body"><span className="eyebrow">{item.simulated ? 'Simulated record' : 'Archived public issue'}</span><h2>{item.title}</h2>
        <div className="source-meta">Source date {new Date(item.evidence.collected_at).toLocaleDateString('en-US', { dateStyle: 'medium', timeZone: 'UTC' })}</div>
        <pre>{item.evidence.text}</pre>
        {item.evidence.url && <a href={item.evidence.url} target="_blank" rel="noreferrer">Open original source <ArrowSquareOut size={15} /></a>}
        <details><summary>Record fingerprint</summary><code>{item.evidence.sha256}</code></details>
        <p className="quiet-note">Current source content may differ from this archived snapshot.</p>
      </div>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>
}

function CaseReader({ item, unavailable, onSaved, onRefresh, onBack }: { item: Case; unavailable: boolean; onSaved: (item: Case) => void; onRefresh: () => void; onBack: () => void }) {
  const [decision, setDecision] = useState<Decision>(item.review?.decision ?? 'follow_up')
  const [reason, setReason] = useState(item.review?.reason ?? '')
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const saveInProgress = useRef(false)
  const [tab, setTab] = useState('finding')
  const boundSource = useRef(item.evidence.sha256)
  const boundRevision = useRef(item.review?.revision ?? 0)
  const sourceChanged = boundSource.current !== item.evidence.sha256

  async function refreshCase() {
    try {
      const current = (await loadWorkspace()).cases.find(row => row.id === item.id)
      if (!current) throw new Error('This case is no longer in the current packet.')
      boundSource.current = current.evidence.sha256; boundRevision.current = current.review?.revision ?? 0
      onSaved(current); setError(''); setNotice('Case refreshed. Review your existing note before saving.')
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not refresh the case.') }
    onRefresh()
  }

  async function submit() {
    if (!reason.trim() || saveInProgress.current || sourceChanged || unavailable) return
    saveInProgress.current = true; setSaving(true); setError(''); setNotice('')
    try {
      const updated = await saveDecision(item.id, decision, reason.trim(), boundRevision.current, boundSource.current)
      boundRevision.current = updated.review?.revision ?? 0
      onSaved(updated); setNotice(updated.outcome ? 'Decision saved. Later outcome is now available.' : 'Decision saved. No later outcome is available yet.')
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? 'This case changed in another view. Refresh the case before saving.' : err instanceof Error ? err.message : 'Could not save. Try again.')
    } finally { saveInProgress.current = false; setSaving(false) }
  }

  return <main className="reader" aria-label="Selected case">
    <header className="case-toolbar"><Button className="mobile-back" onClick={onBack} aria-label="Back to cases"><ArrowLeft size={18} /></Button><span className="case-number">{item.id}</span><div className="toolbar-actions"><Evidence item={item}><Button aria-label="Open evidence"><FileText size={17} /></Button></Evidence><span className="reviewer-avatar">H</span><span className="reviewer-name">Reviewer</span><Button variant="outline" className="review-state" onClick={()=>setTab('activity')}><CheckCircle size={15} />{item.review ? 'Reviewed' : 'Needs review'}</Button></div></header>
    <div className="case-heading"><h1>{item.title}</h1><div className="case-tags"><span className="source-tag"><span className="tiny-dot" />{item.source_kind}</span><span className="tag">{item.simulated ? 'Simulated' : 'Historical replay'}</span></div></div>
    <Tabs.Root value={tab} onValueChange={setTab} className="case-tabs">
      <Tabs.List aria-label="Case sections" className="tab-list"><Tabs.Trigger value="finding">Finding</Tabs.Trigger><Tabs.Trigger value="activity">Decision history</Tabs.Trigger><Tabs.Trigger value="outcome">Later outcome{!item.review && <span className="locked-dot" />}</Tabs.Trigger></Tabs.List>
      <div className="reader-scroll">
        <Tabs.Content value="finding" className="tab-content">
          <div className="timeline-row"><div className="timeline-icon source"><FileText size={17} /></div><section className="record-block"><div className="record-heading"><strong>Source record</strong><span>{new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })}</span></div><p>{item.summary}</p><Evidence item={item}><Button className="source-link">Read original evidence <ArrowSquareOut size={13} /></Button></Evidence></section></div>
          <div className="timeline-label"><span />Observed facts<span /></div>
          <div className="facts-grid">{item.facts.map(fact=><div key={fact.label}><span>{fact.label}</span><strong>{fact.value}</strong></div>)}</div>
          <div className="timeline-row finding-row"><div className="timeline-icon agent"><Sparkle size={17} weight="fill" /></div><section className="record-block finding-block"><div className="record-heading"><strong>BackIntel</strong><span>{item.finding.status}</span></div><p>{item.finding.text}</p><span className="small-label">Suggested review step · Check evidence before acting</span></section></div>
          <details className="prediction-details"><summary><Info size={14} /><span>Prediction estimates</span><span className="experimental">Experimental</span><CaretDown size={14} /></summary><p>{item.prediction.explanation}</p><div className="estimates">{Object.entries(item.prediction.estimates).map(([name,value])=><div key={name}><span>{name}</span><strong>{Math.round(value*100)}%</strong></div>)}</div><p className="quiet-note">These estimates do not set queue order.</p></details>
        </Tabs.Content>
        <Tabs.Content value="activity" className="tab-content"><div className="section-intro"><SealCheck size={24} /><h2>Decision history</h2><p>{item.review ? 'Saved on the local server. Available across both demo frontends.' : 'No decision has been recorded for this case.'}</p></div>{item.history.map(review=><div className="history-entry" key={review.revision}><strong>{decisions.find(d=>d.value===review.decision)?.label}</strong><p>{review.reason}</p><span>Revision {review.revision} · {new Date(review.recorded_at).toLocaleString()}</span></div>)}</Tabs.Content>
        <Tabs.Content value="outcome" className="tab-content"><div className="section-intro"><Clock size={24} /><h2>Later outcome</h2><p>{item.outcome ? item.outcome.text : 'Record your first decision before viewing the later outcome. This keeps later knowledge out of the initial review.'}</p>{item.outcome && <span>{new Date(item.outcome.available_at).toLocaleDateString()}</span>}</div></Tabs.Content>
      </div>
    </Tabs.Root>
    <div className="decision-composer"><div className="composer-top"><span>Your decision</span><span className="small-label">{item.review ? `Saved · revision ${item.review.revision}` : 'Not recorded'}</span></div>
      <div className="decision-options" role="group" aria-label="Decision">{decisions.map(option=><Button key={option.value} aria-pressed={decision===option.value} className={decision===option.value?'decision-active':''} onClick={()=>setDecision(option.value)}>{option.label}</Button>)}</div>
      <label className="sr-only" htmlFor="decision-reason">Reason and next step</label><textarea id="decision-reason" maxLength={2000} placeholder="Add your reason and next step…" value={reason} onChange={e=>{setReason(e.target.value);setNotice('')}} />
      <div className="composer-footer"><span className="quiet-note"><SealCheck size={13} />Evidence stays linked to your decision</span><Button variant="primary" disabled={!reason.trim() || saving || sourceChanged || unavailable} onClick={submit}>{saving?'Saving…':'Save decision'}</Button></div>
      {unavailable && <p role="alert" className="save-error">Current evidence is unavailable. Saving is disabled until the workspace refreshes.</p>}
      {sourceChanged && <div role="alert" className="save-error">New source information arrived. Refresh the case before saving. Your draft is preserved. <Button onClick={refreshCase}>Refresh case</Button></div>}
      {notice && <p role="status" className="save-success">{notice}</p>}{error && <div role="alert" className="save-error">{error} {error.includes('Refresh') && <Button onClick={refreshCase}>Refresh case</Button>}</div>}
    </div>
  </main>
}

export function App() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [workflow, setWorkflow] = useState<'issues'|'equipment'>('issues')
  const [filter, setFilter] = useState('open')
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [mobileCase, setMobileCase] = useState(false)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [overview, setOverview] = useState(false)
  const demoOpened = useRef(false)

  useEffect(()=>{
    const controller = new AbortController(); setError('')
    loadWorkspace(controller.signal).then(data=>{setWorkspace(data);if(data.demo&&!demoOpened.current){demoOpened.current=true;setOverview(true)}}).catch(err=>{if(err.name!=='AbortError')setError('Could not load the workspace. Check the local service and try again.')})
    return ()=>controller.abort()
  },[refresh])
  useEffect(()=>{
    if (workspace?.demo?.status !== 'running') return
    const interval=setInterval(()=>setRefresh(value=>value+1),1500)
    return ()=>clearInterval(interval)
  },[workspace?.demo?.status])
  const cases=(workspace?.cases??[]).filter(item=>item.workflow===workflow)
  const visible=cases.filter(item=>(filter==='all'||(filter==='open'?!item.review:!!item.review))&&`${item.id} ${item.title} ${item.summary}`.toLowerCase().includes(query.toLowerCase()))
  const selected=visible.find(item=>item.id===selectedId)??visible[0]
  const counts={open:cases.filter(item=>!item.review).length,reviewed:cases.filter(item=>item.review).length,all:cases.length}
  function changeWorkflow(next:'issues'|'equipment'){setWorkflow(next);setQuery('');setSelectedId('');setFilter('open');setMobileCase(false);setOverview(false)}
  function updateCase(item:Case){setWorkspace(current=>current?{...current,cases:current.cases.map(row=>row.id===item.id?item:row)}:current);setFilter('all');setSelectedId(item.id)}

  return <div className={`workspace ${navCollapsed?'nav-collapsed':''} ${mobileCase?'mobile-case-open':''}`}>
    <aside className="navigation" aria-label="Workspace navigation"><div className="brand-row"><span className="brand-mark"><Sparkle size={17} weight="fill" /></span><strong>BackIntel</strong><Button aria-label="Collapse navigation" onClick={()=>setNavCollapsed(true)}><SidebarSimple size={17} /></Button></div>
      <div className="navigation-search"><MagnifyingGlass size={16} /><span>Decision workspace</span></div>
      <nav aria-label="Review status">{workspace?.demo&&<button className={overview?'selected':''} onClick={()=>{setOverview(true);setMobileCase(true)}}><Sparkle size={17}/><span>Workflow demo</span></button>}<button className={filter==='open'&&!overview?'selected':''} onClick={()=>{setFilter('open');setMobileCase(false);setOverview(false)}}><Inbox size={17} /><span>Needs review</span><span className="nav-count">{counts.open}</span></button><button className={filter==='reviewed'&&!overview?'selected':''} onClick={()=>{setFilter('reviewed');setMobileCase(false);setOverview(false)}}><CheckCircle size={17} /><span>Reviewed</span><span className="nav-count">{counts.reviewed}</span></button><button className={filter==='all'&&!overview?'selected':''} onClick={()=>{setFilter('all');setMobileCase(false);setOverview(false)}}><Tray size={17} /><span>All cases</span><span className="nav-count">{counts.all}</span></button></nav>
      <div className="nav-section"><span>Workflows</span><button className={workflow==='issues'?'workflow-selected':''} onClick={()=>changeWorkflow('issues')}><span className="workflow-icon"><Inbox size={13} /></span>{workspace?.demo?'Support queues':'Public issue review'}</button>{!workspace?.demo&&<button className={workflow==='equipment'?'workflow-selected':''} onClick={()=>changeWorkflow('equipment')}><span className="workflow-icon equipment"><GearSix size={13} /></span>Equipment watch<span className="simulation-dot" title="Simulated data" /></button>}</div>
      <div className="nav-bottom"><div className="demo-note"><span className="status-dot" />Local demonstration</div><div className="nav-user"><span className="user-avatar">H</span><div><strong>Human reviewer</strong><span>Decisions saved locally</span></div></div></div>
    </aside>
    <section className="case-list" aria-label="Cases"><header><div>{navCollapsed&&<Button aria-label="Expand navigation" onClick={()=>setNavCollapsed(false)}><SidebarSimple size={17}/></Button>}<h2>{filter==='open'?'Needs review':filter==='reviewed'?'Reviewed':'All cases'}</h2><span className="list-total">{visible.length}</span></div><Button aria-label="Refresh workspace" onClick={()=>setRefresh(v=>v+1)}><Plus size={17}/></Button></header>
      <div className="list-filter"><div className="search-field"><MagnifyingGlass size={15}/><label className="sr-only" htmlFor="case-search">Search cases</label><input id="case-search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search cases"/></div><span title="Oldest first"><Funnel size={14}/></span></div>
      <div className="mobile-controls">{workspace?.demo?<Button onClick={()=>{setOverview(true);setMobileCase(true)}}>Workflow demo</Button>:<select aria-label="Workflow" value={workflow} onChange={e=>changeWorkflow(e.target.value as 'issues'|'equipment')}><option value="issues">Public issue review</option><option value="equipment">Equipment watch · Simulated</option></select>}<select aria-label="Review status" value={filter} onChange={e=>{setFilter(e.target.value);setMobileCase(false)}}><option value="open">Needs review</option><option value="reviewed">Reviewed</option><option value="all">All cases</option></select></div>
      <div className="list-caption">{workspace?.demo?'Synthetic support queues':workflow==='issues'?'Archived public issues':'Simulated equipment events'}<span>Oldest first</span></div>
      <div className="case-list-scroll">{!workspace&&!error&&<div role="status" className="queue-message">Loading cases…</div>}{error&&<div role="alert" className="queue-message">{error}<Button variant="outline" onClick={()=>setRefresh(v=>v+1)}>Retry</Button></div>}{workspace&&!visible.length&&<div className="queue-message"><Inbox size={23}/><strong>No cases here</strong><p>{query?'Try a different search.':'Choose another review status or workflow.'}</p></div>}{visible.map(item=><button key={item.id} className={`case-row ${selected?.id===item.id&&!overview?'active':''}`} onClick={()=>{setSelectedId(item.id);setMobileCase(true);setOverview(false)}} aria-current={selected?.id===item.id&&!overview?'true':undefined}><div className="row-meta"><span className="row-source"><span className={`row-dot ${item.review?'complete':''}`}/>{item.id}</span><span>{new Date(item.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',timeZone:'UTC'})}</span></div><strong>{item.title}</strong><p>{item.summary}</p><span className="row-badge">{item.review?'Reviewed':item.simulated?'Simulation':'Public source'}</span></button>)}</div>
      <footer><span className="status-dot"/>{workspace?.demo?`Background evidence · ${workspace.demo.status}`:'Offline evidence · No model calls'}</footer>
    </section>
    {overview&&workspace?.demo?<DemoOverview demo={workspace.demo} onClose={()=>{setOverview(false);setMobileCase(false)}}/>:selected?<CaseReader key={selected.id} item={selected} unavailable={workspace?.demo?.status==='unavailable'||Boolean(error)} onSaved={updateCase} onRefresh={()=>setRefresh(v=>v+1)} onBack={()=>setMobileCase(false)}/>:<main className="reader empty-reader"><Inbox size={32}/><h1>{workspace?'Your review queue is clear':'Decision workspace'}</h1><p>{workspace?'Choose a workflow or review status to see cases.':'Findings, evidence, and human decisions in one place.'}</p></main>}
  </div>
}
