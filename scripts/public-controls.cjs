const {chromium}=require('playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.BATCHFENCE_BASE_URL||'https://127.0.0.1:8790';
const out=path.join(root,'docs/cloud');
async function main(){
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const local=new URL(base).hostname==='127.0.0.1';
 const context=await browser.newContext({viewport:{width:1440,height:1000},ignoreHTTPSErrors:local});
 const page=await context.newPage();const errors=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  let healthy=false;
  for(let attempt=0;attempt<15;attempt++){
    try{healthy=(await context.request.get(base+'/api/health')).ok();}catch{}
    if(healthy)break;
    await new Promise(r=>setTimeout(r,1000));
  }
  assert(healthy,'Health must be ready before browser verification');
  await page.goto(base+'/workspace/review');
  await page.getByRole('button',{name:'Load synthetic incident',exact:false}).waitFor();
  await page.reload();
  await page.getByRole('button',{name:'Open recorded AMD packet',exact:false}).waitFor();
  checks.push('Initial loading and internal-route refresh');
  assert.equal((await context.request.get(base+'/api/missing')).status(),404);
  for(const src of await page.locator('script[src],link[rel=stylesheet]').evaluateAll(es=>es.map(e=>e.src||e.href))){
   assert.equal((await context.request.get(src)).status(),200);
  }
  checks.push('Built assets and API 404');
  await page.getByRole('button',{name:'Open recorded AMD packet',exact:false}).click();
  await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
  assert.equal(await page.getByLabel('Run mode',{exact:true}).inputValue(),'live');
  await page.getByText(/Replay · historical live AMD response/).waitFor();
  await page.screenshot({path:path.join(out,local?'local-replay.png':'public-replay.png'),fullPage:true});
  checks.push('Historical AMD replay labeled; no approval/execution authority');
  await page.getByRole('button',{name:'Return to live desk',exact:true}).click();
  await page.getByRole('button',{name:'Load synthetic incident',exact:false}).click();
  await page.getByLabel('Run mode',{exact:true}).selectOption('live');
  await page.getByLabel('Demonstration access key',{exact:true}).fill('deliberately-invalid-test-value');
  const deniedPending=page.waitForResponse(r=>r.url().endsWith('/analyze')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Extract selected notice',exact:true}).click();
  const denied=await deniedPending; const detail=(await denied.json()).detail;
  assert([403,503].includes(denied.status()));
  assert(['LIVE_PROTECTED','LIVE_UNAVAILABLE'].includes(detail.code));
  await page.getByRole('alert').filter({hasText:detail.message}).waitFor();
  const health=await (await context.request.get(base+'/api/health')).json();
  if(health.storage_mode==='ephemeral') await page.getByRole('note').filter({hasText:'Free demo · temporary storage'}).waitFor();
  const id=await page.evaluate(()=>localStorage.getItem('bf.case'));
  const state=await (await context.request.get(base+'/api/cases/'+id)).json();
  assert.equal(state.runs.length,0);
  const other=await browser.newContext({ignoreHTTPSErrors:local});
  assert.equal((await other.request.get(base+'/api/cases/'+id)).status(),404);
  assert.equal((await other.request.get(base+'/api/cases/'+id+'/export')).status(),404);
  checks.push('Live access denied before provider reservation; second browser session cannot read case or receipt');
  assert.equal(await page.evaluate(()=>localStorage.getItem('LIVE_DEMO_TOKEN')),null);
  await page.screenshot({path:path.join(out,local?'local-protected-live.png':'public-protected-live.png'),fullPage:true});
  checks.push('Protected-live error remains usable and access key not persisted');
  assert.deepEqual(errors,[]);
  const report={at:new Date().toISOString(),url:base,environment:local?'local HTTPS simulation':'public HTTPS',live_calls:0,live_access_denial:{status:denied.status(),code:detail.code},checks,errors};
  await fs.writeFile(path.join(out,local?'local-public-controls.json':'public-controls.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
 } finally {await browser.close();}
}
main().catch(e=>{console.error(String(e.message).split('\n')[0]);process.exitCode=1;});
