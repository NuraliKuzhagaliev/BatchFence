// Finite packaged-client acceptance using a local fixture backend; no provider calls.
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {_electron,chromium}=require('playwright');
const R=path.resolve(__dirname,'..'),base='http://127.0.0.1:8816';
(async()=>{
 const out=path.join(R,'work/lot-citation-fix');await fs.mkdir(out,{recursive:true});
 const server=spawn(process.env.BATCHFENCE_PYTHON||'python',['-m','uvicorn','backend.app:app','--host','127.0.0.1','--port','8816'],{cwd:R,env:{...process.env,INFERENCE_MODE:'fixture',DATABASE_PATH:path.join(out,'client.sqlite3'),SOURCE_STORAGE_PATH:path.join(out,'sources')},stdio:['ignore','pipe','pipe']});
 let app,browser,log='';server.stderr.on('data',b=>log+=b.toString());
 const checks=[],errors=[];
 try{
  let ready=false;for(let i=0;i<100;i++){try{if((await fetch(base+'/api/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,200));}assert(ready,log.slice(-1000));
  let page;
  if(process.env.BATCHFENCE_CLIENT_EXE){
   app=await _electron.launch({executablePath:process.env.BATCHFENCE_CLIENT_EXE,env:{...process.env,BATCHFENCE_BACKEND_ORIGIN:base,BATCHFENCE_USER_DATA:path.join(out,'client-user-data')}});page=await app.firstWindow();
  }else{browser=await chromium.launch({headless:true});page=await browser.newPage({viewport:{width:1440,height:900}});await page.goto(base);}
  page.on('pageerror',e=>errors.push(e.message));
  await page.getByRole('button',{name:'Open example incident',exact:false}).click();
  await page.getByLabel('Run mode',{exact:true}).selectOption('fixture');
  for(const e of ['focus','online'])await page.evaluate(e=>window.dispatchEvent(new Event(e)),e);
  assert.equal(await page.getByLabel('Run mode',{exact:true}).inputValue(),'fixture');checks.push('Explicit synthetic route preserved across focus and reconnect');
  const state=await page.evaluate(async()=>{
   const id=localStorage.getItem('bf.case');return window.batchfence?window.batchfence.request('GET','/api/cases/'+id):fetch('/api/cases/'+id).then(r=>r.json());
  });assert(state.id);checks.push('Client transport loads owned case through actual backend');
  await page.getByRole('button',{name:'Knowledge',exact:true}).filter({visible:true}).first().click();
  await page.getByLabel('Run mode',{exact:true}).selectOption('live');
  await page.getByLabel('Live knowledge evidence route',{exact:true}).selectOption('rag');
  assert.equal(await page.getByLabel('Live knowledge evidence route',{exact:true}).inputValue(),'rag');
  await page.getByText('Set up an isolated Evolus library · administrator',{exact:true}).click();
  await page.getByLabel('Library type',{exact:true}).selectOption('Rag');
  await page.getByLabel('Existing isolated RAG agent ID (explicit reconciliation only)',{exact:true}).fill('diagnostic-agent-not-submitted');
  checks.push('RAG route and explicit existing-agent reconciliation visible and selectable');
  assert(await page.getByText(/provider-native citation annotations are not implied/).count());
  checks.push('Application source-citation origin and missing-proof rejection disclosed');
  const after=await page.evaluate(async id=>window.batchfence?window.batchfence.request('GET','/api/cases/'+id):fetch('/api/cases/'+id).then(r=>r.json()),state.id);
  assert.deepEqual(after.receipts,state.receipts);assert.deepEqual(after.plan,state.plan);checks.push('Changing retrieval route creates no plan, receipt or inventory action');
  await page.screenshot({path:path.join(out,'client-knowledge.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  const report={passed:true,surface:app?'Windows packaged Electron':'Web Chromium',checks,inference_calls:0,cash_spent:0,native_dialogs:'Not exercised; no native-dialog or independent human acceptance claim',fresh_rag_application_acceptance:'Not exercised: no private live-access token or provider configuration in the build runner',page_errors:errors};
  await fs.writeFile(path.join(out,'client-results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{if(app)await app.close();if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
