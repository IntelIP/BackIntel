import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { ApiError, type Case, type Demo, type Workspace } from './api'
import * as api from './api'

vi.mock('./api', async importOriginal=>({ ...await importOriginal<typeof import('./api')>(), loadWorkspace:vi.fn(), saveDecision:vi.fn() }))

const item:Case={id:'GH-1',workflow:'issues',title:'An issue to review',summary:'Original issue summary',created_at:'2024-02-01T00:00:00Z',source_kind:'GitHub issue',simulated:false,facts:[{label:'Opened',value:'2024-02-01'}],finding:{text:'Check the source',status:'Rule-based suggestion'},prediction:{status:'experimental',explanation:'Did not beat baseline',estimates:{baseline:0.4}},evidence:{text:'<script>unsafe()</script>',url:'https://github.com/example/project/issues/1',sha256:'a'.repeat(64),collected_at:'2024-02-01T00:00:00Z'},review:null,history:[],outcome:null}
const workspace:Workspace={schema:'backintel-decision-workspace/v1',cases:[item,{...item,id:'EQ-1',workflow:'equipment',title:'Equipment example',simulated:true}],source_mode:'retained-public-issue-evidence'}
const demo:Demo={title:'Support workflow demonstration',persona:'Support lead',problem:'Prepare reports for review',today:['Read reports manually'],status:'prepared',jev_mode:'Jev has not run',demo_id:'business-test',captured_at:'2026-09-30T12:00:00Z',actual_provider_calls:0,stages:[{id:'interpret',title:'Interpret report text',technology:'Jev',count:0,status:'pending',explanation:'Answer a fixed question'}],comparisons:[],value:{assumptions:{cases_per_week:600,manual_minutes_per_case:8,assisted_minutes_per_case:3,labour_usd_per_hour:40},capacity_hours_per_week:50,capacity_value_usd_per_week:2000,provider_usd:0,compute_usd:null,net_benefit_usd:null,explanation:'Capacity value is an assumption, not measured savings.'},stack:[{name:'LangGraph',role:'Run bounded steps'}],boundaries:['Synthetic inputs and future outcomes']}

