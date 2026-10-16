import React from 'react';
import {act, render, screen, waitFor, within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach, afterEach, describe, expect, it, vi} from 'vitest';
import App from '../src/main';

const standingQuestion = 'Which departments have weaker recommendations?';
const answer = 'Standing answer: group A has an observed mean of 0.5.';
let role: string;
let source: Record<string, any>;
let goal: Record<string, any>;
let runs: Record<string, any>[];
let savedFinding: Record<string, any>;
let requests: {path: string; method: string; body: any}[];
let failRun: boolean;
let releaseRun: (() => void) | undefined;
let delayRun: boolean;

beforeEach(() => {
  sessionStorage.clear();
  history.replaceState(null, '', '/');
  role = 'manager'; failRun = false; delayRun = false; releaseRun = undefined; requests = [];
  source = {id: 'commerce', domain: 'commerce', latest_snapshot: 'snapshot-1', body: {
    name: 'Fixture clothing reviews', question: standingQuestion, caveat: 'Synthetic component fixture.',
    terms_acknowledged: true, license: 'Fixture', kaggle: 'fixture/fixture',
  }};
  goal = {id: 'goal-1', domain: 'commerce', version: 1, confirmed: true, paused: false,
    freshness: 'current', last_success: 'run-1', active_model: null,
    body: {question: standingQuestion, definitions: {group: 'department'}, notification_delta: 0.1, budget_usd: 1}};
  runs = [{id: 'run-1', goal_id: 'goal-1', status: 'succeeded', created_at: '2024-01-01T00:00:00Z', snapshot_id: 'snapshot-1',
    body: {operation: 'analysis', question: standingQuestion}, result: {
      summary: answer, findings: [{claim: 'Observed group A mean is 0.5.', kind: 'fact', evidence_ids: ['calculation-1']}],
      tables: [{title: 'summarize', evidence_id: 'calculation-1', rows: [{group: 'A', count: 4, labeled: 4, mean: 0.5}]}],
      usage: {provider_usd: 0, charge_status: 'reconciled'}, limitations: ['Synthetic component fixture.'],
    }}];
  savedFinding = structuredClone(runs[0]);
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = new URL(String(input), location.origin).pathname;
    const method = init?.method || 'GET';
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    requests.push({path, method, body});
    let value: unknown;
    if (path === '/api/v1/me') value = {id: role, role, domains: ['commerce'], budget: {suite_usd: 10}};
    else if (path === '/api/v1/sources') value = [source];
    else if (path === '/api/v1/goals' && method === 'GET') value = [goal];
    else if (path === '/api/v1/notifications' || path.endsWith('/models') || path.endsWith('/reviews')) value = [];
    else if (path === '/api/v1/runs') value = runs;
    else if (path === '/api/v1/goals/goal-1/findings') value = savedFinding;
    else if (path === '/api/v1/sources/commerce/terms') {
      source = {...source, body: {...source.body, terms_acknowledged: body.acknowledged}}; value = source;
    } else if (path === '/api/v1/goals/goal-1' && method === 'PATCH') {
      goal = {...goal, version: goal.version + 1, confirmed: false, body: {...goal.body, budget_usd: body.budget_usd}}; value = goal;
    } else if (path === '/api/v1/goals/goal-1/runs') {
      if (delayRun) await new Promise<void>(resolve => {releaseRun = resolve;});
      if (failRun) return Response.json({detail: 'Provider charge unresolved; standing answer preserved.'}, {status: 409});
      value = runs[0];
    } else if (path === '/api/v1/evidence/calculation-1') value = {snapshot: 'snapshot-1', count: 4, mean: 0.5};
    else if (path === '/api/v1/runs/run-1/workflow' && method === 'POST') {
      goal.workflows = [{version:'workflow-fixture-1',created_at:1,mode:'fixture',goal_version:1,question:standingQuestion}];
      value = {format:'backintel.workflow/v1',version:'workflow-fixture-1',body:{question:standingQuestion}};
    } else if (path === '/api/v1/workflows/workflow-fixture-1') value = {status:'ready',issues:[],package:{version:'workflow-fixture-1'}};
    else if (path === '/api/v1/workflows/workflow-fixture-1/export') value = {version:'workflow-fixture-1',body:{connection:{secret_ref:'SOURCE_DSN'}}};
    else if (path === '/api/v1/workflows/workflow-fixture-1/runs' && method === 'POST') value = runs[0];
    else throw new Error('Unexpected component fixture request: ' + method + ' ' + path);
    return Response.json(value);
  }));
});

