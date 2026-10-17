// Read-only capture of genuine persisted responses. No inference during recording.
const {chromium}=require('playwright'),fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs/enterprise/live/final-ui');
(async()=>{
 await fs.mkdir(out,{recursive:true});const browser=await chromium.launch({channel:'msedge',headless:true});const reports=[];
 for(const profile of ['frozen','receiving-v2']){
  const frozen=profile==='frozen',base='http://127.0.0.1:'+(frozen?8797:8796);
  const state=JSON.parse(await fs.readFile(path.join(root,'work',frozen?'enterprise-live-frozen':'enterprise-live-v2','private.json'),'utf8'));
  const context=await browser.newContext({viewport:{width:1366,height:900},recordVideo:{dir:path.join(root,'work/enterprise-final-media'),size:{width:1366,height:900}}});
  const login=await context.request.post(base+'/api/auth/login',{data:{username:frozen?'frozen-reviewer':'fresh-reviewer',password:state.password,org:frozen?'frozen':'liveeval',site:'synthetic'}});assert.equal(login.status(),200);
  const page=await context.newPage(),writes=[],errors=[];page.on('request',r=>{if(r.method()==='POST')writes.push(new URL(r.url()).pathname)});page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.evaluate(id=>localStorage.setItem('bf.case',id),state.case_id);await page.reload();
  if(frozen){
   await page.getByRole('button',{name:'Signals',exact:true}).click();
   const heading=page.getByRole('heading',{name:'Unreviewed explanation · live · succeeded',exact:true});await heading.waitFor();
   const card=page.locator('article.module-card').filter({has:heading});
   assert((await card.innerText()).includes('SHIFT-005'));assert((await card.innerText()).includes('BASE-001 through BASE-020'));
   assert((await card.innerText()).includes('Matches the current frozen chart'));
   await page.locator('.control-chart').screenshot({path:path.join(out,'signal-chart.png')});
   await card.scrollIntoViewIfNeeded();await page.waitForTimeout(5000);await card.screenshot({path:path.join(out,'signal-explanation.png')});
   await card.getByText('Actual inference provenance and raw output',{exact:true}).click();
   assert((await card.innerText()).includes('8474390ed7b6425196010a2eee945349'));
   await page.screenshot({path:path.join(out,'signal-provenance.png')});await page.waitForTimeout(5000);
   await page.reload();await page.getByRole('button',{name:'Signals',exact:true}).click();await heading.waitFor();
   assert((await card.innerText()).includes('SHIFT-005'));
  }else{
   await page.getByRole('button',{name:'Overview',exact:true}).click();await page.getByRole('heading',{name:'One evidence chain. Four connected decisions.',exact:true}).waitFor();
   await page.locator('.quantity-strip').last().screenshot({path:path.join(out,'recovery-quantities.png')});await page.screenshot({path:path.join(out,'receiving-overview.png')});await page.waitForTimeout(5000);
   await page.getByRole('button',{name:'Incidents',exact:true}).click();await page.getByRole('tab',{name:'Recovery',exact:true}).click();await page.getByRole('heading',{name:'Recovery proposal',exact:true}).waitFor();
   await page.getByText('Recovery receipts (separate from original containment receipts)',{exact:true}).click();await page.getByText('Recovery receipts (separate from original containment receipts)',{exact:true}).scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(out,'typed-recovery-receipt.png')});await page.waitForTimeout(5000);
   const response=await context.request.get(base+'/api/cases/'+state.case_id);const c=await response.json();assert.equal(c.quantities.confirmed_recovery_units,100);assert.equal(c.quantities.applied_hold_units,700);assert.equal(c.receipts.length,2);assert.equal(c.recovery_receipts.length,1);
  }
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);const health=await(await context.request.get(base+'/api/health')).json();
  reports.push({profile,version:health.version,writes,errors,checks:frozen?'Actual v3 AMD response survives page reload, exact request provenance and chart shown':'Actual v2 typed draft workflow: 700 applied,100 confirmed,two original receipts plus one recovery receipt'});
  const video=page.video();await context.close();await video.saveAs(path.join(root,'work/enterprise-final-media',profile+'.webm'));
 }
 await browser.close();await fs.writeFile(path.join(out,'capture.json'),JSON.stringify({at:new Date().toISOString(),provenance:'Actual read-only display of retained fresh AMD outputs. Synthetic sources; agent-operated review. No inference during capture.',reports},null,2));console.log(JSON.stringify(reports));
})().catch(e=>{console.error(e.message);process.exit(1)});
