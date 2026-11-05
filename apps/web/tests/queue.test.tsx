import React from 'react';
import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {QueuePanel} from '../src/QueuePanel';

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('shows permitted waiting work and the current user budget without inventing computer costs',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json({
    shared_capacity:{active:2,waiting:2,active_limit:2},
    your_usage:{provider_usd:0,reserved_usd:0.04,budget_usd:0.05,unresolved_charges:1},
    jobs:[{id:'run',goal_id:'goal',status:'queued',state:'queued',waiting_seconds:8.2}],
  })));
  render(<QueuePanel token="fixture" goals={[{id:'goal',body:{question:'Our retail question'}}]}/>);
  expect(await screen.findByText(/Our retail question.*waited 8.2 seconds/)).toBeTruthy();
  expect(screen.getByText(/Shared service: 2 running, 2 waiting/)).toBeTruthy();
  expect(screen.getByText(/US\$0.0400 reserved.*US\$0.05 user limit/)).toBeTruthy();
  expect(screen.getByText(/Local computer costs have not been measured/)).toBeTruthy();
});
it('handles an unavailable queue without breaking the workspace',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(Response.json([])));
  render(<QueuePanel token="fixture" goals={[]}/>);
  expect(await screen.findByRole('status')).toHaveTextContent('Work status is unavailable.');
});
