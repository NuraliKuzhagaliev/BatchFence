// Explicit one-shot deployed acceptance; no owner/provider credentials loaded.
const {chromium}=require('playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs/judge-access/public'),privateDir=path.join(root,'work/judge-access');
async function main(){
  assert.equal(process.env.BATCHFENCE_VISITOR_LIVE,'true','Fresh inference requires explicit test activation');
  const attempt=process.env.BATCHFENCE_VISITOR_ATTEMPT||'1';assert(['1','2','3'].includes(attempt),'Finite plan: initial failure, timeout retest, one source-only validation-fix verification');
  const base='https://batchfence.onrender.com',checks=[],errors=[],modelPosts=[];
  await fs.mkdir(out,{recursive:true});await fs.mkdir(privateDir,{recursive:true});
  const browserTmp=path.join(privateDir,'browser-tmp');await fs.mkdir(browserTmp,{recursive:true});
  process.env.TEMP=browserTmp;process.env.TMP=browserTmp;
  const browser=await chromium.launch({channel:'chrome',headless:true,downloadsPath:privateDir});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  const other=await browser.newContext({viewport:{width:390,height:844}});
  const page=await context.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{
    if(r.url().startsWith(base+'/api/')){
      assert(!r.headers()['x-bf-demo-token']&&!r.headers()['authorization'],'No owner or provider token may be sent');
      if(r.method()==='POST'&&r.url().endsWith('/visitor-analysis'))modelPosts.push({url:r.url(),body:r.postDataJSON()});
    }
  });
  try{
    assert.equal((await context.storageState()).cookies.length,0);
    await page.goto(base,{waitUntil:'networkidle'});
    const health=await (await context.request.get(base+'/api/health')).json();
    assert(process.env.BATCHFENCE_EXPECTED_COMMIT,'Require an exact deployed commit before fresh inference');
    assert.equal(health.commit,process.env.BATCHFENCE_EXPECTED_COMMIT);
    assert(health.visitor_review_enabled);assert.equal(health.version,'0.4.0-rc.7');
    assert.deepEqual(await (await context.request.get(base+'/api/cases')).json(),[]);
    await page.getByRole('button',{name:'Analyze your document',exact:true}).click();
    await page.getByRole('heading',{name:'Bring your own evidence.',exact:true}).waitFor();
    const caseId=(await (await context.request.get(base+'/api/cases')).json())[0].id;
    const route=base+'/api/cases/'+caseId;
    const empty=await (await context.request.get(route)).json();
    assert.deepEqual(empty.stocks,[]);assert.deepEqual(empty.edges,[]);assert.deepEqual(empty.documents,[]);
    checks.push('Clean visitor session without owner token; editable blank case has no sample/private inventory');
    const upload=async filename=>{
      const response=page.waitForResponse(r=>r.url()===route+'/documents'&&r.request().method()==='POST');
      await page.locator('.visitor-review input[type=file]').setInputFiles(path.join(root,'docs/judge-access/inputs',filename));
      const r=await response;assert.equal(r.status(),200,await r.text());
      await page.getByLabel('Uploaded original',{exact:true}).selectOption({label:filename});
    };
    await upload('supplier-quality-helio.pdf');
    const uploaded=await (await context.request.get(route)).json();
    const inputHash=createHash('sha256').update(await fs.readFile(path.join(root,'docs/judge-access/inputs/supplier-quality-helio.pdf'))).digest('hex');
    assert.equal(uploaded.documents[0].original_hash,inputHash);assert.equal(uploaded.documents[0].synthetic,false);
    await page.getByRole('img',{name:'Original PDF page 1 of supplier-quality-helio.pdf',exact:true}).waitFor({state:'visible',timeout:30000});
    await context.storageState({path:path.join(privateDir,'public-session-'+attempt+'.json')});
    await fs.writeFile(path.join(privateDir,'fresh-started'+(attempt==='1'?'':'-'+attempt)+'.json'),JSON.stringify({at:new Date().toISOString(),caseId,planned_model_calls:1}),{flag:'wx'});
    await page.getByRole('checkbox',{name:/I may share this nonsensitive document/}).check();
    const pending=page.waitForResponse(r=>r.url()===route+'/visitor-analysis'&&r.request().method()==='POST',{timeout:150000});
    await page.getByRole('button',{name:'Analyze with AMD Gemma',exact:true}).click();
    const response=await pending;const actual=await response.json();
    await fs.writeFile(path.join(out,'fresh-analysis.json'),JSON.stringify({at:new Date().toISOString(),runtime:health,input:'../inputs/supplier-quality-helio.pdf',http_status:response.status(),actual},null,2));
    assert.equal(response.status(),200);assert.equal(actual.status,'completed / review required');
    assert.equal(actual.provenance.http_status,200);assert(actual.provenance.model_id);assert.equal(actual.provenance.requested_model_id,'Gemma-4-31B-IT');
    if(attempt==='3'){
      const previous=JSON.parse(await fs.readFile(path.join(out,'attempt-2-validation-failure.json'),'utf8'));
      assert.notEqual(actual.provenance.response_hash,previous.actual.provenance.response_hash,'Retained response cannot substitute for fresh inference');
    }
    const required=['HELIO-731','HELIO-732','HELIO-733'];
    for(const id of required){assert(actual.draft.candidates.some(c=>c.value===id&&c.inventory_status.includes('unresolved')));await page.getByText(id,{exact:true}).first().waitFor();}
    checks.push('Fresh AMD model response drives visible source-grounded proposals; all three non-sample IDs retained unresolved against inventory');
    await page.getByRole('checkbox',{name:/I inspected these proposals/}).check();
    await page.getByLabel('Review note',{exact:true}).fill('Agent-operated fictional engineering check: inspected each lot statement and unresolved inventory context against the retained original.');
    const review=page.waitForResponse(r=>r.url()===route+'/visitor-review'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Record source inspection',exact:true}).click();assert.equal((await review).status(),200);
    await page.getByText(/Source inspection recorded/).waitFor();
    await page.screenshot({path:path.join(out,'fresh-review-1440.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'Narrow source review must not overflow');
    await page.screenshot({path:path.join(out,'fresh-review-390.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1000});
    const rawExpected={'HELIO-731':'affected','HELIO-732':'explicitly_excluded','HELIO-733':'uncertain'};
    const rawQuality=Object.entries(rawExpected).map(([id,expected])=>({id,expected,raw:actual.raw_output.candidates?.filter(c=>c.value===id)||[],assembled:actual.draft.candidates.filter(c=>c.value===id),inventory_context:'unresolved',review:'Agent-operated source inspection, not independent human validation'}));
    await fs.writeFile(path.join(out,'raw-quality.json'),JSON.stringify(rawQuality,null,2));
    const second=await other.newPage();await second.goto(base,{waitUntil:'networkidle'});
    await second.getByRole('button',{name:'Analyze your document',exact:true}).waitFor();
    assert.deepEqual(await (await other.request.get(base+'/api/cases')).json(),[]);
    for(const suffix of ['', '/visitor-analysis','/export'])assert.equal((await other.request.get(route+suffix)).status(),404);
    const foreignUpload=await other.request.post(route+'/documents',{data:{filename:'foreign.txt',content_base64:Buffer.from('Supplier lot FOREIGN-1 requires review.').toString('base64')}});assert.equal(foreignUpload.status(),404);
    checks.push('Second clean browser context cannot list/read/export first visitor case, its proposals or upload to it');
    await second.screenshot({path:path.join(out,'clean-visitor-390.png'),fullPage:true});
    await upload('unrelated-garden.txt');
    await page.getByRole('checkbox',{name:/I may share this nonsensitive document/}).check();
    const rejected=page.waitForResponse(r=>r.url()===route+'/visitor-analysis'&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Analyze with AMD Gemma',exact:true}).click();
    const unrelated=await rejected;assert.equal(unrelated.status(),422);assert.equal((await unrelated.json()).detail.code,'UNRELATED_INPUT');
    await page.getByRole('alert').filter({hasText:'Unsupported document purpose'}).waitFor();
    await page.screenshot({path:path.join(out,'unrelated-rejection.png'),fullPage:true});
    const records=await (await context.request.get(route+'/visitor-analysis')).json();assert.equal(records.length,1);assert(records[0].stale);
    const state=await (await context.request.get(route)).json();assert.deepEqual(state.stocks,[]);assert.deepEqual(state.edges,[]);assert.deepEqual(state.receipts,[]);assert.equal(state.plan,null);
    assert.equal((await context.request.post(route+'/approve',{data:{}})).status(),403);
    assert.equal((await context.request.post(route+'/apply',{data:{}})).status(),403);
    checks.push('Unrelated upload explicitly rejected before inference; earlier result preserved stale; no visitor approval/execution authority');
    assert.deepEqual(errors,[]);
    const report={at:new Date().toISOString(),passed:true,url:base,version:health.version,commit:health.commit,case_id:caseId,checks,
      fresh_model_requests:1,phase_conservative_model_attempts:Number(attempt),prior_failed_attempts:['attempt-1-failure.json',...(attempt==='3'?['attempt-2-validation-failure.json']:[])].slice(0,Number(attempt)-1),input_sha256:inputHash,browser_analysis_posts:modelPosts.length,unrelated_model_requests:0,no_owner_or_provider_token_in_browser:true,
      provenance:actual.provenance,raw_quality_file:'raw-quality.json',review:'Agent-operated fictional engineering acceptance; not independent judge/domain validation',page_errors:errors,
      provider_access_end:'Not published; shared free access can be withdrawn. Daily reset is not expiry.',entitlement:actual.entitlement};
    await fs.writeFile(path.join(out,'result.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify({passed:true,commit:health.commit,checks:checks.length,fresh_model_requests:1,model_id:actual.provenance.model_id}));
  }finally{await context.close();await other.close();await browser.close();}
}
main().catch(e=>{console.error(e.stack);process.exitCode=1;});
