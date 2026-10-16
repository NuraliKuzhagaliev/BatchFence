// Deliberately pauses after each real extraction for an operator's source review.
// Never generates substitute model output or auto-corrects a failed extraction.
const { chromium } = require('playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const dir = path.join(root, 'docs/live-verification');
const scratch = path.join(root, 'work/live-verification', process.argv[2] || 'review-session');
const base = 'http://127.0.0.1:8787';
async function main() {
  await fs.mkdir(scratch, { recursive: true });
  const manifest = JSON.parse(await fs.readFile(path.join(dir, 'input-manifest.json'), 'utf8'));
  const report = { started_at: new Date().toISOString(), mode: 'live', synthetic_inputs: true,
    fixture_fallback_used: false, review_method: 'Operator examines raw output and source, then supplies accepted lots. UI review/approval clicks are automated.',
    independent_human_validation: false, review_directory:scratch, stages: [], errors: [] };
  const reportFile = path.join(dir, 'browser-results.json');
  const save = () => fs.writeFile(reportFile, JSON.stringify(report, null, 2));
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const page = await context.newPage();
  page.on('pageerror', e => report.errors.push(e.message));
  const click = name => page.getByRole('button', { name, exact: true }).click();
  const screenshot = name => page.screenshot({ path: path.join(dir, name + '.png'), fullPage: true });
  try {
    await page.goto(base);
    const health = await (await context.request.get(base + '/api/health')).json();
    assert.equal(health.amd_configured, true);
    assert.equal(health.inference_mode, 'live');
    await page.locator('input[type=file][accept=".json"]').setInputFiles(path.join(dir, 'input-packet.json'));
    await click('Promote to new draft');
    await page.getByText('New draft created. Historical approval does not transfer.', {exact:true}).waitFor();
    const id = await page.evaluate(() => localStorage.getItem('bf.case'));
    report.case_id = id;
    const current = async () => (await context.request.get(base + '/api/cases/' + id)).json();
    for (let i = 0; i < 2; i++) {
      const truth = manifest.cases[i];
      const raw = await fs.readFile(path.join(dir, truth.file));
      const before = await current();
      const uploadResponse = page.waitForResponse(r => r.url().endsWith('/documents') && r.request().method() === 'POST');
      await page.locator('input[type=file][accept=".txt,.csv,.pdf"]').setInputFiles({
        name: manifest.uploaded_filename_for_both, mimeType: 'text/plain', buffer: raw,
      });
      assert.equal((await uploadResponse).status(), 200);
      assert.equal((await current()).revision, before.revision + 1);
      await page.getByLabel('Run mode', {exact:true}).selectOption('live');
      const analysis = page.waitForResponse(r => r.url().endsWith('/analyze') && r.request().method() === 'POST', {timeout:60000});
      await click('Extract selected notice');
      const state = await (await analysis).json();
      const run = state.runs.at(-1);
      const selected = state.documents.find(d => d.id === run.document_id);
      const affected = run.output?.facts.filter(f => f.affected).map(f => f.lot_id).sort() || [];
      const stage = { sequence:i+1, source:selected, raw_run:run,
        raw_evaluation: { expected:truth.affected_lots, extracted:affected,
          missing:truth.affected_lots.filter(x => !affected.includes(x)),
          extra:affected.filter(x => !truth.affected_lots.includes(x)) },
        review_status:'awaiting_operator' };
      report.stages.push(stage);
      await save();
      assert.equal(run.mode, 'live');
      assert.equal(run.status, 'succeeded', run.error || 'Live extraction failed; no fallback');
      await page.getByRole('heading',{name:'Confirm the affected supplier lots.',exact:true}).waitFor();
      for (const fact of run.output.facts) {
        await page.getByRole('button',{name:new RegExp('^'+fact.lot_id.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+' ')}).click();
        assert((await page.locator('.source-block.highlight').textContent()).includes(fact.evidence[0].quote));
      }
      await click('Technical details');
      await screenshot(`0${i+1}-live-candidates`);
      await click('Technical details');
      await context.storageState({path:path.join(scratch,'private-browser-session.json')});
      console.log(JSON.stringify({stage:i+1,status:'awaiting_operator',review_directory:scratch,case_id:id,run,source:selected},null,2));
      const reviewPath = path.join(scratch, `review-${i+1}.json`);
      let reviewed;
      const deadline = Date.now() + 600000;
      while (Date.now() < deadline) {
        try { reviewed = JSON.parse(await fs.readFile(reviewPath,'utf8')); break; }
        catch(e) { if(e.code !== 'ENOENT') throw e; }
        await new Promise(r => setTimeout(r,1000));
      }
      assert(reviewed, 'Operator review not supplied within ten minutes');
      assert.equal(reviewed.run_id, run.id, 'Review must refer to the current raw model run');
      assert.equal(reviewed.source_hash, selected.original_hash, 'Review must refer to the exact source');
      await page.getByLabel('Accepted affected lots · comma separated',{exact:true}).fill(reviewed.accepted_lots.join(', '));
      await page.getByLabel('I reviewed inventory, lineage and the bounded completeness manifest. Uncheck to decline narrowing.').check();
      await page.getByLabel('I checked lot IDs, exclusions, qualifiers and whether this notice supersedes prior scope.').check();
      await click('Confirm scope & calculate');
      await page.getByRole('button',{name:'Approve exact plan',exact:true}).waitFor();
      const calculated = await current();
      for (const field of ['hold_units','documented_units','uncertain_units','outside_units','hold_cents'])
        assert.equal(calculated.plan.result[field], truth[field], field);
      assert.deepEqual(calculated.plan.actions.map(a=>a.pool_id).sort(), [...truth.hold_pools].sort());
      stage.review = reviewed;
      stage.review_status = 'reviewed';
      stage.corrections = { removed:affected.filter(x=>!reviewed.accepted_lots.includes(x)), added:reviewed.accepted_lots.filter(x=>!affected.includes(x)) };
      stage.result_after_review = calculated.plan.result;
      await screenshot(`0${i+1}-reviewed-scope`);
      await click('Approve exact plan');
      await page.getByRole('button',{name:'Apply sandbox holds',exact:true}).waitFor();
      await click('Apply sandbox holds');
      await page.getByRole('heading',{name:'Holds applied. Evidence preserved.',exact:true}).last().waitFor();
      const downloadPending = page.waitForEvent('download');
      await click('Export packet');
      await (await downloadPending).saveAs(path.join(dir, `packet-${i+1}.json`));
      const applied = await current();
      stage.receipt = applied.receipts.at(-1);
      assert.equal(applied.receipts.length, i+1);
      assert.equal(stage.receipt.changes.reduce((n,x)=>n+x.units,0), truth.hold_units);
      stage.held_units_persisted = applied.stocks.filter(s=>s.status==='held').reduce((n,s)=>n+s.units,0);
      assert.equal(stage.held_units_persisted, truth.hold_units);
      await screenshot(`0${i+1}-sandbox-receipt`);
      await page.reload();
      await page.locator('.case-status').filter({hasText:'Applied to sandbox'}).waitFor();
      assert.deepEqual((await current()).receipts, applied.receipts);
      stage.refresh_persistence = true;
      await save();
    }
    report.finished_at = new Date().toISOString();
    report.status = 'passed';
    assert.deepEqual(report.errors, []);
    console.log(JSON.stringify({status:report.status,stages:report.stages.length,errors:report.errors}));
  } catch(e) {
    report.status='failed'; report.failure=e.message; await save(); throw e;
  } finally { await save(); await browser.close(); }
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
