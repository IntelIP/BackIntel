import React from 'react';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {afterEach,describe,it,expect,vi} from 'vitest';
import {CoordinationPanel,type Coordination} from '../src/CoordinationPanel';

afterEach(cleanup);
const usage={provider_calls:2,provider_usd:0.02,reserved_usd:0,charge_status:'measured'};
const value:Coordination={run_id:'run',goal_version:1,source_version:'source-v1',status:'partial',
  policy:{request_id:'stable-request',max_model_calls:6,max_spend_usd:0.25},usage,
  agents:[{role:'checking',responsibility:'Check the finding',status:'rejected',input_version:'inputs-v1',
    error:'Source and finding disagree',contribution:{decision:'review_required'},usage}]};

describe('specialist coordination',()=>{
  it('resumes the same request and allowance while showing the rejected contribution',()=>{
    const start=vi.fn();
    render(<CoordinationPanel value={value} allowed busy={false} budget={0.5} onStart={start}/>);
    expect(screen.getByRole('alert').textContent).toContain('Source and finding disagree');
    fireEvent.click(screen.getByRole('button',{name:'Resume specialist work'}));
    expect(start).toHaveBeenCalledWith('stable-request',0.25);
    expect(screen.getByText('Inspect contribution and evidence')).toBeTruthy();
  });
  it('prevents starting without an allowance or during accepted work',()=>{
    const view=render(<CoordinationPanel allowed busy={false} budget={0} onStart={vi.fn()}/>);
    expect(screen.getByRole('button').hasAttribute('disabled')).toBe(true);
    view.rerender(<CoordinationPanel value={{...value,status:'running'}} allowed busy={false} budget={0.5} onStart={vi.fn()}/>);
    expect(screen.getByRole('button',{name:'Specialists are working'}).hasAttribute('disabled')).toBe(true);
  });
});
