// Read existing evidence only. No model calls; private cookies never printed.
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright'),{validatePacket}=require('../desktop/packet.cjs');
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:8787';
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true});
 try {
  const saved=JSON.parse(await fs.readFile(path.join(root,'work/live-verification/ambiguity-fix-live/private-browser-session.json'),'utf8'));
  const c=await b.newContext({viewport:{width:1920,height:1080}});await c.addCookies(saved.cookies);
  const packet=JSON.parse(await fs.readFile(path.join(root,'docs/ambiguity-fix/clear-live/packet-2.json'),'utf8'));
  const r=await c.request.get(base+'/api/cases/'+packet.case.id+'/export');assert(r.ok());const fresh=await r.json();validatePacket(fresh);
  assert.deepEqual(fresh.case.receipts,packet.case.receipts);assert.deepEqual(fresh.case.runs,packet.case.runs);
  const page=await c.newPage();await page.goto(base);
  await page.evaluate(id=>localStorage.setItem('bf.case',id),packet.case.id);await page.reload();
  await page.locator('.comparison .required strong').filter({hasText:'800'}).waitFor();
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(root,'submission/cover-0.1.1.png')});
  // Same packet also passes the browser's independent hash/shape check.
  await page.locator('input[type=file][accept=".json"]').setInputFiles(path.join(root,'docs/ambiguity-fix/clear-live/packet-2.json'));
  await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('Run mode',{exact:true}).inputValue(),'live');
  await page.getByText('Historical model run · no new inference.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
  const ambiguity=JSON.parse(await fs.readFile(path.join(root,'docs/ambiguity-fix/live-ambiguity.json'),'utf8'));
  const cookie=JSON.parse(await fs.readFile(path.join(root,'work/ambiguity-live-session.json'),'utf8'));
  const fail=await b.newContext();await fail.addCookies(Object.entries(cookie).map(([name,value])=>({name,value,url:base})));
  const p=await fail.newPage();await p.goto(base);await p.evaluate(id=>localStorage.setItem('bf.case',id),ambiguity.cases[1].case_id);await p.reload();
  await p.getByRole('alert').filter({hasText:'Lot identifier absent from cited quote'}).waitFor();
  assert.equal(await p.getByRole('button',{name:'Review candidate facts',exact:false}).count(),0);
  assert.equal(await p.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
  const report={at:new Date().toISOString(),passed:true,new_inference_calls:0,
    checks:['Fresh server export hash accepted by desktop validator; same model runs and receipts',
      'Reissued packet accepted by browser; offline approval absent',
      'Failed live extraction error persists after reload; candidate review and approval absent'],
    cover:'Actual live-case 800-unit view at 1920x1080, synthetic data; no new inference for screenshot'};
  await fs.writeFile(path.join(root,'docs/ambiguity-fix/final-ui-results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 } finally {await b.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
