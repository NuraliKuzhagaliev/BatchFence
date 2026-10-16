const { _electron: electron, chromium } = require('playwright');
const fs = require('node:fs/promises'), path = require('node:path'), assert = require('node:assert/strict');
const root=path.resolve(__dirname,'..'), out=path.join(root,'docs/release-0.1.2');
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const checks=[], errors=[];
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.goto(process.env.BATCHFENCE_BASE_URL||'http://127.0.0.1:8792');
  await page.getByRole('button',{name:'Open example incident',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Open web app',exact:true}).count(),0);
  assert.equal(await page.getByRole('link',{name:/Open web app/}).count(),0);
  const link=page.getByRole('link',{name:'Download for Windows',exact:true});
  assert.equal(await link.getAttribute('href'),'https://github.com/NuraliKuzhagaliev/BatchFence/releases/download/v0.1.2/BatchFence-0.1.2-win-x64-setup.exe');
  const body=await page.locator('body').innerText();
  for(const text of ['SANDBOX','Human review','Free demo','Public demo','BatchFence 0.1.1','public download pending']) assert(!body.includes(text),text);
  await page.screenshot({path:path.join(out,'web-landing.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await link.isVisible());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'web-mobile.png'),fullPage:true});
  checks.push('Web: download action only, retired labels absent, mobile layout within viewport');
 }finally{await browser.close()}
 const app=await electron.launch({executablePath:path.join(root,'work/installed-0.1.2/BatchFence.exe'),env:{...process.env,BATCHFENCE_USER_DATA:path.join(root,'work/desktop-distribution-012')},timeout:30000});
 try{
  const page=await app.firstWindow(); page.on('pageerror',e=>errors.push(e.message));
  await page.getByRole('button',{name:'Open example incident',exact:true}).waitFor();
  await page.locator('button:not([disabled])').filter({hasText:'Open example incident'}).waitFor();
  await page.getByText('Backend connected',{exact:true}).waitFor();
  assert.equal(await page.getByRole('link',{name:'Download for Windows',exact:true}).count(),0);
  await app.evaluate(({shell})=>{global.testOpened=[];shell.openExternal=async url=>{global.testOpened.push(url)}});
  await page.getByRole('button',{name:'Open web app',exact:true}).click();
  assert.deepEqual(await app.evaluate(()=>global.testOpened),['https://batchfence.onrender.com']);
  await page.locator('button:not([disabled])').filter({hasText:'Open example incident'}).waitFor();
  await page.screenshot({path:path.join(out,'desktop-landing.png'),fullPage:true});
  checks.push('Installed desktop: no download, Open web app reaches fixed HTTPS shell target (launch intercepted)');
  await page.getByRole('button',{name:'Open recorded AMD packet',exact:true}).click();
  await page.getByText('Offline evidence review · historical snapshot',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Approve exact plan',exact:true}).count(),0);
  await page.getByRole('button',{name:'Return to live desk',exact:true}).click();
  checks.push('Installed desktop reads hosted historical AMD packet through restricted transport');
  await page.getByRole('button',{name:'Open example incident',exact:true}).click();
  await page.getByLabel('Run mode',{exact:true}).selectOption('live');
  await page.getByLabel('Live access key',{exact:true}).fill('invalid-verification-token');
  await page.getByRole('button',{name:'Extract selected notice',exact:true}).click();
  await page.getByRole('alert').waitFor();
  assert((await page.getByRole('alert').textContent()).includes('access key'));
  const state=()=>page.evaluate(async()=>window.batchfence.request('GET','/api/cases/'+localStorage.getItem('bf.case')));
  assert.equal((await state()).runs.length,0);
  const security=await page.evaluate(async()=>{
   const bridge=window.batchfence, denied=[];
   for(const [method,route,body,token] of [['GET','https://example.com/'],['POST','/api/replay',{}],['GET','/api/health',undefined,'bad\r\nheader'],['GET','/api/health',undefined,'x'.repeat(201)]]){
    try{await bridge.request(method,route,body,token);denied.push(false)}catch{denied.push(true)}
   }
   return {denied,node:typeof window.require,rawIpc:typeof bridge.ipcRenderer};
  });
  assert(security.denied.every(Boolean));assert.equal(security.node,'undefined');assert.equal(security.rawIpc,'undefined');
  checks.push('Installed desktop rejects wrong live key before inference; restricted URLs, methods and malformed tokens denied');
  let live=null;
  if(process.env.BATCHFENCE_VERIFY_LIVE==='true'){
   const env=await fs.readFile(path.join(root,'work/cloud-demo.env'),'utf8');
   const token=env.split(/\r?\n/).find(x=>x.startsWith('LIVE_DEMO_TOKEN=')).slice('LIVE_DEMO_TOKEN='.length).trim();
   await page.getByLabel('Live access key',{exact:true}).fill(token);
   await page.getByRole('button',{name:'Extract selected notice',exact:true}).click();
   await page.getByRole('heading',{name:'Confirm the affected supplier lots.',exact:true}).waitFor({timeout:65000});
   const current=await state(); const run=current.runs.at(-1);
   assert.equal(run.mode,'live');assert.equal(run.status,'succeeded');
   assert.equal(current.plan,null);assert.equal(current.receipts.length,0);
   const exported=await page.evaluate(async()=>window.batchfence.request('GET','/api/cases/'+localStorage.getItem('bf.case')+'/export'));
   await fs.writeFile(path.join(out,'desktop-live-candidates.json'),JSON.stringify(exported,null,2));
   await page.screenshot({path:path.join(out,'desktop-live-candidates.png'),fullPage:true});
   live={mode:run.mode,status:run.status,model_id:run.model_id,elapsed_ms:run.elapsed_ms,at:run.at,review:'Not performed; actual response drives unresolved candidate facts only',receipt:false};
   checks.push('Installed desktop forwards private access token; actual cloud AMD response populates unresolved source-backed candidates');
   console.log(JSON.stringify({live,facts:run.output.facts.map(f=>({lot_id:f.lot_id,affected:f.affected})),qualifiers:run.output.qualifiers}));
  }
  assert.deepEqual(errors,[]);
  await fs.writeFile(path.join(out,live?'distribution-results.json':'distribution-controls-results.json'),JSON.stringify({at:new Date().toISOString(),checks,errors,security,live,native_dialogs:'Not exercised by this check; other installed tests use dialog stubs.'},null,2));
  console.log(JSON.stringify({checks:checks.length,errors}));
 }finally{await app.close()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
