// Recover persisted observations after a test-only selector failure. No inference.
const { chromium } = require('playwright');
const fs = require('node:fs/promises'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname,'..'), dir = path.join(root,'docs/live-verification');
(async()=>{
  const reportPath=path.join(dir,'browser-results.json');
  const report=JSON.parse(await fs.readFile(reportPath,'utf8'));
  await fs.writeFile(path.join(dir,'second-test-selector-failure.json'),JSON.stringify(report,null,2),{flag:'wx'});
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,
    storageState:path.join(report.review_directory,'private-browser-session.json')});
  const page=await context.newPage();
  const base='http://127.0.0.1:8787', route=base+'/api/cases/'+report.case_id;
  try {
    await page.goto(base);
    await page.locator('.case-status').filter({hasText:'Applied to sandbox'}).waitFor();
    const state=await (await context.request.get(route)).json();
    assert.equal(state.runs.length,2);
    assert(state.runs.every(r=>r.mode==='live'&&r.status==='succeeded'));
    assert.equal(state.receipts.length,2);
    assert.equal(state.plan.result.hold_units,800);
    assert.equal(state.stocks.filter(s=>s.status==='held').reduce((n,s)=>n+s.units,0),800);
    const final=report.stages[1];
    final.receipt=state.receipts[1];
    assert.equal(final.receipt.changes.reduce((n,s)=>n+s.units,0),800);
    final.newly_held_units=final.receipt.changes.filter(s=>s.before!=='held').reduce((n,s)=>n+s.units,0);
    assert.equal(final.newly_held_units,300);
    final.held_units_persisted=800;
    await page.getByRole('tab',{name:'Receipt',exact:true}).click();
    assert.equal(await page.getByRole('heading',{name:'Holds applied. Evidence preserved.',exact:true}).count(),2);
    const download=page.waitForEvent('download');
    await page.getByRole('button',{name:'Export packet',exact:true}).click();
    await (await download).saveAs(path.join(dir,'packet-2.json'));
    const packet=JSON.parse(await fs.readFile(path.join(dir,'packet-2.json'),'utf8'));
    assert.deepEqual(packet.case.receipts,state.receipts);
    await page.screenshot({path:path.join(dir,'02-sandbox-receipt.png'),fullPage:true});
    await page.reload();
    await page.locator('.case-status').filter({hasText:'Applied to sandbox'}).waitFor();
    const persisted=await (await context.request.get(route)).json();
    assert.deepEqual(persisted.receipts,state.receipts);
    final.refresh_persistence=true;
    const first=JSON.parse(await fs.readFile(path.join(dir,'packet-1.json'),'utf8')).case.plan;
    const stale=await context.request.post(route+'/apply',{data:{plan_id:first.id,digest:first.digest,
      actions:first.actions,idempotency_key:'live-stale-recheck-'+Date.now()}});
    const staleBody=await stale.json();
    assert.equal(stale.status(),409); assert.equal(staleBody.detail.code,'STALE_APPROVAL');
    report.stale_request_recheck={status:stale.status(),code:staleBody.detail.code};
    report.test_harness_recovery={at:new Date().toISOString(),additional_model_calls:0,
      reason:report.failure,observed_receipt_count:state.receipts.length,
      method:'Reopened the saved private browser session; fetched persisted case; inspected both UI receipts; exported and reloaded the current packet.'};
    delete report.failure;
    report.status='passed_after_test_selector_recovery'; report.finished_at=new Date().toISOString();
    await fs.writeFile(reportPath,JSON.stringify(report,null,2));
    console.log(JSON.stringify({status:report.status,case_id:report.case_id,receipts:state.receipts.map(r=>r.transaction_id),held_units:800,newly_held_units:final.newly_held_units,stale_request:report.stale_request_recheck,additional_model_calls:0},null,2));
  } finally {await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
