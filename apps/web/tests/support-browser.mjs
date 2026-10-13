import assert from 'node:assert/strict';
import {spawn, spawnSync} from 'node:child_process';
import {existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync} from 'node:fs';
import {homedir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const evidenceRoot = join(homedir(), 'Library/Application Support/BackIntel/Validation/Sprint4');
mkdirSync(evidenceRoot, {recursive: true});
const evidence = mkdtempSync(join(evidenceRoot, 'support-'));
const application = spawn(join(root, '.venv/bin/python'), ['-u', '-m', 'scripts.support_workspace', '--port', '0'], {cwd: root});
let stderr = '';
application.stderr.on('data', data => {stderr += data;});
let browser;

try {
  const address = await new Promise((accept, reject) => {
    const timeout = setTimeout(() => reject(new Error('Local support server did not start: ' + stderr)), 15000);
    let output = '';
    application.stdout.on('data', data => {
      output += data;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+\/support/);
      if (match) {clearTimeout(timeout); accept(match[0]);}
    });
    application.once('exit', code => {clearTimeout(timeout); reject(new Error('Local support server exited: ' + code + ' ' + stderr));});
  });
  const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  browser = await chromium.launch({headless: true, ...(existsSync(chrome) ? {executablePath: chrome} : {})});
  const page = await browser.newPage({viewport: {width: 1365, height: 900}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(address);
  await page.getByRole('heading', {name: 'Which queue needs attention?'}).waitFor();
  assert.equal(await page.getByRole('button', {name: 'Run analysis', exact: true}).isDisabled(), true);
  await page.getByRole('button', {name: 'Use fictional example'}).click();
  await page.getByText('Selected: FictionalSupportTickets.csv', {exact: true}).waitFor();

  async function run() {
    const response = page.waitForResponse(response => response.url().endsWith('/api/support-check') && response.request().method() === 'POST');
    await page.getByRole('button', {name: 'Run analysis', exact: true}).click();
    const value = await response;
    assert.equal(value.status(), 200);
    return value.json();
  }
  async function save(filename) {
    const event = page.waitForEvent('download');
    await page.getByRole('link', {name: 'Save checked report'}).click();
    await (await event).saveAs(join(evidence, filename));
    return readFileSync(join(evidence, filename), 'utf8');
  }

  const initial = await run();
  assert.deepEqual(initial.selected_queues, ['Email']);
  assert.deepEqual(initial.evidence.table.map(row => [row.group, row.count, row.mean]), [['Email', 8, 12], ['Chat', 8, 3.5], ['Phone', 8, 2]]);
  await page.getByRole('heading', {name: '2. Queues to review: Email', exact: true}).waitFor();
  await page.getByText('Fictional example. These are not customer results.', {exact: true}).waitFor();
  await page.getByText('Supporting tickets', {exact: true}).click();
  assert.equal(await page.getByRole('table', {name: 'Supporting tickets', exact: true}).getByRole('row').count(), 9);
  const firstReport = await save('report-email.md');
  for (let n = 1; n <= 8; n++) assert.ok(firstReport.includes('S3-E0' + n));
  assert.ok(firstReport.includes('| Email | 8 | 12 |'));
  assert.ok(firstReport.includes(initial.evidence.input_sha256));
  assert.ok(!firstReport.includes('[input.csv]'));

  const sample = readFileSync(join(root, 'docs/demo/Sprint3SupportTickets.csv'), 'utf8');
  const lines = sample.trimEnd().split(/\r?\n/);
  const columns = lines[0].split(',');
  const channel = columns.indexOf('channel');
  const duration = columns.indexOf('resolution_time_hours');
  const changed = Buffer.from(lines.map((line, index) => {
    if (!index) return line;
    const values = line.split(',');
    if (values[channel] === 'Chat') values[duration] = '20';
    return values.join(',');
  }).join('\n') + '\n');
  writeFileSync(join(evidence, 'changed-fictional-input.csv'), changed);
  await page.getByLabel('Support-ticket file', {exact: true}).setInputFiles({name: 'changed-fictional-input.csv', mimeType: 'text/csv', buffer: changed});
  assert.equal(await page.getByRole('heading', {name: /Queues to review:/}).count(), 0);
  assert.equal(await page.getByRole('link', {name: 'Save checked report'}).count(), 0);
  const updated = await run();
  assert.deepEqual(updated.selected_queues, ['Chat']);
  assert.equal(updated.evidence.table[0].mean, 20);
  assert.equal(updated.evidence.input_sha256, createHash('sha256').update(changed).digest('hex'));
  await page.getByRole('heading', {name: '2. Queues to review: Chat', exact: true}).waitFor();
  await page.getByText('Supporting tickets', {exact: true}).click();
  assert.equal(await page.getByRole('table', {name: 'Supporting tickets', exact: true}).getByRole('row').count(), 9);
  const changedReport = await save('report-chat.md');
  for (let n = 1; n <= 8; n++) assert.ok(changedReport.includes('S3-C0' + n));
  assert.ok(changedReport.includes('| Chat | 8 | 20 |'));
  assert.ok(changedReport.includes(updated.evidence.input_sha256));
  await page.screenshot({path: join(evidence, 'desktop.png'), fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  assert.equal(await page.locator('.workspace').count(), 1);
  assert.equal(await page.getByRole('heading', {name: 'Which queue needs attention?'}).count(), 1);
  await page.getByRole('heading', {name: '2. Queues to review: Chat', exact: true}).scrollIntoViewIfNeeded();
  await page.screenshot({path: join(evidence, 'narrow.png'), animations: 'disabled'});

  await page.getByLabel('Support-ticket file', {exact: true}).setInputFiles({name: 'invalid.csv', mimeType: 'text/csv', buffer: Buffer.from('wrong,columns\n1,2\n')});
  const rejected = page.waitForResponse(response => response.url().endsWith('/api/support-check'));
  await page.getByRole('button', {name: 'Run analysis', exact: true}).click();
  assert.equal((await rejected).status(), 400);
  await page.getByRole('alert').filter({hasText: 'ticket_id, channel, and resolution_time_hours'}).waitFor();
  assert.equal(await page.getByRole('heading', {name: /Queues to review:/}).count(), 0);
  assert.equal(await page.getByRole('link', {name: 'Save checked report'}).count(), 0);
  assert.deepEqual(errors, []);

  const receipt = {
    status: 'passed',
    source_revision: spawnSync('git', ['rev-parse', 'HEAD'], {cwd: root, encoding: 'utf8'}).stdout.trim(),
    working_tree_clean: spawnSync('git', ['status', '--porcelain'], {cwd: root, encoding: 'utf8'}).stdout.trim() === '',
    checks: ['current app screen', 'fictional example', 'queue comparison', 'supporting tickets', 'saved self-contained report', 'changed uploaded input', 'new input clears old answer', 'updated supporting tickets and saved report', 'desktop and narrow layout', 'invalid input rejects stale results', 'no browser page errors'],
    initial_queues: initial.selected_queues, changed_queues: updated.selected_queues,
    initial_input_sha256: initial.evidence.input_sha256, changed_input_sha256: updated.evidence.input_sha256,
    evidence,
  };
  writeFileSync(join(evidence, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt));
} finally {
  if (browser) await browser.close();
  application.kill('SIGTERM');
}