describe('review journey',()=>{
  beforeEach(()=>{vi.mocked(api.loadWorkspace).mockResolvedValue(structuredClone(workspace)); vi.mocked(api.saveDecision).mockReset()})
  it('keeps later knowledge hidden and persists a reasoned human decision',async()=>{
    vi.mocked(api.saveDecision).mockResolvedValue({...item,review:{decision:'follow_up',reason:'Ask owner',revision:1,recorded_at:'2026-09-29T12:00:00Z'},outcome:{text:'Later archived outcome',available_at:'2024-02-08T00:00:00Z'}})
    render(<App/>);await screen.findByRole('heading',{name:'An issue to review'})
    expect(screen.getByRole('button',{name:'Save decision'})).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Reason and next step'),{target:{value:'Ask owner'}})
    fireEvent.click(screen.getByRole('button',{name:'Save decision'}))
    await waitFor(()=>expect(api.saveDecision).toHaveBeenCalledWith('GH-1','follow_up','Ask owner',0,item.evidence.sha256))
    await screen.findByRole('button',{name:'Reviewed'})
    fireEvent.mouseDown(screen.getByRole('tab',{name:'Later outcome'}),{button:0,ctrlKey:false})
    expect(await screen.findByText('Later archived outcome')).toBeInTheDocument()
  })
  it('shows conflict and preserves unsaved reason',async()=>{
    vi.mocked(api.saveDecision).mockRejectedValue(new ApiError(409,'conflict'))
    render(<App/>);await screen.findByRole('heading',{name:'An issue to review'})
    fireEvent.change(screen.getByLabelText('Reason and next step'),{target:{value:'Keep my note'}})
    fireEvent.click(screen.getByRole('button',{name:'Save decision'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('changed in another view')
    expect(screen.getByLabelText('Reason and next step')).toHaveValue('Keep my note')
  })
  it('renders source as text and supports empty search and second workflow',async()=>{
    render(<App/>);await screen.findByRole('heading',{name:'An issue to review'})
    fireEvent.click(screen.getByRole('button',{name:'Open evidence'}))
    expect(screen.getByText('<script>unsafe()</script>')).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    fireEvent.click(screen.getByRole('button',{name:'Close evidence'}))
    fireEvent.change(screen.getByLabelText('Search cases'),{target:{value:'missing-case'}})
    expect(screen.getByText('No cases here')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Equipment watch'}))
    expect(await screen.findByRole('heading',{name:'Equipment example'})).toBeInTheDocument()
  })
  it('supports retry after service failure',async()=>{
    vi.mocked(api.loadWorkspace).mockRejectedValueOnce(new Error('offline'))
    render(<App/>);await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button',{name:'Retry'}))
    await screen.findByRole('heading',{name:'An issue to review'})
  })
  it('does not issue duplicate writes while save is pending',async()=>{
    let done!: (value:Case)=>void
    vi.mocked(api.saveDecision).mockReturnValue(new Promise(resolve=>{done=resolve}))
    render(<App/>);await screen.findByRole('heading',{name:'An issue to review'})
    fireEvent.change(screen.getByLabelText('Reason and next step'),{target:{value:'Owner check'}})
    fireEvent.click(screen.getByRole('button',{name:'Save decision'}))
    expect(screen.getByRole('button',{name:'Saving…'})).toBeDisabled()
    expect(api.saveDecision).toHaveBeenCalledTimes(1)
    await act(async()=>done({...item,review:{decision:'follow_up',reason:'Owner check',revision:1,recorded_at:'2026-09-29T12:00:00Z'}}))
  })
  it('keeps the native rehearsal separate from pending live interpretation',async()=>{
    vi.mocked(api.loadWorkspace).mockResolvedValue({...workspace,demo:{...demo,workflow_rehearsal:{
      status:'completed with simulated intelligence',scope_boundary:'This separate rehearsal does not complete the live Jev journey.',
      technology:'Aegra native scheduling',pending_triggers:0,replay_unchanged:true,evidence_records:737,
      scenarios:[{name:'Support queues',completed_jobs:14,simulated_predictions:22,delivery_records:5,simulated_model_updates:1}],
    }}})
    render(<App/>)
    await screen.findByRole('heading',{name:'Scheduled workflow rehearsal'})
    expect(screen.getByText('Jev has not run')).toBeInTheDocument()
    expect(screen.getByText('Awaiting execution')).toBeInTheDocument()
    expect(screen.getByText('completed with simulated intelligence')).toBeInTheDocument()
    expect(screen.getByText(/Replay kept all 737 evidence records unchanged/)).toBeInTheDocument()
    expect(screen.getAllByText('Not run')).toHaveLength(5)
  })
  it('shows assumptions and pending execution without claiming financial returns',async()=>{
    vi.mocked(api.loadWorkspace).mockResolvedValue({...workspace,demo})
    render(<App/>);await screen.findByRole('heading',{name:demo.title})
    expect(screen.getByText('Jev has not run')).toBeInTheDocument()
    expect(screen.getByText('Awaiting execution')).toBeInTheDocument()
    expect(screen.getByText('$2,000.00')).toBeInTheDocument()
    expect(screen.getAllByText('Unknown')).toHaveLength(2)
    expect(screen.getAllByText('Not measured')).toHaveLength(2)
    expect(screen.getAllByText('Not run')).toHaveLength(5)
  })
  it('keeps a partial live run and its unknown total distinct from recorded charges',async()=>{
    vi.mocked(api.loadWorkspace).mockResolvedValue({...workspace,demo:{...demo,status:'blocked',jev_mode:'Actual response retained',actual_provider_calls:1,error:'The live attempt stopped after 2 request attempts.',live_attempt:{request_attempts:2,unknown_request_cost_count:1,total_provider_charge_usd:null},value:{...demo.value,provider_usd:0.000013608}}})
    render(<App/>);await screen.findByRole('heading',{name:demo.title})
    expect(screen.getByText('$0.000013608')).toBeInTheDocument()
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument()
    expect(screen.getAllByText('Unknown')).toHaveLength(3)
    expect(screen.getByText('Total retained attempt charge').nextElementSibling).toHaveTextContent('Unknown')
    expect(screen.getByText('Not completed')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('stopped after 2 request attempts')
  })
  it('preserves a draft but requires explicit source refresh before saving',async()=>{
    render(<App/>);await screen.findByRole('heading',{name:item.title})
    fireEvent.change(screen.getByLabelText('Reason and next step'),{target:{value:'Preserve this note'}})
    const changed={...item,evidence:{...item.evidence,sha256:'b'.repeat(64)}}
    vi.mocked(api.loadWorkspace).mockResolvedValue({...workspace,cases:[changed]})
    fireEvent.click(screen.getByRole('button',{name:'Refresh workspace'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('New source information arrived')
    expect(screen.getByLabelText('Reason and next step')).toHaveValue('Preserve this note')
    expect(screen.getByRole('button',{name:'Save decision'})).toBeDisabled()
    fireEvent.click(screen.getByRole('button',{name:'Refresh case'}))
    await waitFor(()=>expect(screen.getByRole('button',{name:'Save decision'})).toBeEnabled())
    vi.mocked(api.saveDecision).mockResolvedValue({...changed,review:{decision:'follow_up',reason:'Preserve this note',revision:1,recorded_at:demo.captured_at}})
    fireEvent.click(screen.getByRole('button',{name:'Save decision'}))
    await waitFor(()=>expect(api.saveDecision).toHaveBeenCalledWith(item.id,'follow_up','Preserve this note',0,changed.evidence.sha256))
  })
  it('disables saving against an unavailable background snapshot',async()=>{
    vi.mocked(api.loadWorkspace).mockResolvedValue({...workspace,demo:{...demo,status:'unavailable'}})
    render(<App/>);await screen.findByRole('heading',{name:demo.title})
    fireEvent.click(screen.getByRole('button',{name:/^Needs review/}))
    fireEvent.change(screen.getByLabelText('Reason and next step'),{target:{value:'Check evidence'}})
    expect(screen.getByRole('button',{name:'Save decision'})).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('Current evidence is unavailable')
  })
})
