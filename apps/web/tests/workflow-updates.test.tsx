import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,it} from 'vitest';
import {WorkflowUpdateStatus,type WorkflowUpdateState} from '../src/WorkflowUpdateStatus';

afterEach(cleanup);
it('keeps the accepted answer and source time beside a failed update and its decision',()=>{
  const value:WorkflowUpdateState={state:'review_required',question:'What is net invoice value?',policy:'Preserve values and meanings.',
    accepted:{run_id:'accepted',summary:'Accepted net invoice value: GBP 100.',source_time:'2026-10-15T00:00:00Z',workflow_version:'checked-version'},
    latest:{run_id:'failed',status:'failed',started_at:'2026-10-16T00:00:00Z',error:'Required quantity field is missing.',
      report:{source_time:'2026-10-16T00:00:00Z',decision:'Restore the quantity field or approve new meanings.'}}};
  render(<WorkflowUpdateStatus value={value}/>);
  expect(screen.getByText('Accepted net invoice value: GBP 100.')).toBeVisible();
  expect(screen.getByText(/Source observed:/)).toBeVisible();
  expect(screen.getByText(/Update source observed:/)).toBeVisible();
  expect(screen.getByText(/Update status: review required/)).toBeVisible();
  expect(screen.getByText(/Restore the quantity field/)).toBeVisible();
  expect(screen.queryByText(/checked snapshot/)).not.toBeInTheDocument();
});
