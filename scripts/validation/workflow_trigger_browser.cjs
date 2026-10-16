const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(process.env.S20_BROWSER_URL,{waitUntil:'domcontentloaded'});
    await page.getByLabel('Access credential',{exact:true}).fill(process.env.S20_BROWSER_TOKEN);
    await page.getByRole('button',{name:'Open workspace',exact:true}).click();
    await page.getByRole('navigation',{name:'Data domains'}).getByRole('button').filter({hasText:new RegExp(process.env.S20_DOMAIN,'i')}).click();
    await page.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:process.env.S20_GOAL_QUESTION}).first().click();
    const panel=page.getByRole('region',{name:'Automatic workflow starts'}).getByRole('article')
      .filter({has:page.locator('code').filter({hasText:'/api/v1/triggers/'+process.env.S20_TRIGGER+'/events'})});
    await panel.getByText('retail.collection.completed',{exact:true}).waitFor({timeout:180000});
    // Observe rendered state across the native scheduler's minute tick.
    try {await panel.getByText(/Accepted starts: 2 of 2/).waitFor({timeout:180000});}
    catch(error) {
      fs.writeFileSync(path.join(process.env.S20_OUTPUT,'trigger-visible-text.txt'),await panel.innerText());
      await page.screenshot({path:path.join(process.env.S20_OUTPUT,'trigger-failed.png'),fullPage:true});
      throw error;
    }
    // The accepted answer replaces the result panel. Open its current history
    // after completion, rather than retaining a disclosure from the old answer.
    await panel.getByText(/Work succeeded/).first().waitFor({state:'attached',timeout:900000});
    const history=panel.locator('details').filter({has:page.getByText('Run and attempt history',{exact:true})});
    if(!await history.evaluate(element=>element.open))await history.locator('summary').click();
    await panel.getByText(/Work succeeded/).first().waitFor();
    await panel.getByText(/Event identity was already used/).waitFor();
    await panel.scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(process.env.S20_OUTPUT,'trigger-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    if(await panel.evaluate(element=>element.scrollWidth>element.clientWidth || element.getBoundingClientRect().right>innerWidth)) {
      const overflow=await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(element=>element.getBoundingClientRect().right>innerWidth)
        .map(element=>({tag:element.tagName,classes:element.className,width:element.getBoundingClientRect().width,right:element.getBoundingClientRect().right,text:element.textContent.slice(0,120)})).slice(-20));
      fs.writeFileSync(path.join(process.env.S20_OUTPUT,'mobile-overflow.json'),JSON.stringify(overflow,null,2));
      throw new Error('The trigger panel has horizontal overflow');
    }
    await page.screenshot({path:path.join(process.env.S20_OUTPUT,'trigger-mobile.png'),fullPage:true});
    if(errors.length)throw new Error(errors.join('\n'));
    fs.writeFileSync(path.join(process.env.S20_OUTPUT,'browser-result.json'),JSON.stringify({status:'passed',errors,visibleHistory:true,nativeScheduledResult:true},null,2));
    console.log('PASS: actual native schedule, event, saved answer, and owner-visible browser history');
  } catch(error) {
    fs.writeFileSync(path.join(process.env.S20_OUTPUT,'browser-visible-text.txt'),await page.locator('body').innerText());
    await page.screenshot({path:path.join(process.env.S20_OUTPUT,'browser-failed.png'),fullPage:true});
    throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
