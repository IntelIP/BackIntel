import React from 'react';

export type Objective = {
  source_ref: string; expected_source_sha256: string|null; allowed_schemas: string[];
  allowed_actions: ['read']; metric: string; population: string; period: string;
  target: string|null; expected_checks: string[]; freshness: string;
  output_destination: 'local'; limits: {max_source_bytes: number; timeout_seconds: number};
  open_questions: string[];
};
export const emptyObjective: Objective = {
  source_ref: '', expected_source_sha256: null, allowed_schemas: [], allowed_actions: ['read'],
  metric: '', population: '', period: '', target: null, expected_checks: [], freshness: '',
  output_destination: 'local', limits: {max_source_bytes: 104857600, timeout_seconds: 900}, open_questions: [],
};

export function ObjectiveForm({question, objective, busy, onSave}: {
  question: string; objective: Objective; busy: boolean;
  onSave: (value: {question: string; objective: Objective}) => void;
}) {
  return <form onSubmit={event=>{
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const value = (key: string) => String(data.get(key) ?? '').trim();
    const lines = (key: string) => value(key).split('\n').map(s=>s.trim()).filter(Boolean);
    onSave({question: value('question'), objective: {
      ...objective, source_ref: value('source_ref'), expected_source_sha256: value('hash') || null,
      allowed_schemas: value('schemas').split(',').map(s=>s.trim()).filter(Boolean),
      metric: value('metric'), population: value('population'), period: value('period'),
      target: value('target') || null, expected_checks: lines('checks'), freshness: value('freshness'),
      open_questions: lines('questions'), limits: {max_source_bytes: Number(value('bytes')), timeout_seconds: Number(value('seconds'))},
    }});
  }}>
    <label>Business question<textarea name="question" defaultValue={question} maxLength={2000} required/></label>
    <label>Saved connection name<input name="source_ref" defaultValue={objective.source_ref} pattern="[a-z][a-z0-9_-]{0,63}" required/></label>
    <p>Use a saved connection name. Do not enter a password or connection URL. Access is read-only; reports stay local.</p>
    <label>Permitted database schemas, separated by commas<input name="schemas" defaultValue={objective.allowed_schemas.join(', ')} required/></label>
    <label>Source file SHA-256, if known<input name="hash" defaultValue={objective.expected_source_sha256 ?? ''} pattern="[0-9a-f]{64}"/></label>
    <label>Measure and units<textarea name="metric" defaultValue={objective.metric} maxLength={2000} required/></label>
    <label>Records to include<textarea name="population" defaultValue={objective.population} maxLength={2000} required/></label>
    <label>Time period<textarea name="period" defaultValue={objective.period} maxLength={2000} required/></label>
    <label>Business target, if agreed<input name="target" defaultValue={objective.target ?? ''} maxLength={2000}/></label>
    <label>Checks required, one per line<textarea name="checks" defaultValue={objective.expected_checks.join('\n')} required/></label>
    <label>How current must the answer be?<textarea name="freshness" defaultValue={objective.freshness} maxLength={2000} required/></label>
    <label>Unresolved questions, one per line<textarea name="questions" defaultValue={objective.open_questions.join('\n')}/></label>
    <label>Maximum source size in bytes<input name="bytes" type="number" min="1" max="104857600" defaultValue={objective.limits.max_source_bytes} required/></label>
    <label>Maximum execution time in seconds<input name="seconds" type="number" min="1" max="900" defaultValue={objective.limits.timeout_seconds} required/></label>
    <button disabled={busy}>Save business objective</button>
  </form>;
}
