const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright'),{validatePacket}=require('../desktop/packet.cjs');
const root=path.resolve(__dirname,'..'),base='https://batchfence.onrender.com',out=path.join(root,'docs/cloud',process.env.BATCHFENCE_CLOUD_EVIDENCE||'live');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const c=await browser.newContext({viewport:{width:1440,height:1000},storageState:path.join(root,'work/live-verification',process.env.BATCHFENCE_CLOUD_SESSION||'cloud-free-live','private-browser-session.json')});
 const report=JSON.parse(await fs.readFile(path.join(out,'browser-results.json'),'utf8'));const route=base+'/api/cases/'+report.case_id;
 const res=await c.request.get(route+'/export');assert(res.ok());const packet=await res.json();validatePacket(packet);
 const completed=report.status==='passed';assert.equal(packet.case.receipts.length,completed?2:1);assert.equal(packet.case.runs.at(-1).status,completed?'succeeded':'failed');
 await fs.writeFile(path.join(out,'final-public-packet.json'),JSON.stringify(packet,null,2));
 const page=await c.newPage();await page.goto(base);await page.reload();
 if(completed){await page.locator('.comparison .required strong').filter({hasText:'800'}).waitFor();}
 else {await page.getByRole('alert').filter({hasText:'Lot identifier absent from cited quote'}).waitFor();}
 assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
 await page.screenshot({path:path.join(out,'03-final-live-state.png'),fullPage:true});
 await page.locator('input[type=file][accept=".json"]').setInputFiles(path.join(out,completed?'packet-2.json':'packet-1.json'));await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
 await page.getByText('Historical model run · no new inference.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
 await page.screenshot({path:path.join(out,'04-exported-live-receipt.png'),fullPage:true});
 const other=await browser.newContext();assert.equal((await other.request.get(route)).status(),404);assert.equal((await other.request.get(route+'/export')).status(),404);
 const checks={at:new Date().toISOString(),url:base,live_calls:0,passed:true,runs:packet.case.runs.length,receipts:packet.case.receipts.length,checks:['Fresh exported packet validates with actual model runs and receipts',completed?'800-unit applied state persists after refresh':'Failed revised live extraction persists after reload and offers no approval','Actual live receipt opens as historical read-only packet','Separate session cannot read or export actual live case']};
 await fs.writeFile(path.join(out,'final-ui-results.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(String(e.message).split('\n')[0]);process.exitCode=1});
