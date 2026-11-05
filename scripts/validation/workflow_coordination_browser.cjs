const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];
  const rejected=process.env.S33_EXPECT_REJECTED==='1';
  const prefix=rejected?'coordination-rejected':'coordination';
  page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(process.env.S33_URL,{waitUntil:'domcontentloaded'});
    await page.getByLabel('Access credential',{exact:true}).fill(process.env.BACKINTEL_ACCESS_TOKEN);
    await page.getByRole('button',{name:'Open workspace',exact:true}).click();
    await page.getByRole('navigation',{name:'Data domains'}).getByRole('button').filter({hasText:new RegExp(process.env.S33_DOMAIN,'i')}).click();
    await page.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:process.env.S33_QUESTION}).first().click();
    const panel=page.getByRole('region',{name:'Specialist coordination',exact:true});
    await panel.getByText(rejected?/Shared plan: partial/:/Shared plan: succeeded/).waitFor({timeout:30000});
    for(const role of ['data','analysis','checking']) {
      const specialist=panel.getByRole('article',{name:role+' specialist',exact:true});
      await specialist.getByText('Status: '+(rejected&&role==='checking'?'rejected':'accepted')+'.',{exact:true}).waitFor();
      await specialist.getByText('Inspect contribution and evidence',{exact:true}).click();
      await specialist.getByText(/Input version:/).waitFor();
    }
    if(rejected) await panel.getByRole('alert').filter({hasText:'net_invoice_value'}).waitFor();
    await page.getByText(process.env.S33_EXPECTED_NET,{exact:false}).first().waitFor();
    await panel.screenshot({path:path.join(process.env.S33_OUTPUT,prefix+'-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await panel.screenshot({path:path.join(process.env.S33_OUTPUT,prefix+'-mobile.png')});
    if(await panel.evaluate(element=>element.scrollWidth>element.clientWidth)) throw Error('Coordination panel overflows mobile viewport');
    if(errors.length) throw Error(errors.join('\n'));
    fs.writeFileSync(path.join(process.env.S33_OUTPUT,prefix+'-visible-text.txt'),await panel.innerText());
    console.log('PASS: '+(rejected?'the rejected finding and last accepted answer remain visible':'all three accepted contributions and their versions are visible')+' on desktop and mobile.');
  } catch(error) {
    fs.writeFileSync(path.join(process.env.S33_OUTPUT,'browser-failed-text.txt'),await page.locator('body').innerText());
    await page.screenshot({path:path.join(process.env.S33_OUTPUT,'browser-failed.png'),fullPage:true});
    throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
