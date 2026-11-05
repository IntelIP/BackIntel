const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');

(async()=>{
  const browser=await chromium.launch({headless:true});
  const tokens=JSON.parse(process.env.S30_TOKENS);
  const results=[];
  try {
    for(const name of ['a','b','viewer']) {
      const context=await browser.newContext({viewport:{width:1440,height:1000}});
      const page=await context.newPage();
      const errors=[];page.on('pageerror',error=>errors.push(error.message));
      await page.goto(process.env.S30_URL,{waitUntil:'domcontentloaded'});
      await page.getByLabel('Access credential',{exact:true}).fill(tokens[name]);
      await page.getByRole('button',{name:'Open workspace',exact:true}).click();
      const panel=page.getByRole('region',{name:'Work in progress'});
      await panel.getByText(/Your model spending: US\$0.0000 charged/).waitFor();
      const navigation=page.getByRole('navigation',{name:'Saved goals'});
      await navigation.getByRole('button').first().waitFor();
      const labels=await navigation.getByRole('button').allTextContents();
      if(labels.length !== (name==='viewer'?1:2)) throw new Error('Unexpected number of visible objectives');
      const owner=name==='viewer'?'A':name.toUpperCase();
      if(labels.some(label=>!label.startsWith('Owner '+owner+' analysis '))) throw new Error('Another owner objective was disclosed');
      await navigation.getByRole('button').first().click();
      if(name==='viewer') {
        await page.getByRole('button',{name:'Goals',exact:true}).click();
        if(await page.getByRole('button',{name:'Save goal',exact:true}).count()) throw new Error('Viewer can create goals');
        await page.getByRole('button',{name:'History',exact:true}).click();
        if(await page.getByRole('button',{name:'Cancel run',exact:true}).count()) throw new Error('Viewer has cancellation controls');
      }
      const text=await panel.innerText();
      await page.screenshot({path:path.join(process.env.S30_OUTPUT,'multiuser-'+name+'.png'),fullPage:true});
      await page.setViewportSize({width:390,height:844});
      if(await panel.evaluate(element=>element.scrollWidth>element.clientWidth || element.getBoundingClientRect().right>innerWidth)) throw new Error('Queue has horizontal overflow');
      if(errors.length) throw new Error(errors.join('\n'));
      results.push({name,labels,queue:text,errors});
      await context.close();
    }
    fs.writeFileSync(path.join(process.env.S30_OUTPUT,'multiuser-browser.json'),JSON.stringify({status:'passed',accounts:results},null,2));
    console.log('PASS: separate owner workspaces and read-only viewer, visible queue and costs, desktop and narrow layout.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
