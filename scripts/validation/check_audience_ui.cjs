/* Render and exercise the local audience surface; access tokens are never logged. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

async function main() {
  const fixture = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const base = process.env.BACKINTEL_AUDIENCE_URL || 'http://127.0.0.1:2028';
  const output = path.resolve('artifacts/validation/AudienceUI', crypto.randomUUID());
  fs.mkdirSync(output, { recursive: true });
  const result = { schema: 'backintel-audience-ui/v1', candidate: 'uncommitted-working-tree', status: 'running',
    checks: [], screenshots: [], browser_errors: [], paid_provider_calls: 0, local_compute_usd: null };
  const check = (name, passed) => {
    result.checks.push({ name, passed: Boolean(passed) });
    if (!passed) throw new Error(name);
  };
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.BACKINTEL_BROWSER_PATH });
    async function capture(page, name) {
      const metrics = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth,
        unlabeled: [...document.querySelectorAll('input:not([type=hidden]),textarea,select')].filter(e => !e.labels.length && !e.getAttribute('aria-label')).length,
        unnamed: [...document.querySelectorAll('a,button')].filter(e => !(e.textContent.trim() || e.getAttribute('aria-label'))).length,
        main: document.querySelectorAll('main').length,
        headings: document.querySelectorAll('h1').length,
      }));
      check(name + ':page_width', !metrics.overflow);
      check(name + ':labels_and_structure', metrics.unlabeled === 0 && metrics.unnamed === 0 && metrics.main === 1 && metrics.headings === 1);
      const file = path.join(output, name + '.png');
      await page.screenshot({ path: file, fullPage: true });
      result.screenshots.push({ name, path: file, sha256: crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'), metrics });
    }
    for (const task of fixture.tasks) {
      for (const audience of ['manager', 'operator', 'analyst', 'empty']) {
        const grant = fixture.grants.find(g => g.task_id === task && g.audience === audience);
        const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
        const page = await context.newPage();
        page.on('pageerror', e => result.browser_errors.push(e.message));
        await page.goto(base + '/login');
        await page.getByLabel('Audience access token').fill(grant.token);
        await Promise.all([page.waitForURL(base + '/'), page.getByRole('button', { name: 'Open report', exact: true }).click()]);
        check(task + ':' + audience + ':login', await page.locator('h1').count() === 1 && !(await page.locator('h1').innerText()).includes('unavailable'));
        const key = task.split('-')[0] + '-' + audience;
        await capture(page, key + '-desktop');
        if (audience === 'manager' || audience === 'analyst') {
          check(key + ':readonly_controls', await page.locator('form[action="/correct"],form[action="/review"]').count() === 0);
        }
        if (audience !== 'empty') {
          const summary = page.locator('details > summary').first();
          await summary.focus();
          await page.keyboard.press('Enter');
          check(key + ':keyboard_evidence', await page.locator('details').first().getAttribute('open') !== null);
          const href = await page.getByRole('link', { name: 'Open source record' }).first().getAttribute('href');
          const response = await context.request.get(base + href);
          check(key + ':source_open', response.status() === 200 && (await response.json()).kind === 'source');
        }
        await page.setViewportSize({ width: 390, height: 844 });
        if (audience !== 'empty') {
          const table = page.getByRole('region', { name: 'Outcome comparison' });
          await table.focus();
          await page.keyboard.press('ArrowRight');
          await page.waitForFunction(() => document.querySelector('.scroll').scrollLeft > 0);
          check(key + ':keyboard_table_scroll', await table.evaluate(element => element.scrollLeft > 0));
          await table.evaluate(element => { element.scrollLeft = 0; });
        }
        await capture(page, key + '-mobile');
        if (audience === 'operator') {
          const candidates = await page.locator('a[href^="/candidate/"]').evaluateAll(elements => elements.map(e => e.getAttribute('href')));
          check(key + ':candidate_links', candidates.length === 2);
          for (let index = 0; index < candidates.length; index++) {
            await page.goto(base + candidates[index]);
            await capture(page, key + '-candidate-' + index);
          }
          await page.goto(base + '/');
          await page.locator('details > summary').first().click();
          const form = page.locator('form[action="/correct"]').first();
          const select = form.locator('select[name="value"]');
          if (await select.count()) await select.selectOption('false');
          else await form.locator('input[name="value"]').fill('2.5');
          await form.getByLabel('Reason for correction').fill('Browser-checked correction on synthetic data');
          await Promise.all([page.waitForURL(base + '/'), form.getByRole('button').click()]);
          await page.waitForLoadState('domcontentloaded');
          check(key + ':browser_correction', (await page.content()).includes('Browser-checked correction on synthetic data'));
          await capture(page, key + '-correction-saved');
        }
        await context.close();
      }
    }
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    const denied = await page.goto(base + '/');
    check('unauthenticated_error', denied.status() === 403);
    await capture(page, 'access-denied-mobile');
    await page.goto(base + '/login');
    await capture(page, 'login-mobile');
    await context.close();
    check('browser_runtime_errors', result.browser_errors.length === 0);
    result.status = 'passed';
  } catch (error) {
    result.status = 'failed'; result.error = error.message;
    throw error;
  } finally {
    if (browser) await browser.close();
    const file = path.join(output, 'checks.json');
    fs.writeFileSync(file, JSON.stringify(result, null, 2));
    console.log(JSON.stringify({ status: result.status, checks: result.checks.length, captures: result.screenshots.length, receipt: file }));
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
