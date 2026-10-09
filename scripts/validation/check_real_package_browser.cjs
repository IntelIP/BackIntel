const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const root = path.resolve(process.argv[2]);
  const output = path.join(root, 'Browser');
  fs.mkdirSync(output, { recursive: true });
  const receipt = { status: 'running', provider: 'fixture', checks: [], screenshots: [] };
  let browser;
  try {
    browser = await chromium.launch({ executablePath: process.env.BACKINTEL_CHROMIUM_EXECUTABLE, headless: true });
    for (const task of fs.readdirSync(path.join(root, 'Reports'))) {
      for (const file of ['Report.html', 'GeneratedView.html']) {
        const source = path.join(root, 'Reports', task, 'operator', file);
        for (const width of [1280, 390]) {
          const page = await browser.newPage({ viewport: { width, height: 900 } });
          await page.goto(pathToFileURL(source).href);
          const label = await page.locator('p.tag').first().innerText();
          if (!label.includes('Text findings: deterministic test fixtures')) throw new Error('Fixture status is not visible');
          if (await page.locator('form').count()) throw new Error('Offline export exposes a live form');
          if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Page overflows the viewport');
          if (await page.locator('a[href^="/"]').count()) throw new Error('Offline export contains live-app links');
          receipt.checks.push({ task, file, width, fixture_label_visible: true, offline: true, no_page_overflow: true });
          if (file === 'Report.html') {
            const image = path.join(output, `${task}-${width}.png`);
            await page.screenshot({ path: image, fullPage: true });
            receipt.screenshots.push(image);
          }
          await page.close();
        }
      }
    }
    receipt.status = 'passed';
  } catch (error) {
    receipt.status = 'failed';
    receipt.error = error.message;
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    const target = path.join(output, 'Checks.json');
    fs.writeFileSync(target, JSON.stringify(receipt, null, 2));
    process.stdout.write(JSON.stringify({ status: receipt.status, checks: receipt.checks.length, receipt: target }) + '\n');
  }
})();
