// Read retained, genuine model outputs. No inference or write requests while filming.
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs/continuation/live/ui'),media=path.join(root,'work/continuation-media');
(async()=>{
 await fs.mkdir(out,{recursive:true});await fs.mkdir(media,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true}),reports=[];
 for(const [name,file,tabs] of [['evolus','evolus-flow-v2-session.json',['Sources','Recovery']],['gemma','flow-session.json',['Sources','Requests','Recovery','Revisions','Handover']]]){
  const state=JSON.parse(await fs.readFile(path.join(root,'work/continuation',file),'utf8'));
  const context=await browser.newContext({viewport:{width:1366,height:900},recordVideo:{dir:media,size:{width:1366,height:900}}});
  await context.addCookies(Object.entries(state.cookies).map(([name,value])=>({name,value,url:'http://127.0.0.1:8802'})));const page=await context.newPage(),writes=[],errors=[];
  page.on('request',r=>{if(!['GET','HEAD'].includes(r.method()))writes.push(r.method()+' '+new URL(r.url()).pathname)});page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8802');await page.evaluate(id=>localStorage.setItem('bf.case',id),state.case_id);await page.reload();
  await page.getByRole('button',{name:'Incidents',exact:true}).click();
  for(const tab of tabs){await page.getByRole('tab',{name:tab==='Sources'?'Sources & intake':tab==='Requests'?'Evidence requests':tab,exact:tab!=='Requests'}).click();await page.waitForTimeout(700);const target=page.locator(tab==='Sources'?'.assist-proposal':tab==='Handover'?'.handover-card':tab==='Recovery'?'.assist-conditions':tab==='Requests'?'.assist-requests':'.assist-changes').first();if(await target.count())await target.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,name+'-'+tab.toLowerCase()+'.png')});await page.waitForTimeout(3500);}
  const response=await context.request.get('http://127.0.0.1:8802/api/cases/'+state.case_id);assert.equal(response.status(),200);const c=await response.json();assert.equal(c.receipts.length,2);const applied=c.quantities?.applied_hold_units??c.plan.result.hold_units;assert.equal(applied,name==='evolus'?800:700);
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);const video=page.video();await context.close();await video.saveAs(path.join(media,name+'.webm'));
  reports.push({profile:name,case_id:state.case_id,applied,quantity_origin:c.quantities?'hold ledger':'executed containment plan (case has no recovery)',receipts:c.receipts.length,tabs,writes,errors});
 }
 await browser.close();await fs.writeFile(path.join(out,'capture.json'),JSON.stringify({at:new Date().toISOString(),provenance:'Stored genuine AMD/Evolus results. Synthetic sources and inventory. Agent-operated reviews. Read-only capture, no inference.',reports},null,2));console.log(JSON.stringify(reports));
})().catch(e=>{console.error(e.message);process.exitCode=1});
