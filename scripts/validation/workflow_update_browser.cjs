const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('fs');const path=require('path');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(process.env.S21_URL,{waitUntil:'domcontentloaded'});
    await page.getByLabel('Access credential',{exact:true}).fill(process.env.S21_TOKEN);
    await page.getByRole('button',{name:'Open workspace'}).click();
    await page.getByRole('navigation',{name:'Data domains'}).getByRole('button').filter({hasText:new RegExp(process.env.S21_DOMAIN,'i')}).click();
    await page.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:process.env.S21_QUESTION}).first().click();
    const panel=page.getByRole('region',{name:'Answer updates'});
    await panel.getByText('Update status: '+process.env.S21_STATE+'.',{exact:true}).waitFor({timeout:30000});
    await panel.getByRole('heading',{name:'Last accepted answer'}).waitFor();
    await panel.getByText(/Source observed:/).waitFor();
    if(process.env.S21_DECISION)await panel.getByText(new RegExp(process.env.S21_DECISION)).first().waitFor();
    await panel.scrollIntoViewIfNeeded();
    await panel.screenshot({path:path.join(process.env.S21_OUTPUT,process.env.S21_CASE+'-desktop.png')});
    await page.setViewportSize({width:390,height:844});
    await panel.screenshot({path:path.join(process.env.S21_OUTPUT,process.env.S21_CASE+'-mobile.png')});
    if(errors.length)throw Error(errors.join('\n'));
    console.log('PASS: accepted answer, source time, update status, and required decision are visible');
  } catch(error) {
    fs.writeFileSync(path.join(process.env.S21_OUTPUT,process.env.S21_CASE+'-visible-text.txt'),await page.locator('body').innerText());
    throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
