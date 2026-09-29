import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { ApiError, type Case, type Workspace } from './api'
import * as api from './api'

vi.mock('./api', async importOriginal=>({ ...await importOriginal<typeof import('./api')>(), loadWorkspace:vi.fn(), saveDecision:vi.fn() }))

const item:Case={id:'GH-1',workflow:'issues',title:'An issue to review',summary:'Original issue summary',created_at:'2024-02-01T00:00:00Z',source_kind:'GitHub issue',simulated:false,facts:[{label:'Opened',value:'2024-02-01'}],finding:{text:'Check the source',status:'Rule-based suggestion'},prediction:{status:'experimental',explanation:'Did not beat baseline',estimates:{baseline:0.4}},evidence:{text:'<script>unsafe()</script>',url:'https://github.com/example/project/issues/1',sha256:'a'.repeat(64),collected_at:'2024-02-01T00:00:00Z'},review:null,history:[],outcome:null}
const workspace:Workspace={schema:'backintel-decision-workspace/v1',cases:[item,{...item,id:'EQ-1',workflow:'equipment',title:'Equipment example',simulated:true}],source_mode:'retained-public-issue-evidence'}

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
})
