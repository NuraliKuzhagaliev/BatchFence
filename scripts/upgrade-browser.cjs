// Agent-operated synthetic UI acceptance, never independent user validation.
const {chromium,_electron:electron}=require('playwright'), fs=require('node:fs/promises'), path=require('node:path'), assert=require('node:assert/strict');
const base=process.env.BATCHFENCE_BASE_URL||'http://127.0.0.1:8793';
const out=process.env.BATCHFENCE_UPGRADE_REPORT_DIR||path.resolve('docs/release-0.2.0/upgrade-browser');
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const desktop=process.env.BATCHFENCE_TEST_EXE ? await electron.launch({executablePath:process.env.BATCHFENCE_TEST_EXE,env:{...process.env,BATCHFENCE_USER_DATA:path.resolve('work/upgrade-desktop-profile')}}):null;
 const browser=desktop?null:await chromium.launch({channel:'msedge',headless:true});
 const context=desktop?desktop.context():await browser.newContext({viewport:{width:1440,height:900},acceptDownloads:true,recordVideo:process.env.BATCHFENCE_RECORD?{dir:path.resolve('work/upgrade-media'),size:{width:1440,height:900}}:undefined});
 const page=desktop?await desktop.firstWindow():await context.newPage(),checks=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const click=name=>page.getByRole('button',{name,exact:true}).click();
 const tab=name=>page.getByRole('tab',{name,exact:false}).click();
 const shot=name=>page.screenshot({path:path.join(out,name+'.png'),fullPage:true});
 const units=async n=>{await page.locator('.comparison .required strong').filter({hasText:String(n)}).waitFor();};
 try{
  if(!desktop) await page.goto(base);await page.getByRole('button',{name:'Open example incident',exact:false}).click();
  await page.getByRole('region',{name:'Genealogy not yet evaluated'}).waitFor();checks.push('Unclassified genealogy visible before interpretation');await shot('01-preview');
  await page.getByLabel('Run mode',{exact:true}).selectOption('fixture');await click('Extract selected notice');
  await page.getByLabel('Disposition of SUP-A',{exact:true}).waitFor();assert.equal(await page.getByLabel('Disposition of SUP-A',{exact:true}).inputValue(),'unresolved');checks.push('Model candidate defaults unresolved');
  await require('./review-controls.cjs')(page,{affected:[],uncertain:['SUP-A'],resolved:false,note:'Agent test deliberately retains an unreviewed boundary.'});
  await click('Confirm scope & calculate');await units('1,200');await tab('Evidence requests');
  assert.equal(await page.getByRole('heading',{name:'Complete incident boundary',exact:true}).count(),1);
  assert.equal(await page.getByRole('heading',{name:'Receiving identity for FG-C',exact:true}).count(),1);
  assert.equal(await page.getByRole('heading',{name:/Receiving identity for FG-[ABDEF]/}).count(),0);
  checks.push('Shared boundary cause; only actual FG-C receiving gap');await shot('02-shared-boundary');
  await click('Review candidate facts');await require('./review-controls.cjs').fixture(page,['SUP-A']);await click('Confirm scope & calculate');await units('500');
  await click('Approve exact plan');await tab('Evidence requests');
  const b=page.locator('.hypothesis').filter({hasText:'FG-C: SUP-B only'});
  await b.getByRole('button',{name:'Simulate',exact:true}).click();await page.getByRole('heading',{name:'500 → 400 proposed units',exact:true}).waitFor();
  await click('Close simulation');await b.getByRole('button',{name:'Add to joint scenario'}).click();await b.getByRole('button',{name:'Add to joint scenario'}).click();await click('Recompute joint scenario');await page.getByRole('heading',{name:'500 → 400 proposed units'}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Apply holds',exact:true}).count(),1);checks.push('Standalone and duplicate joint simulation 500→400; approval preserved');await shot('03-simulation');
  await click('Add supplier v2');await click('Test stale approval');await page.getByRole('alert').filter({hasText:'stale'}).waitFor();checks.push('Changed evidence rejects prior approval');
  await click('Review current evidence');await require('./review-controls.cjs').fixture(page,['SUP-A','SUP-C']);await click('Confirm scope & calculate');await units('800');
  await tab('Revisions');await page.locator('.causal-pool.changed-path').filter({hasText:'FG-D'}).waitFor();assert((await page.locator('.causal-pool.changed-path').textContent()).includes('SUP-C → FG-D → O-104'));checks.push('Causal revision: SUP-C→FG-D→O-104, 300 units');
  await click('Before · historical');await shot('04-before');await click('After · current proposal');await shot('05-causal-after');
  await click('Approve exact plan');await click('Apply holds');await page.getByRole('heading',{name:'Holds applied. Evidence preserved.'}).waitFor();
  await tab('Evidence requests');await click('Complete example reply');
  await click('Interpret reply · Synthetic');await page.locator('.raw-reply').filter({hasText:'succeeded'}).waitFor();
  await page.getByLabel('Reply outcome',{exact:true}).selectOption('resolved');await page.getByLabel('Reviewed supplier identity',{exact:true}).selectOption('SUP-B');
  await page.getByLabel('This is a complete replacement of every parent record',{exact:true}).check();
  const quote='FG-C complete ancestry: SUP-B only. Supersedes LIN-3, LIN-4. Receipt REC-C-2 covers all 100 units; no other parent lots.';
  await page.getByLabel('Exact reply passage',{exact:true}).fill(quote);await page.getByLabel('Reply review explanation',{exact:true}).fill('Agent-operated synthetic review: the complete record explicitly supersedes both possible parent rows for all FG-C units.');
  await click('Preview reconciliation');await page.getByRole('heading',{name:'800 → 700 proposed units'}).waitFor();await shot('06-reply-preview');
  await page.getByLabel('I reviewed the exact reply and record identity',{exact:true}).check();await page.getByLabel('I reviewed every superseded parent and the complete replacement',{exact:true}).check();
  await click('Confirm reply & recalculate');await units('700');checks.push('Reviewed linked reply narrows proposal to 700; 800 applied units remain held');
  const state=await page.evaluate(async()=>{const id=localStorage.getItem('bf.case');return window.batchfence?window.batchfence.request('GET','/api/cases/'+id):(await fetch('/api/cases/'+id)).json();});
  assert.equal(state.stocks.filter(s=>s.status==='held').reduce((n,s)=>n+s.units,0),800);assert.equal(state.receipts.length,1);assert.equal(state.plan.status,'proposed');
  await tab('Verification');await click('Run boundary challenges');await page.locator('.challenge-result').last().waitFor();assert.equal(await page.locator('.challenge-result').count(),6);assert(!(await page.locator('.verification-panel').textContent()).includes('FAILED'));checks.push('Six executable synthetic boundary challenges pass');await shot('07-verification');
  await tab('Exposure');
  const metrics=[];
  for(const [width,height] of [[1366,768],[1440,900],[1920,1080],[390,844]]){
    await page.setViewportSize({width,height});await shot('viewport-'+width);
    const m=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));assert(m.scrollWidth<=m.width,JSON.stringify(m));metrics.push(m);
  }
  await page.setViewportSize({width:1440,height:900});await page.evaluate(()=>document.documentElement.style.zoom='2');await shot('zoom-200');
  const zoom=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));assert(zoom.scrollWidth<=zoom.width);checks.push('1366/1440/1920/mobile and 200% CSS zoom without horizontal page overflow');
  assert.deepEqual(errors,[]);
  const packet=await page.evaluate(async()=>{const id=localStorage.getItem('bf.case');return window.batchfence?window.batchfence.request('GET','/api/cases/'+id+'/export'):(await fetch('/api/cases/'+id+'/export')).json();});await fs.writeFile(path.join(out,'upgraded-packet.json'),JSON.stringify(packet,null,2));
  await fs.writeFile(path.join(out,'results.json'),JSON.stringify({at:new Date().toISOString(),base,provenance:'Synthetic; agent-operated review',checks,metrics,zoom,page_errors:errors},null,2));console.log(JSON.stringify({checks,metrics,zoom},null,2));
 }catch(e){await shot('failure');await fs.writeFile(path.join(out,'failure.json'),JSON.stringify({at:new Date().toISOString(),message:e.message,checks,errors},null,2));throw e;}finally{if(desktop)await desktop.close();else {await context.close();await browser.close();}}
})().catch(e=>{console.error(e);process.exitCode=1;});
