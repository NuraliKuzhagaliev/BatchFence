// Capture the actual owned case after a fresh request/review. No new inference.
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path');
const stage=process.argv[2],root=path.resolve(__dirname,'..');
(async()=>{
 const privateState=JSON.parse(await fs.readFile(path.join(root,'work/upgrade-live-session.json'),'utf8'));
 const out=path.join(root,'docs/release-0.2.0/live');
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 await context.addCookies(Object.entries(privateState.cookies).map(([name,value])=>({name,value,url:'https://batchfence.onrender.com'})));
 const page=await context.newPage();
 await page.goto('https://batchfence.onrender.com');await page.evaluate(id=>localStorage.setItem('bf.case',id),privateState.case_id);await page.reload();
 await page.locator('.comparison').waitFor();
 await page.screenshot({path:path.join(out,stage+'-exposure.png'),fullPage:false});
 if(stage==='review2'){
  await page.getByRole('tab',{name:'Revisions',exact:true}).click();await page.locator('.causal-pool.changed-path').waitFor();
  await page.locator('.timeline').evaluate(el=>el.scrollTop=370);await page.screenshot({path:path.join(out,'fresh-causal-revision.png'),fullPage:false});
 }
 await page.getByRole('tab',{name:'Verification',exact:true}).click();await page.screenshot({path:path.join(out,stage+'-verification.png'),fullPage:false});
 if(stage==='final'){await page.getByRole('tab',{name:'Exposure',exact:false}).click();await page.setViewportSize({width:1920,height:1080});await page.screenshot({path:path.join(root,'submission/cover-0.2.0.png'),fullPage:false});}
 await context.close();await browser.close();console.log('Captured actual '+stage+' state; no inference calls.');
})().catch(e=>{console.error(e.message);process.exitCode=1;});
