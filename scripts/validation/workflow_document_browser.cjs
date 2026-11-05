const {chromium}=require('../../apps/web/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
(async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(process.env.S27_URL,{waitUntil:'domcontentloaded'});
    await page.getByLabel('Access credential',{exact:true}).fill(process.env.S27_TOKEN);
    await page.getByRole('button',{name:'Open workspace',exact:true}).click();
    await page.getByRole('navigation',{name:'Saved goals'}).getByRole('button').filter({hasText:process.env.S27_GOAL}).click();
    const citations=page.getByRole('region',{name:'Supporting document passages'});
    await citations.getByRole('heading',{name:'InvoiceNo · UCI Online Retail field guide',exact:true}).waitFor();
    await citations.getByRole('heading',{name:'UnitPrice · UCI Online Retail field guide',exact:true}).waitFor();
    await page.screenshot({path:path.join(process.env.S27_OUTPUT,'document-answer.png'),fullPage:true});
    await page.getByRole('button',{name:'Sources',exact:true}).click();
    const panel=page.getByRole('region',{name:'Source documents'});
    await panel.getByRole('heading',{name:'UCI Online Retail field guide',exact:true}).waitFor();
    const downloading=page.waitForEvent('download');
    await panel.getByRole('button',{name:'Download original UCI Online Retail field guide',exact:true}).click();
    const download=await downloading;
    const bytes=fs.readFileSync(await download.path());
    if(crypto.createHash('sha256').update(bytes).digest('hex')!==process.env.S27_DOCUMENT_SHA256) throw new Error('Original bytes changed');
    await page.setViewportSize({width:390,height:844});
    if(await panel.evaluate(element=>element.scrollWidth>element.clientWidth||element.getBoundingClientRect().right>innerWidth)) throw new Error('Document panel overflows narrow viewport');
    await page.screenshot({path:path.join(process.env.S27_OUTPUT,'document-sources-mobile.png'),fullPage:true});
    if(errors.length) throw new Error(errors.join('\n'));
    fs.writeFileSync(path.join(process.env.S27_OUTPUT,'document-browser.json'),JSON.stringify({status:'passed',original_bytes:bytes.length,cited_fields:['InvoiceNo','UnitPrice'],errors},null,2));
    console.log('PASS: retained quotations beside the answer, exact original download, desktop and narrow views.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
