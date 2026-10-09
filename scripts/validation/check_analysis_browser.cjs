const fs = require('node:fs');
const path = require('node:path');
const child = require('node:child_process');
const {chromium} = require('playwright');

(async () => {
  const out = process.argv[2]; fs.mkdirSync(out, {recursive:true});
  const receipt = {status:'blocked',provider_calls:0,provider_usd:0,checks:[],screenshots:[]};
  let browser;
  try {
    const access = JSON.parse(child.execFileSync('docker',['compose','-f','compose.analysis.yml','exec','-T','runtime','python','-c',"from pathlib import Path;print(Path('/run/backintel-credentials/access.json').read_text())"],{encoding:'utf8'}));
    browser = await chromium.launch({executablePath:process.env.BACKINTEL_CHROMIUM_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
    for (const role of ['manager','analyst','viewer']) {
      for (const width of [1440,390]) {
        const page = await browser.newPage({viewport:{width,height:1000}});
        const errors=[];page.on('pageerror',e=>errors.push(e.message));
        await page.goto('http://127.0.0.1:2028/#access='+access[role]);
        await page.getByRole('heading',{name:'Clothing reviews',exact:true}).waitFor();
        await page.getByRole('button',{name:'Sources',exact:true}).click();
        await page.getByRole('heading',{name:'Source readiness'}).waitFor();
        if (await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error('Page overflows viewport');
        const controls=await page.getByRole('button',{name:'Confirm source access and terms'}).count();
        if ((role==='manager') !== Boolean(controls)) throw Error('Role controls mismatch');
        const denied=await page.evaluate(async token=>{
          const api=await fetch('/api/v1/goals',{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify({domain:'commerce',question:'denial fixture'})});
          const core=await fetch('/threads',{headers:{Authorization:'Bearer '+token}});
          return {api:api.status,core:core.status};
        },access[role]);
        if (role!=='manager' && denied.api!==403) throw Error('Backend role denial failed');
        if (denied.core!==403) throw Error('Core bypass denial failed');
        const goal=await page.evaluate(async token=>{
          const response=await fetch('/api/v1/goals',{headers:{Authorization:'Bearer '+token}});
          return (await response.json()).find(g=>g.domain==='commerce'&&g.confirmed);
        },access[role]);
        let answers=0;
        if (goal) {
          await page.getByRole('button').filter({hasText:goal.body.question}).first().click();
          answers=await page.evaluate(async ({token,id})=>{
            const response=await fetch('/api/v1/runs?goal_id='+id,{headers:{Authorization:'Bearer '+token}});
            return (await response.json()).filter(r=>r.status==='succeeded'&&r.body.operation==='analysis').length;
          },{token:access[role],id:goal.id});
          for (const view of ['Goals','Conversation','Review','History']) {
            await page.getByRole('button',{name:view,exact:true}).click();
            if (await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error(view+' overflows viewport');
            if (view==='Conversation'&&answers>=3) {
              await page.getByRole('button',{name:'Inspect calculation',exact:true}).first().click();
              await page.getByRole('heading',{name:'Source and calculation evidence',exact:true}).waitFor();
            }
            const image=path.join(out,role+'-'+width+'-'+view.toLowerCase()+'.png');
            await page.screenshot({path:image,fullPage:true});receipt.screenshots.push(image);
          }
        }
        await page.getByRole('button',{name:'Analysis',exact:true}).click();
        await page.keyboard.press('Tab');
        if (errors.length) throw Error(errors.join('; '));
        const image=path.join(out,role+'-'+width+'.png');
        await page.screenshot({path:image,fullPage:true});
        receipt.screenshots.push(image);receipt.checks.push({role,width,no_overflow:true,no_page_errors:true,backend_denial:true,populated_answers:answers});
        await page.close();
      }
    }
    receipt.status=receipt.checks.every(c=>c.populated_answers>=3)?'passed':'blocked';
    if(receipt.status==='blocked')receipt.reason='Role and source checks passed; three real answers are required for the populated journey.';
  } catch(e) {receipt.status='failed';receipt.error=e.message;process.exitCode=1;}
  finally {if(browser)await browser.close();fs.writeFileSync(path.join(out,'evidence.json'),JSON.stringify(receipt,null,2));console.log(JSON.stringify({status:receipt.status,error:receipt.error,evidence:path.join(out,'evidence.json')}));}
})();
