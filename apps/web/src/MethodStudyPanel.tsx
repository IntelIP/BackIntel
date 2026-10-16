import {useState} from 'react';

export const FORECAST_QUESTION = 'Forecast four complete weeks of total net invoice value in GBP across all countries, including cancellations.';
type Score = {mean_absolute_weekly_error:string; four_week_total_error:string};
type Candidate = {name:string; code:string; rationale:string; status:string; reason:string; validation?:Score};
type Study = {
  promoted:boolean;
  contract:{policy:{question:string}; splits:Record<string,{weeks:number;first:string;last:string}>};
  selection:{baseline:Score; candidates:Candidate[]; selected:{name:string;kind:string}};
  final_test:{status:string; baseline:Score; selected?:Score};
  uncertainty:string[];
};
type Forecast = {weeks:{start:string;net_value:string}[]; currency:string; uncertainty:string; promoted:boolean};
export type MethodResult = {method_study?:Study; forecast?:Forecast; mode?:string; elapsed_seconds?:number};
type StudyRun = {id:string; status:string; error?:string; body:{operation:string}; result?:MethodResult & {usage:{provider_usd:number;charge_status:string}}};
const gbp = (value:string) => new Intl.NumberFormat(undefined,{style:'currency',currency:'GBP'}).format(Number(value));

export function MethodStudyPanel({runs,canStart,disabled,onStart,onSave,onInspect}:{
  runs:StudyRun[]; canStart:boolean; disabled:boolean;
  onStart:(policy:{question:string;max_spend_usd:number})=>void;
  onSave:(identity:string)=>void; onInspect:(identity:string)=>void;
}) {
  const [allowance,setAllowance]=useState('0');
  const studyRun=runs.find(run=>run.body.operation==='method');
  const study=studyRun?.result?.method_study;
  const forecastRun=runs.find(run=>run.status==='succeeded'&&run.result?.forecast);
  const forecast=forecastRun?.result?.forecast;
  return <section aria-label="Forecast method development">
    <h3>Develop a forecasting method</h3>
    <p>{FORECAST_QUESTION}</p>
    <p>Compare two generated methods with repeating the latest four weeks. Choose the lowest average weekly error on four earlier weeks. Reserve the final four complete weeks for one unseen check. Keep the simple method on a tie.</p>
    <p>Historical evaluation only. Saving or running a forecast does not approve it for operational use.</p>
    {!studyRun&&canStart&&<form onSubmit={event=>{event.preventDefault();onStart({question:FORECAST_QUESTION,max_spend_usd:Number(allowance)});}}>
      <label htmlFor="method-allowance">Spending allowance for one model call (USD)</label>
      <input id="method-allowance" type="number" min="0" max="0.5" step="0.01" required value={allowance} onChange={event=>setAllowance(event.target.value)}/>
      <p>Default allowance is zero. Only earlier weekly totals and the agreed policy go to the model.</p>
      <button disabled={disabled||Number(allowance)<=0||Number(allowance)>0.5}>Develop and compare methods</button>
    </form>}
    {studyRun&&<p>Method study: {studyRun.status}. {studyRun.error}</p>}
    {study&&studyRun&&<>
      <p>{studyRun.result?.mode==='fixture'?'Simulated model response.':'Model-generated methods.'} Selected method: <strong>{study.selection.selected.name}</strong>. Predictor is not promoted.</p>
      <details><summary>Protected evaluation periods</summary>{Object.entries(study.contract.splits).map(([name,period])=><p key={name}>{name.replaceAll('_',' ')}: {period.weeks} weeks, starting {period.first} through {period.last}.</p>)}</details>
      <div className="table-scroll"><table><caption>Method comparison on earlier validation weeks</caption><thead><tr><th>Method</th><th>Average weekly error</th><th>Decision</th></tr></thead><tbody>
        <tr><td>Repeat the latest four weeks</td><td>{gbp(study.selection.baseline.mean_absolute_weekly_error)}</td><td>{study.selection.selected.kind==='baseline'?'Selected':'Retained for comparison'}</td></tr>
        {study.selection.candidates.map((candidate,index)=><tr key={index}><td>{candidate.name}</td><td>{candidate.validation?gbp(candidate.validation.mean_absolute_weekly_error):'Unavailable'}</td><td>{candidate.status}: {candidate.reason}</td></tr>)}
      </tbody></table></div>
      <h4>Unseen final four weeks</h4>
      <p>Simple method average weekly error: {gbp(study.final_test.baseline.mean_absolute_weekly_error)}. Selected method: {study.final_test.selected?gbp(study.final_test.selected.mean_absolute_weekly_error):'Execution failed; no replacement was selected'}.</p>
      <p>This result does not change the selection or trigger more model calls.</p>
      {study.uncertainty.map(text=><p className="caveat" key={text}>{text}</p>)}
      <p>Measured inference: ${studyRun.result?.usage.provider_usd} ({studyRun.result?.usage.charge_status}). Execution: {studyRun.result?.elapsed_seconds??'Unavailable'} seconds. Local computing cost is unavailable.</p>
      <details><summary>Generated methods and reasons</summary>{study.selection.candidates.map((candidate,index)=><article key={index}><h4>{candidate.name}</h4><p>{candidate.rationale}</p><pre>{candidate.code}</pre></article>)}</details>
      <button disabled={disabled} onClick={()=>onInspect(studyRun.id)}>Inspect method evidence</button>
      {canStart&&<button disabled={disabled||study.final_test.status!=='evaluated_once'} onClick={()=>onSave(studyRun.id)}>Save selected forecast workflow</button>}
    </>}
    {forecast&&<section aria-label="Saved forecast result"><h3>Saved forecast result</h3>
      <p>{forecastRun?.result?.mode==='fixture'?'Uses a simulated method proposal. ':''}Evaluation use only. Predictor is not promoted.</p>
      <div className="table-scroll"><table><caption>Four future weeks from the historical source</caption><thead><tr><th>Week starting</th><th>Forecast net invoice value</th></tr></thead><tbody>{forecast.weeks.map(week=><tr key={week.start}><td>{week.start}</td><td>{gbp(week.net_value)}</td></tr>)}</tbody></table></div>
      <p>{forecast.uncertainty}</p><p>New inference cost: ${forecastRun?.result?.usage.provider_usd}.</p>
    </section>}
  </section>;
}
