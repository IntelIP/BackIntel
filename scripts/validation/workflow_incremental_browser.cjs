const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(process.env.S24_URL,{waitUntil:'domcontentloaded'});
    await page.getByLabel('Access credential',{exact:true}).fill(process.env.S24_TOKEN);
    await page.getByRole('button',{name:'Open workspace',exact:true}).click();
    await page.getByRole('navigation',{name:'Data domains'}).getByRole('button').filter({hasText:new RegExp(process.env.S24_DOMAIN,'i')}).click();
    await page.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:process.env.S24_QUESTION}).first().click();
    if(process.env.S24_START){
      await page.getByLabel('Workflow to refresh',{exact:true}).selectOption(process.env.S24_VERSION);
      const response=page.waitForResponse(value=>value.request().method()==='POST'&&value.url().endsWith('/refresh'));
      await page.getByRole('button',{name:'Refresh from source',exact:true}).click();
      const admitted=await response;
      if(admitted.status()!==202)throw Error('Refresh rejected: '+await admitted.text());
      await page.getByText('Refresh queued. Check the answer update status for progress.',{exact:true}).waitFor();
    }
    const panel=page.getByRole('region',{name:'Answer updates'});
    if(process.env.S24_STATE==='checked snapshot')await Promise.race([
      panel.getByRole('heading',{name:'Source changes',exact:true}).waitFor({timeout:1000000}),
      panel.getByText(/Update status: (update failed|review required)\./).waitFor({timeout:1000000}).then(()=>{throw Error('The refresh requires attention; inspect the visible update error');})
    ]);
    await panel.getByText('Update status: '+process.env.S24_STATE+'.',{exact:true}).waitFor({timeout:1000000});
    await panel.getByRole('heading',{name:'Last accepted answer',exact:true}).waitFor();
    await panel.getByText(/Source observed:/).waitFor();
    await panel.screenshot({path:path.join(process.env.S24_OUTPUT,process.env.S24_CASE+'-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await panel.screenshot({path:path.join(process.env.S24_OUTPUT,process.env.S24_CASE+'-mobile.png')});
    if(await panel.evaluate(element=>element.scrollWidth>element.clientWidth))throw Error('Update panel overflows on mobile');
    if(errors.length)throw Error(errors.join('\n'));
    fs.writeFileSync(path.join(process.env.S24_OUTPUT,process.env.S24_CASE+'-visible-text.txt'),await panel.innerText());
    console.log('PASS: visible accepted answer and current-source update state');
  } catch(error) {
    fs.writeFileSync(path.join(process.env.S24_OUTPUT,'browser-failed-text.txt'),await page.locator('body').innerText());
    await page.screenshot({path:path.join(process.env.S24_OUTPUT,'browser-failed.png'),fullPage:true});
    throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
