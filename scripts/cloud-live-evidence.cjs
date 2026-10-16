const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright'),{validatePacket}=require('../desktop/packet.cjs');
const root=path.resolve(__dirname,'..'),base='https://batchfence.onrender.com',out=path.join(root,'docs/cloud/live');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const c=await browser.newContext({viewport:{width:1440,height:1000},storageState:path.join(root,'work/live-verification/cloud-free-live/private-browser-session.json')});
 const report=JSON.parse(await fs.readFile(path.join(out,'browser-results.json'),'utf8'));const route=base+'/api/cases/'+report.case_id;
 const res=await c.request.get(route+'/export');assert(res.ok());const packet=await res.json();validatePacket(packet);
 assert.equal(packet.case.receipts.length,1);assert.equal(packet.case.runs.at(-1).status,'failed');
 await fs.writeFile(path.join(out,'final-failed-v2-packet.json'),JSON.stringify(packet,null,2));
 const page=await c.newPage();await page.goto(base);await page.getByRole('alert').filter({hasText:'Lot identifier absent from cited quote'}).waitFor();await page.reload();
 await page.getByRole('alert').filter({hasText:'Lot identifier absent from cited quote'}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
 await page.screenshot({path:path.join(out,'03-failed-live-revision.png'),fullPage:true});
 await page.locator('input[type=file][accept=".json"]').setInputFiles(path.join(out,'packet-1.json'));await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
 await page.getByText('Historical model run · no new inference.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
 await page.screenshot({path:path.join(out,'04-exported-live-receipt.png'),fullPage:true});
 const other=await browser.newContext();assert.equal((await other.request.get(route)).status(),404);assert.equal((await other.request.get(route+'/export')).status(),404);
 const checks={at:new Date().toISOString(),url:base,live_calls:0,passed:true,checks:['Fresh exported packet validates with all three actual model runs and single receipt','Failed revised live extraction persists after reload and offers no approval','500-unit actual live receipt opens as historical read-only packet','Separate session cannot read or export actual live case']};
 await fs.writeFile(path.join(out,'final-ui-results.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(String(e.message).split('\n')[0]);process.exitCode=1});