afterEach(() => {vi.unstubAllGlobals();});

async function openWorkspace() {
  sessionStorage.setItem('backintel-access', 'component-fixture-access');
  const user = userEvent.setup();
  render(<App/>);
  await screen.findByRole('heading', {name: 'Fixture clothing reviews'});
  await user.click(within(screen.getByRole('navigation', {name: 'Saved goals'})).getByRole('button'));
  await screen.findByText(answer);
  return user;
}

describe('analysis workspace user controls', () => {
  it('keeps a connected objective at zero spend and shows its saved proposal as a proposal', async () => {
    goal.body.budget_usd = 0;
    goal.body.objective = {source_ref: 'online-retail-postgres', expected_source_sha256: null,
      allowed_schemas: ['retail_raw'], allowed_actions: ['read'], metric: 'Signed invoice value in GBP',
      population: 'All invoice lines', period: 'Recorded historical period', target: null,
      expected_checks: ['Preserve cancellations'], freshness: 'Historical snapshot', output_destination: 'local',
      limits: {max_source_bytes: 104857600, timeout_seconds: 900}, open_questions: ['Timezone unknown']};
    goal.source_access = true;
    goal.interpretation = {summary:'Inspect proposed meanings.',mode:'fixture',interpretation:{tables:[{schema_name:'retail_raw',table_name:'invoices',grain:'One invoice line.',fields:[{name:'InvoiceNo',meaning:'Invoice identifier.',confidence:'proposed',unit:null,limitations:[]}]}],unresolved:['Currency needs confirmation.']}};
    goal.collection = {summary:'All five source rows retained.',coverage:{expected_rows:5,collected_rows:5,pending_rows:0},limitations:['Preparation and analysis have not run.']};
    goal.preparation = {summary:'Prepared five retained rows.',mode:'fixture',coverage:{processed_rows:5,expected_rows:5,pending_rows:0},unresolved_rows:1,repaired:true,limitations:['Meaning checks are still required.']};
    goal.validation = {status:'failed',summary:'An inconsistent currency was refused.',source_rows:5,candidate_rows:5,failure_groups:[{reason:'Mixed or changed units are not accepted'}]};
    goal.discovery = {summary:'Connected to one permitted table.', observed_at:'2026-10-14T00:00:00Z',
      fields:[{schema:'retail_raw',table:'invoices',column:'InvoiceNo',type:'text'}], limitations:['Full-data collection has not run.']};
    goal.plan = {summary: 'Inspect invoices before calculating values.', mode: 'fixture', plan: {
      data_needs: ['Invoice lines'], steps: [{action: 'check', purpose: 'Check cancellations', expected_result: 'Signed values retained'}],
      assumptions: [], open_questions: []}};
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Goals'}));
    expect(screen.getByLabelText('Maximum frontier cost per run (USD)')).toHaveValue(0);
    expect(screen.getByRole('button', {name: 'Generate agent plan'})).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Interpret source fields'})).toBeDisabled();
    expect(screen.getByText('Simulated interpretation. Live field interpretation has not been verified.')).toBeInTheDocument();
    expect(screen.getByText('Currency needs confirmation.')).toBeInTheDocument();
    expect(screen.getByText('Inspect invoices before calculating values.')).toBeInTheDocument();
    expect(screen.getByText('Simulated provider response. This does not prove live agent planning.')).toBeInTheDocument();
    expect(screen.getByText('Timezone unknown', {selector: 'li'})).toBeInTheDocument();
    expect(screen.getByRole('table', {name:'Permitted source fields'})).toHaveTextContent('InvoiceNo');
    expect(screen.getByText('Full-data collection has not run.')).toBeInTheDocument();
    expect(screen.getByText('Collected 5 of 5 rows. Pending: 0.')).toBeInTheDocument();
    expect(screen.getByText('Preparation and analysis have not run.')).toBeInTheDocument();
    expect(screen.getByText('Prepared 5 of 5 rows. Pending: 0.')).toBeInTheDocument();
    expect(screen.getByText('Rows with unresolved conversions: 1.')).toBeInTheDocument();
    expect(screen.getByText('Meaning checks are still required.')).toBeInTheDocument();
    expect(screen.getByText('Meaning check: failed.')).toBeInTheDocument();
    expect(screen.getByText('Mixed or changed units are not accepted')).toBeInTheDocument();
    await user.click(screen.getByRole('button', {name:'Check prepared data'}));
    await waitFor(()=>expect(requests.some(r=>r.body?.operation==='validation')).toBe(true));
    await user.click(screen.getByRole('button', {name:'Prepare source data'}));
    await waitFor(()=>expect(requests.some(r=>r.body?.operation==='preparation')).toBe(true));
    await user.click(screen.getByRole('button', {name:'Collect complete source'}));
    await waitFor(()=>expect(requests.some(r=>r.body?.operation==='collection')).toBe(true));
    await user.click(screen.getByRole('button', {name:'Discover connected data'}));
    await waitFor(()=>expect(requests.some(r=>r.path==='/api/v1/goals/goal-1/runs'&&r.body?.operation==='discovery')).toBe(true));
  });

  it('keeps a newly proposed goal selected when an older refresh finishes later', async () => {
    const original = fetch;
    let created = false;
    let delay = false;
    let release: (() => void) | undefined;
    let poll: (() => void) | undefined;
    const interval = globalThis.setInterval;
    const intervalSpy = vi.spyOn(globalThis, 'setInterval').mockImplementation((callback, ms, ...args) => {
      if (ms === 30000) poll = callback as () => void;
      return interval(callback, ms, ...args);
    });
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === '/api/v1/goals') {
        if (init?.method === 'POST') {created = true; return Response.json(goal);}
        const value = created ? [goal] : [];
        if (delay && !created) await new Promise<void>(resolve => {release = resolve;});
        return Response.json(value);
      }
      return original(input, init);
    }));
    try {
      sessionStorage.setItem('backintel-access', 'component-fixture-access');
      const user = userEvent.setup(); render(<App/>);
      await screen.findByRole('heading', {name:'Fixture clothing reviews'});
      delay = true;
      act(() => {poll!();});
      await waitFor(() => expect(release).toBeTypeOf('function'));
      await user.click(screen.getByRole('button', {name:'Goals', exact:true}));
      await user.click(screen.getByRole('button', {name:'Propose goal', exact:true}));
      await screen.findByRole('heading', {name:'Confirm business meaning'});
      await act(async () => {release!();});
      expect(screen.getByRole('heading', {name:'Confirm business meaning'})).toBeVisible();
    } finally {intervalSpy.mockRestore();}
  });

  it('discards delayed candidates and reviews from a previously selected goal', async () => {
    const original = fetch;
    const other = {...goal, id:'goal-2', last_success:null, body:{...goal.body, question:'Second question'}};
    let release: (() => void) | undefined;
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path==='/api/v1/goals') return Response.json([goal,other]);
      if (path==='/api/v1/goals/goal-1/models') {
        await new Promise<void>(resolve=>{release=resolve;});
        return Response.json([{id:'old-candidate',promoted:false,body:{methods:[]}}]);
      }
      if (path==='/api/v1/goals/goal-1/reviews') return Response.json([{id:1,actor:'manager',body:{kind:'correction',text:'Old private review'}}]);
      if (path==='/api/v1/goals/goal-2/models') return Response.json([{id:'new-candidate',promoted:false,body:{methods:[]}}]);
      if (path==='/api/v1/goals/goal-2/reviews' || path==='/api/v1/runs?goal_id=goal-2') return Response.json([]);
      if (path==='/api/v1/goals/goal-2/findings') return Response.json(null);
      return original(input,init);
    }));
    sessionStorage.setItem('backintel-access','component-fixture-access');
    const user=userEvent.setup();render(<App/>);
    const goals=await screen.findByRole('navigation',{name:'Saved goals'});
    await user.click(within(goals).getByRole('button',{name:new RegExp(standingQuestion)}));
    await waitFor(()=>expect(release).toBeTypeOf('function'));
    await user.click(within(goals).getByRole('button',{name:/Second question/}));
    await user.click(screen.getByRole('button',{name:'Review',exact:true}));
    expect(await screen.findByText(/Candidate new-candidat/)).toBeVisible();
    await act(async()=>{release!();});
    expect(screen.queryByText(/old-candidat|Old private review/)).not.toBeInTheDocument();
    expect(screen.getByText(/Candidate new-candidat/)).toBeVisible();
  });

  it('clears all scoped data on sign-out and ignores an old evidence response', async () => {
    const user=await openWorkspace();
    const original=fetch;
    let release: (()=>void) | undefined;
    vi.stubGlobal('fetch',vi.fn(async (input: RequestInfo | URL,init?: RequestInit)=>{
      if (String(input).includes('/evidence/')) {
        await new Promise<void>(resolve=>{release=resolve;});
        return Response.json({private:'old-principal-evidence'});
      }
      return original(input,init);
    }));
    await user.click(screen.getByRole('button',{name:'Inspect calculation'}));
    await waitFor(()=>expect(release).toBeTypeOf('function'));
    await user.click(screen.getByRole('button',{name:'Sign out'}));
    role='viewer';
    vi.stubGlobal('fetch',vi.fn(async (input: RequestInfo | URL,init?: RequestInit)=>{
      if (String(input)==='/api/v1/goals') return Response.json([]);
      return original(input,init);
    }));
    await user.type(screen.getByLabelText('Access credential'),'narrower-access');
    await user.click(screen.getByRole('button',{name:'Open workspace'}));
    await screen.findByRole('heading',{name:'Fixture clothing reviews'});
    await act(async()=>{release!();});
    await user.click(screen.getByRole('button',{name:'History',exact:true}));
    expect(screen.getByText('No runs for the selected goal.')).toBeVisible();
    expect(screen.queryByText(answer)).not.toBeInTheDocument();
    expect(screen.queryByText(/old-principal-evidence/)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Source and calculation evidence'})).not.toBeInTheDocument();
  });

  it('removes cached answers when a refresh loses authorization', async () => {
    const user=await openWorkspace();
    const original=fetch;
    vi.stubGlobal('fetch',vi.fn(async (input: RequestInfo | URL,init?: RequestInit)=>{
      if (String(input)==='/api/v1/me') return Response.json({detail:'Access revoked'}, {status:403});
      return original(input,init);
    }));
    await user.click(screen.getByRole('button',{name:'Run analysis'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Access revoked');
    expect(screen.getByLabelText('Access credential')).toBeVisible();
    expect(screen.queryByText(answer)).not.toBeInTheDocument();
    expect(sessionStorage.getItem('backintel-access')).toBeNull();
  });

  it('shows the complete connected answer and saves, inspects and downloads its workflow', async () => {
    goal.source_access = true;
    goal.body.objective = {source_ref:'retail-connection',allowed_schemas:['retail_raw'],freshness:'Historical snapshot'};
    savedFinding.body.operation = 'answer';
    savedFinding.result.mode = 'fixture';
    savedFinding.result.calculation = {currency:'GBP',period_start:'2020-12-01T00:00:00',period_end:'2020-12-05T00:00:00',
      coverage:{processed_rows:5,expected_rows:5},totals:{net_invoice_value:'6.5',signed_cancellation_value:'-3.25',cancellation_reduction:'3.25'},
      dimensions:[{label:'product',field:'product_code',groups:[{value:'A',row_count:2,net_value:'3.25',signed_cancellation_value:'-3.25'},
        {value:'B',row_count:1,net_value:'3.25',signed_cancellation_value:'0'}]}]};
    const user = await openWorkspace();
    expect(screen.getByText('Processed 5 of 5 rows.')).toBeInTheDocument();
    expect(screen.getByRole('table',{name:'Net invoice value by product_code'})).toHaveTextContent('3.25');
    expect(screen.getByText('Simulated analysis method. Live agent method generation has not been verified.')).toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:'Save checked workflow'}));
    expect(await screen.findByText('This version contains a simulated method.')).toBeInTheDocument();
    expect(requests.some(item=>item.path==='/api/v1/runs/run-1/workflow'&&item.method==='POST')).toBe(true);
    savedFinding.body.operation = 'workflow';
    await user.click(screen.getByRole('button',{name:/Run saved workflow/}));
    expect(requests.some(item=>item.path==='/api/v1/workflows/workflow-fixture-1/runs'&&item.method==='POST')).toBe(true);
    expect(screen.getByRole('button',{name:/Run saved workflow/})).toBeEnabled();
    expect(screen.queryByRole('button',{name:'Save checked workflow'})).not.toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:/Inspect saved workflow/}));
    expect(await screen.findByText(/"status": "ready"/)).toBeInTheDocument();
    const createURL=vi.fn(()=> 'blob:workflow-fixture');
    const revokeURL=vi.fn();
    vi.stubGlobal('URL',Object.assign(URL,{createObjectURL:createURL,revokeObjectURL:revokeURL}));
    const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
    await user.click(screen.getByRole('button',{name:/Download workflow/}));
    await waitFor(()=>expect(click).toHaveBeenCalledOnce());
    expect(createURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(revokeURL).toHaveBeenCalledWith('blob:workflow-fixture');
    click.mockRestore();
    await user.click(screen.getByRole('button',{name:'Sources',exact:true}));
    expect(screen.getByRole('heading',{name:'Connected data analysis'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Source connection'})).toBeInTheDocument();
    expect(screen.getByText('retail-connection')).toBeInTheDocument();
    expect(screen.queryByRole('link',{name:'Review original source terms'})).not.toBeInTheDocument();
  });

  it('shows incomplete retained preparation without presenting it as completion', async () => {
    runs = [{...runs[0],id:'prepared-partial',snapshot_id:null,status:'partial',coverage:{processed_rows:2,expected_rows:5,pending_rows:3},
      body:{operation:'preparation',question:'Prepare the full source.'},
      result:{summary:'Preparation reached its time limit.',usage:{provider_usd:0,charge_status:'measured'},limitations:[]}}];
    const user = await openWorkspace();
    await user.click(screen.getByRole('button',{name:'History',exact:true}));
    expect(screen.getByText('Prepared 2 of 5 rows. Pending: 3.')).toBeInTheDocument();
    expect(screen.getByText('Preparation reached its time limit.')).toBeInTheDocument();
  });

  it('keeps the saved answer when fifty newer runs fill the history', async () => {
    runs = Array.from({length: 50}, (_, i) => ({...runs[0], id: 'newer-'+i, status: 'partial', result: null}));
    await openWorkspace();
    expect(screen.getByText(answer)).toBeVisible();
    expect(requests.some(r => r.path === '/api/v1/goals/goal-1/findings')).toBe(true);
  });
  it('shows an expired credential failure and permits another login', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({detail: 'Access credential is invalid, revoked, or expired'}, {status: 403})));
    const user = userEvent.setup(); render(<App/>);
    await user.type(screen.getByLabelText('Access credential'), 'expired-fixture');
    await user.click(screen.getByRole('button', {name: 'Open workspace'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('expired');
    expect(screen.getByLabelText('Access credential')).toBeEnabled();
  });

  it('requires source confirmation before enabling import', async () => {
    source.body.terms_acknowledged = false;
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Sources', exact: true}));
    expect(screen.getByRole('button', {name: 'Import or check for updates'})).toBeDisabled();
    await user.click(screen.getByRole('button', {name: 'Confirm source access and terms'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Import or check for updates'})).toBeEnabled());
    expect(requests.find(r => r.path.endsWith('/terms'))?.body).toEqual({acknowledged: true});
  });

  it('requires reconfirmation after saving changed run limits', async () => {
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Goals', exact: true}));
    await user.clear(screen.getByLabelText('Maximum frontier cost per run (USD)'));
    await user.type(screen.getByLabelText('Maximum frontier cost per run (USD)'), '0.25');
    await user.click(screen.getByRole('button', {name: 'Save goal limits'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Confirm definitions'})).toBeEnabled());
    expect(requests.find(r => r.method === 'PATCH')?.body.budget_usd).toBe(0.25);
    await user.click(screen.getByRole('button', {name: 'Analysis', exact: true}));
    expect(screen.getByRole('button', {name: 'Run analysis'})).toBeDisabled();
  });

  it('submits a follow-up without changing the standing question', async () => {
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Conversation', exact: true}));
    await user.type(screen.getByLabelText('Follow-up question'), 'What is the sample size?');
    await user.click(screen.getByRole('button', {name: 'Investigate'}));
    await waitFor(() => expect(screen.getByLabelText('Follow-up question')).toHaveValue(''));
    expect(requests.find(r => r.path.endsWith('/runs') && r.method === 'POST')?.body).toEqual({question: 'What is the sample size?'});
    expect(goal.body.question).toBe(standingQuestion);
  });

  it('preserves the completed answer when a new run is blocked', async () => {
    failRun = true;
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Run analysis'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('charge unresolved');
    expect(screen.getByText(answer)).toBeVisible();
    expect(screen.getByRole('button', {name: 'Run analysis'})).toBeEnabled();
  });

  it('keeps controls disabled while admission is pending', async () => {
    delayRun = true;
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Run analysis'}));
    expect(screen.getByRole('button', {name: 'Run analysis'})).toBeDisabled();
    await waitFor(() => expect(releaseRun).toBeDefined());
    releaseRun!();
    await waitFor(() => expect(screen.getByRole('button', {name: 'Run analysis'})).toBeEnabled());
  });

  it('opens the cited evidence and closes it with its named control', async () => {
    const user = await openWorkspace();
    await user.click(screen.getByRole('button', {name: 'Inspect calculation'}));
    expect(await screen.findByRole('heading', {name: 'Source and calculation evidence'})).toBeVisible();
    expect(screen.getByText(/"snapshot": "snapshot-1"/)).toBeVisible();
    await user.click(screen.getByRole('button', {name: 'Close evidence'}));
    expect(screen.queryByRole('heading', {name: 'Source and calculation evidence'})).not.toBeInTheDocument();
  });

  it('renders read-only results and disables analysis actions for viewers', async () => {
    role = 'viewer'; const user = await openWorkspace();
    expect(screen.queryByRole('button', {name: 'Run analysis'})).not.toBeInTheDocument();
    expect(within(screen.getByRole('table')).getAllByRole('cell').map(cell => cell.textContent)).toEqual(['A', '4', '4', '0.5']);
    await user.click(screen.getByRole('button', {name: 'Conversation', exact: true}));
    expect(screen.getByRole('button', {name: 'Investigate'})).toBeDisabled();
    await user.click(screen.getByRole('button', {name: 'Sources', exact: true}));
    expect(screen.queryByRole('button', {name: 'Confirm source access and terms'})).not.toBeInTheDocument();
  });

  it('shows empty answers and treats source text as inert text', async () => {
    const hostile = '<img src=x onerror=alert(1)>';
    goal.last_success = null; runs = []; source.body.caveat = hostile;
    sessionStorage.setItem('backintel-access', 'component-fixture-access');
    const user = userEvent.setup(); render(<App/>);
    await screen.findByRole('heading', {name: 'Fixture clothing reviews'});
    await user.click(within(screen.getByRole('navigation', {name: 'Saved goals'})).getByRole('button'));
    expect(await screen.findByRole('heading', {name: 'No completed answer yet'})).toBeVisible();
    expect(screen.getByText(hostile)).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });
});
