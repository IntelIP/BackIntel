import React from 'react';

type UpdateReport = {source_time?:string;decision?:string;definitions_reused?:string[];reused_stages?:string[];recomputed_stages?:string[];changed_source_pages?:number;unchanged_source_pages?:number;validation?:string;method_check?:{summary?:string};source_changes?:{inserted:number;corrected:number;deleted:number;unchanged:number;value_rows_read:number;metadata_rows_scanned:number;excluded_rows:number;failed_rows:number;pending_rows:number;full_rereads:{schema:string;table:string;reason:string}[]}};
export type WorkflowUpdateState = {state:string;question:string;policy:string;
  accepted:{run_id:string;summary:string;source_time:string|null;workflow_version:string|null}|null;
  latest:{run_id:string;status:string;started_at:string;error:string|null;report:UpdateReport|null}|null};

export function WorkflowUpdateStatus({value}:{value?:WorkflowUpdateState}) {
  if(!value)return null;
  const report=value.latest?.report;
  const changes=report?.source_changes;
  return <section aria-label="Answer updates"><h3>Keep the last useful answer</h3>
    <p>{value.question}</p><p>Update status: {value.state.replaceAll('_',' ')}.</p>
    {value.accepted?<div><h4>Last accepted answer</h4><p>{value.accepted.summary}</p>
      <p>Source observed: {value.accepted.source_time?new Date(value.accepted.source_time).toLocaleString():'Not recorded'}.</p>
      {value.accepted.workflow_version&&<p>Checked workflow version: {value.accepted.workflow_version.slice(0,12)}.</p>}
    </div>:<p>No checked answer has been accepted for this question yet.</p>}
    {value.latest&&<div><h4>Latest update</h4><p>Run status: {value.latest.status}.</p>
      {report?.source_time&&<p>Update source observed: {new Date(report.source_time).toLocaleString()}.</p>}
      {value.latest.error&&<p role="alert">{value.latest.error}</p>}
      {report?.decision&&<p><strong>Decision needed:</strong> {report.decision}</p>}
      {report?.validation&&<p>{report.validation}</p>}
      {report?.definitions_reused&&<p>Reused definitions: {report.definitions_reused.join(', ')}.</p>}
      {!!report?.reused_stages?.length&&<p>Reused completed steps: {report.reused_stages.join(', ')}.</p>}
      {!!report?.recomputed_stages?.length&&<p>Recomputed steps: {report.recomputed_stages.join(', ')}.</p>}
      {report?.changed_source_pages!==undefined&&<p>Source pages changed: {report.changed_source_pages}. Unchanged: {report.unchanged_source_pages}.</p>}
      {report?.method_check?.summary&&<p>{report.method_check.summary}</p>}
      {changes&&<div><h4>Source changes</h4>
        <p>Added: {changes.inserted}. Corrected: {changes.corrected}. Deleted from current totals: {changes.deleted}. Unchanged: {changes.unchanged}.</p>
        <p>Read {changes.value_rows_read} record values and scanned {changes.metadata_rows_scanned} record fingerprints. Original values and deletion history remain available.</p>
        <p>Excluded: {changes.excluded_rows}. Failed: {changes.failed_rows}. Pending: {changes.pending_rows}.</p>
        {changes.full_rereads.map(item=><p key={item.schema+'.'+item.table}>Full reread of {item.schema}.{item.table}: {item.reason}</p>)}
      </div>}
    </div>}
    <details><summary>Repair limits</summary><p>{value.policy}</p></details>
  </section>;
}
