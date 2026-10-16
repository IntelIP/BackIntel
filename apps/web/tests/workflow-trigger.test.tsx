import {cleanup,render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import {WorkflowTriggerPanel} from '../src/WorkflowTriggerPanel';

afterEach(cleanup);

it('shows the owner schedule, denied attempts and actual run state, and can pause it',async()=>{
  const trigger={id:'trigger',state:'active',workflow_version:'version',next_due:'2026-10-20T12:00:00Z',expires_at:'2026-10-20T12:15:00Z',accepted_count:1,
    body:{event_source:'retail.collection.completed',timezone:'America/New_York',max_runs:2,max_spend_usd:0},
    attempts:[{sequence:1,created_at:'2026-10-20T12:00:00Z',occurrence:'event:one',status:'accepted',reason:'Saved workflow admitted',run_id:'run-one',run_status:'succeeded'},
      {sequence:2,created_at:'2026-10-20T12:01:00Z',occurrence:'event:two',status:'denied',reason:'Source access expired',run_id:null,run_status:null}]};
  const api=vi.fn().mockImplementation(async(_path:string,method?:string)=>method==='PATCH'?{...trigger,state:'paused'}:[trigger]);
  render(<WorkflowTriggerPanel goalId="goal" versions={[]} api={api} canCreate={false}/>);
  expect(await screen.findByText('retail.collection.completed')).toBeInTheDocument();
  expect(screen.getByText(/Accepted starts: 1 of 2/)).toBeInTheDocument();
  expect(screen.getByText(/Work succeeded/)).toBeInTheDocument();
  expect(screen.getByText(/Source access expired/)).toBeInTheDocument();
  expect(screen.getByText(/America\/New_York/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Pause trigger'}));
  expect(api).toHaveBeenCalledWith('/triggers/trigger','PATCH',{state:'paused'});
  expect(screen.queryByRole('button',{name:'Create bounded trigger'})).not.toBeInTheDocument();
});
