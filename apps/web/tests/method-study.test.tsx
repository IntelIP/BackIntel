import React from 'react';
import {render,screen,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import {MethodStudyPanel,FORECAST_QUESTION} from '../src/MethodStudyPanel';

afterEach(cleanup);
it('requires a positive allowance and submits the fixed evaluation scope',async()=>{
  const start=vi.fn();
  render(<MethodStudyPanel runs={[]} canStart disabled={false} onStart={start} onSave={vi.fn()} onInspect={vi.fn()}/>);
  const button=screen.getByRole('button',{name:'Develop and compare methods'});
  expect(button).toBeDisabled();
  const input=screen.getByRole('spinbutton',{name:/Spending allowance/});
  await userEvent.clear(input);await userEvent.type(input,'0.25');await userEvent.click(button);
  expect(start).toHaveBeenCalledWith({question:FORECAST_QUESTION,max_spend_usd:0.25});
});

it('shows rejected candidates, final error and simulated unpromoted results',async()=>{
  const save=vi.fn();const score={mean_absolute_weekly_error:'12',four_week_total_error:'48'};
  const runs=[{id:'study',status:'succeeded',body:{operation:'method'},result:{mode:'fixture',elapsed_seconds:2,usage:{provider_usd:0,charge_status:'measured'},method_study:{
    promoted:false,contract:{policy:{question:FORECAST_QUESTION},splits:{training:{weeks:44,first:'2010-12-06',last:'2011-10-03'}}},
    selection:{baseline:score,selected:{name:'Repeat the latest four weeks',kind:'baseline'},candidates:[{name:'Unhelpful forecast',code:'def forecast(history, horizon): return [0]*horizon',rationale:'Simulation for checking the flow.',status:'rejected',reason:'Worse validation error.',validation:score}]},
    final_test:{status:'evaluated_once',baseline:score,selected:score},uncertainty:['Only one final period; future reliability is unknown.']
  }}}];
  render(<MethodStudyPanel runs={runs} canStart disabled={false} onStart={vi.fn()} onSave={save} onInspect={vi.fn()}/>);
  expect(screen.getByText(/Simulated model response/)).toBeInTheDocument();
  expect(screen.getByText(/Worse validation error/)).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Unseen final four weeks'})).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:'Develop and compare methods'})).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button',{name:'Save selected forecast workflow'}));
  expect(save).toHaveBeenCalledWith('study');
});
