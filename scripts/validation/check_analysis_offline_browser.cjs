const fs = require('node:fs');
const path = require('node:path');
const {chromium, request} = require('playwright');

(async () => {
  const [out, base, accessPath] = process.argv.slice(2);
  const access = JSON.parse(fs.readFileSync(accessPath, 'utf8'));
  const receipt = {status: 'failed', mode: 'fixture', provider_calls: 0, provider_usd: 0, domains: [], scenarios: [], views: [], screenshots: []};
  // Fixed answers follow directly from the CSV fixture definitions, independent of adapters/tools.
  const oracles = {commerce:{group:'B',count:20,mean:0},support:{group:'silver',count:20,mean:1},
    churn:{group:'Yearly',count:20,mean:0},credit:{group:'Working',count:40,mean:.5},maintenance:{group:'train-1',count:2,mean:.5}};
  let browser, worker, manager, cronId, activeScenario;
  function begin(id, domain) {activeScenario = {id, domain, mode:'fixture'};}
  const check = (condition, message) => {if (!condition) throw Error(message);};
  function passed(id, domain, evidence) {receipt.scenarios.push({id, domain, status:'passed', mode:'fixture', ...evidence});activeScenario=null;}
  async function api(client, method, route, data) {
    const response = await client.fetch(route, {method, data});
    if (!response.ok()) throw Error(route + ': HTTP ' + response.status() + ' ' + (await response.text()).slice(0,500));
    return response.status() === 204 ? null : response.json();
  }
  async function until(read, accept, seconds = 35) {
    const deadline = Date.now() + seconds * 1000;
    while (Date.now() < deadline) {const value = await read(); if (accept(value)) return value; await new Promise(resolve => setTimeout(resolve, 250));}
    throw Error('Timed out waiting for expected durable result');
  }
  async function runs(goal) {return api(manager, 'GET', '/api/v1/runs?goal_id=' + goal);}
  async function finished(identity) {
    return until(() => api(manager, 'GET', '/api/v1/runs/' + identity), value => ['succeeded','partial','cancelled','failed'].includes(value.status));
  }
  try {
    manager = await request.newContext({baseURL: base, extraHTTPHeaders: {Authorization: 'Bearer ' + access.manager}});
    worker = await request.newContext({baseURL: base, extraHTTPHeaders: {Authorization: 'Bearer ' + access.worker}});
    const executablePath = process.env.BACKINTEL_CHROMIUM_EXECUTABLE || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : chromium.executablePath());
    browser = await chromium.launch({executablePath, headless: true});
    const page = await browser.newPage({viewport: {width:1440,height:1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/#access=' + access.manager);
    await page.getByRole('heading', {name:'Clothing reviews',exact:true}).waitFor();
    for (const domain of ['commerce','support','churn','credit','maintenance']) {
      begin('BI-DATA-001', domain);
      await page.getByRole('navigation', {name:'Data domains'}).getByRole('button').filter({hasText: new RegExp('^' + domain, 'i')}).click();
      await page.getByRole('button', {name:'Sources',exact:true}).click();
      await page.getByRole('button', {name:'Confirm source access and terms',exact:true}).click();
      await page.getByRole('button', {name:'Import or check for updates',exact:true}).click();
      await until(() => api(manager, 'GET', '/api/v1/sources'), sources => sources.find(s => s.domain === domain)?.latest_snapshot);
      await page.getByRole('button', {name:'Goals',exact:true}).click();
      const question = 'What is the observed value for ' + domain + '?';
      await page.getByLabel('Question to monitor').fill(question);
      await page.getByRole('button', {name:'Propose goal',exact:true}).click();
      await page.getByRole('heading', {name:'Confirm business meaning',exact:true}).waitFor();
      await page.getByRole('button', {name:'Confirm definitions',exact:true}).click();
      const goal = await until(() => api(manager,'GET','/api/v1/goals'), goals => goals.find(g => g.domain === domain && g.confirmed));
      const selected = goal.find(g => g.domain === domain && g.confirmed);
      await page.getByRole('button', {name:'Analysis',exact:true}).click();
      await page.getByRole('button', {name:'Run analysis',exact:true}).click();
      const standing = (await until(() => runs(selected.id), list => list.some(r => r.status === 'succeeded'))).find(r => r.status === 'succeeded');
      check(standing.result.mode === 'fixture', 'Fixture result must be labeled');
      await page.getByRole('button', {name:'Inspect calculation',exact:true}).first().waitFor();
      await page.getByRole('button', {name:'Inspect calculation',exact:true}).first().click();
      await page.getByRole('heading', {name:'Source and calculation evidence',exact:true}).waitFor();
      const evidence = await api(manager,'GET','/api/v1/evidence/' + standing.result.findings[0].evidence_ids[0]);
      check(evidence.body.snapshot === standing.snapshot_id, 'Evidence snapshot differs from the run');
      check(evidence.body.result.table.length > 0, 'Calculation table is empty');
      const first = evidence.body.result.table[0], expected = oracles[domain];
      check(first.group === expected.group && first.count === expected.count && first.mean === expected.mean, domain + ' disagrees with the independent fixture oracle');
      passed('BI-DATA-001', domain, {run_id:standing.id, snapshot_id:standing.snapshot_id, expected, observed:first});
      begin('BI-DURABLE-001', domain);
      const duplicate = await api(manager,'POST','/api/v1/goals/' + selected.id + '/runs',{});
      check(duplicate.id === standing.id && duplicate.job_id === standing.job_id, 'Duplicate admission changed run/job identity');
      const afterDuplicate = await finished(duplicate.id);
      check(JSON.stringify(afterDuplicate.result) === JSON.stringify(standing.result), 'Duplicate admission changed accepted result');
      check((await runs(selected.id)).length === 1, 'Duplicate admission produced another result');
      passed('BI-DURABLE-001', domain, {run_id:standing.id, job_id:standing.job_id, result_unchanged:true, analysis_runs:1});
      begin('BI-REFRESH-001', domain);
      const refreshed = await api(manager,'POST','/api/v1/sources/' + domain + '/refresh',{});
      const refreshedResult = await finished(refreshed.id);
      check(refreshedResult.status === 'succeeded' && refreshedResult.result.changed === false, 'Unchanged refresh changed snapshot');
      check((await runs(selected.id)).length === 1, 'Unchanged refresh produced another analysis');
      passed('BI-REFRESH-001', domain, {import_run_id:refreshed.id, standing_run_id:standing.id, snapshot_id:standing.snapshot_id, analysis_runs:1});
      await page.getByRole('button', {name:'Close evidence',exact:true}).click();
      await page.getByRole('button', {name:'Conversation',exact:true}).click();
      begin('BI-DIALOGUE-001', domain);
      await page.getByLabel('Follow-up question').fill('Follow-up observed value for ' + domain);
      await page.getByRole('button', {name:'Investigate',exact:true}).click();
      await until(() => runs(selected.id), list => list.filter(r => r.status === 'succeeded').length === 2);
      const unchanged = (await api(manager,'GET','/api/v1/goals')).find(g => g.id === selected.id);
      check(unchanged.last_success === standing.id, 'Follow-up replaced the standing answer');
      check(JSON.stringify((await finished(standing.id)).result) === JSON.stringify(standing.result), 'Follow-up mutated the standing result');
      passed('BI-DIALOGUE-001', domain, {standing_run_id:standing.id, last_success:unchanged.last_success});
      receipt.domains.push({domain, goal_id:selected.id, standing_run:standing.id, source_import:true, confirmed_goal:true, supported_answer:true, independent_oracle:true, evidence_snapshot:true, followup_preserves_standing:true, mode:'fixture'});
    }
    const commerce = receipt.domains.find(d => d.domain === 'commerce');
    begin('BI-DIALOGUE-002', 'commerce');
    const bad = await api(manager,'POST','/api/v1/goals/' + commerce.goal_id + '/runs',{question:'fixture_invalid_number'});
    check((await finished(bad.id)).status === 'partial','Unsupported provider numbers were accepted');
    check((await api(manager,'GET','/api/v1/goals')).find(g => g.id === commerce.goal_id).last_success === commerce.standing_run,'A failed run replaced the standing answer');
    passed('BI-DIALOGUE-002', 'commerce', {standing_run_id:commerce.standing_run, failed_followup_id:bad.id});
    const trained = await api(manager,'POST','/api/v1/goals/' + commerce.goal_id + '/runs',{operation:'training'});
    const comparison = await finished(trained.id);
    check(comparison.status === 'succeeded' && comparison.result.mode === 'fixture','Fixture comparison was not labeled');
    const promoted = await api(manager,'POST','/api/v1/models/' + comparison.result.candidate_id + '/promote',{route:'catboost-facts'});
    check((await finished(promoted.id)).status === 'succeeded','Promoted fixture route did not complete');
    const estimated = await api(manager,'POST','/api/v1/goals/' + commerce.goal_id + '/runs',{question:'What is the estimated recommendation risk?'});
    check((await finished(estimated.id)).status === 'succeeded','Approved fixture predictor was not used');
    const calculation = await api(manager,'GET','/api/v1/evidence/' + (await finished(estimated.id)).result.findings[0].evidence_ids[0]);
    check(calculation.body.tool === 'predict','Prediction question used observations');
    begin('BI-CORRECTION-001', 'commerce');
    await api(manager,'POST','/api/v1/sources/commerce/corrections',{record_id:'1',target:0,explanation:'Synthetic correction for notification check'});
    await until(() => runs(commerce.goal_id), list => list.some(r => r.status === 'succeeded' && r.snapshot_id !== calculation.body.snapshot));
    const notices = await api(manager,'GET','/api/v1/notifications');
    check(notices.some(n => n.goal_id === commerce.goal_id),'Material correction did not notify');
    passed('BI-CORRECTION-001', 'commerce', {previous_snapshot_id:calculation.body.snapshot, material_notification:true});
    receipt.recovery = {unsupported_number_rejected:true,last_answer_preserved:true,fixture_promotion:true,prediction_tool:true,correction_refresh:true,internal_notification:true};
    await page.close();
    for (const role of ['manager','analyst','viewer']) for (const width of [1440,390]) {
      begin('BI-ACCESS-001', 'commerce');
      const view = await browser.newPage({viewport:{width,height:1000}});
      const viewErrors=[];view.on('pageerror',error=>viewErrors.push(error.message));
      await view.goto(base + '/#access=' + access[role]);
      await view.getByRole('heading',{name:'Clothing reviews',exact:true}).waitFor();
      await view.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:'What is the observed value for commerce?'}).click();
      await view.getByRole('button',{name:'Sources',exact:true}).click();
      check(Boolean(await view.getByRole('button',{name:'Confirm source access and terms',exact:true}).count()) === (role === 'manager'),'Source permission control mismatch');
      for (const name of ['Goals','Analysis','Conversation','Review','History']) {
        await view.getByRole('button',{name,exact:true}).click();
        check(!await view.evaluate(() => document.documentElement.scrollWidth > innerWidth), name + ' overflows viewport');
        if (name === 'Analysis') {
          const inspect = view.getByRole('button',{name:'Inspect calculation',exact:true}).first();
          await inspect.focus();await view.keyboard.press('Enter');
          await view.getByRole('heading',{name:'Source and calculation evidence',exact:true}).waitFor();
          check(!await view.evaluate(() => document.documentElement.scrollWidth > innerWidth),'Evidence overflows viewport');
          await view.getByRole('button',{name:'Close evidence',exact:true}).click();
        }
      }
      const denial = await view.evaluate(async ({token,role}) => {
        const api = role === 'manager' ? await fetch('/api/v1/me',{headers:{Authorization:'Bearer '+token}}) : await fetch('/api/v1/goals',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({domain:'commerce',question:'denial fixture'})});
        const core = await fetch('/threads',{headers:{Authorization:'Bearer '+token}});
        return {api:api.status,core:core.status};
      },{token:access[role],role});
      check(role === 'manager' || denial.api === 403,'Backend role denial failed');
      check(denial.core === 403,'Core bypass denial failed');
      check(viewErrors.length === 0,'Browser errors: ' + viewErrors.join('; '));
      const shot = role + '-' + width + '.png';
      await view.screenshot({path:path.join(out,shot),fullPage:true});
      passed('BI-ACCESS-001', 'commerce', {role,width,write_status:denial.api,core_status:denial.core});
      receipt.screenshots.push(shot);receipt.views.push({role,width,no_overflow:true,keyboard_evidence:true,core_denial:true});
      await view.close();
    }
    check(errors.length === 0,errors.join('; '));
    // Real clock, real native cron API; creation is disabled to suppress an immediate run.
    const before = await api(worker,'POST','/runs/crons',{assistant_id:'analysis_refresh',schedule:'* * * * *',input:{run_id:'offline-native-clock'},enabled:false,end_time:new Date(Date.now()+95000).toISOString(),metadata:{backintel_validation:'fixture-clock'}});
    cronId = before.cron_id;
    check(Boolean(cronId),'Disabled cron did not return an identity');
    const next = Date.parse(before.next_run_date);
    check(next > Date.now(),'Cron due time is not in the future');
    const clockThread = await api(worker,'POST','/threads',{metadata:{validation:'native-clock'}});
    // Bind the tested cron to one inspectable thread without changing its due timestamp.
    await api(worker,'DELETE','/runs/crons/' + cronId);
    const scheduled = await api(worker,'POST','/threads/' + clockThread.thread_id + '/runs/crons',{assistant_id:'analysis_refresh',schedule:'* * * * *',input:{run_id:'offline-native-clock'},enabled:false,end_time:new Date(Date.now()+95000).toISOString(),metadata:{backintel_validation:'fixture-clock'}});
    cronId = scheduled.cron_id;
    await api(worker,'PATCH','/runs/crons/' + cronId,{enabled:true});
    const initial = await api(worker,'GET','/threads/' + clockThread.thread_id + '/runs');
    check(initial.length === 0,'Cron fired before its native due time');
    const fired = await until(() => api(worker,'GET','/threads/' + clockThread.thread_id + '/runs'), list => list.some(r => r.status === 'success'), 80);
    const cronRun = fired.find(r => r.status === 'success');
    check(Date.parse(cronRun.created_at) >= Date.parse(scheduled.next_run_date),'Cron fired before due time');
    await api(worker,'DELETE','/runs/crons/' + cronId);cronId=null;
    await api(worker,'DELETE','/threads/' + clockThread.thread_id);
    receipt.native_clock = {status:'passed',mode:'real clock with fixture data/provider',due_at:scheduled.next_run_date,fired_at:cronRun.created_at,run_id:cronRun.run_id,cleanup:'removed'};
    receipt.status='passed';
  } catch (error) {if (activeScenario) receipt.scenarios.push({...activeScenario,status:'failed',reason:error.message});receipt.error=error.message;process.exitCode=1;}
  finally {
    if (cronId && worker) {try {await api(worker,'DELETE','/runs/crons/' + cronId);} catch (_) {receipt.cron_cleanup='database cleanup required';}}
    if (browser) await browser.close();if (manager) await manager.dispose();if (worker) await worker.dispose();
    fs.writeFileSync(path.join(out,'browser-evidence.json'),JSON.stringify(receipt,null,2));
    console.log(JSON.stringify({status:receipt.status,mode:receipt.mode,error:receipt.error,evidence:path.join(out,'browser-evidence.json')}));
  }
})().catch(error => {console.error(error.message);process.exitCode=1;});
