// One fresh browser inference at most. Cloudflare and owner tokens stay server-side.
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const ORIGIN = 'https://batchfence.onrender.com';
const MODEL = '@cf/google/gemma-4-26b-a4b-it';
const folder = path.resolve(__dirname, '../work/cloudflare-visitor');
const lots = { 'NORWICK-581': 'affected', 'NORWICK-582': 'explicitly_excluded', 'NORWICK-583': 'uncertain' };
const filename = 'norwick-revised-supplier-notice.pdf';
const notice = [
  'Norwick Components - supplier quality notice, revision B',
  'Lot NORWICK-581 is affected by seal failure. Inspect and hold this lot.',
  'Lot NORWICK-582 is expressly excluded from this notice.',
  'Receiving records conflict for lot NORWICK-583. Its status is unresolved.',
  'Earlier revision A is superseded. No inventory lineage has been supplied.',
];

function makePdf(lines) {
  const text = ['BT /F1 12 Tf 50 735 Td 20 TL', ...lines.map(line => `(${line}) Tj T*`), 'ET'].join('\n');
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(text)} >>\nstream\n${text}\nendstream`,
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = objects.map((object, index) => {
    const offset = Buffer.byteLength(pdf);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    return offset;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) pdf += `${String(offset).padStart(10, '0')} 00000 n \n`;
  pdf += `trailer\n<< /Root 1 0 R /Size ${objects.length + 1} >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf);
}

async function main() {
  const live = process.argv[2] === '--live';
  const expectedCommit = process.argv[3];
  if (live) assert.match(expectedCommit || '', /^[a-f0-9]{40}$/, 'Require the exact deployed commit');
  await fs.mkdir(folder, { recursive: true });
  const pdf = makePdf(notice);
  await fs.writeFile(path.join(folder, filename), pdf);
  const digest = createHash('sha256').update(pdf).digest('hex');
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const visitor = await browser.newContext({ viewport: { width: 1440, height: 980 } });
    const other = await browser.newContext();
    assert.deepEqual((await visitor.storageState()).cookies, []);
    const page = await visitor.newPage();
    const pageErrors = [];
    let secretHeaders = false;
    let analysisPosts = 0;
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('request', request => {
      if (!request.url().startsWith(ORIGIN + '/api/')) return;
      const headers = request.headers();
      secretHeaders ||= !!(headers['x-bf-demo-token'] || headers.authorization);
      if (request.method() === 'POST' && request.url().endsWith('/visitor-analysis')) analysisPosts++;
    });
    await page.goto(ORIGIN, { waitUntil: 'domcontentloaded', timeout: 100000 });
    const health = await (await visitor.request.get(ORIGIN + '/api/health')).json();
    assert.equal(health.status, 'ok');
    if (live) assert.equal(health.commit, expectedCommit);
    assert.deepEqual(await (await visitor.request.get(ORIGIN + '/api/cases')).json(), []);
    await page.getByRole('button', { name: 'Analyze your document', exact: true }).click({ timeout: 45000 });
    await page.getByRole('heading', { name: 'Bring your own evidence.' }).waitFor();
    const [incident] = await (await visitor.request.get(ORIGIN + '/api/cases')).json();
    const route = `${ORIGIN}/api/cases/${incident.id}`;
    assert.deepEqual((await (await visitor.request.get(route)).json()).stocks, []);
    const uploaded = page.waitForResponse(r => r.url() === route + '/documents' && r.request().method() === 'POST');
    await page.locator('.visitor-review input[type=file]').setInputFiles({ name: filename, mimeType: 'application/pdf', buffer: pdf });
    const upload = await uploaded;
    assert.equal(upload.status(), 200, await upload.text());
    const [original] = (await upload.json()).documents;
    assert.equal(original.original_hash, digest);
    await page.getByRole('img', { name: 'Original PDF page 1 of ' + filename }).waitFor({ timeout: 30000 });
    assert.deepEqual(await (await other.request.get(ORIGIN + '/api/cases')).json(), []);
    assert.equal((await other.request.get(route)).status(), 404);
    assert.equal((await other.request.get(route + '/visitor-analysis')).status(), 404);
    const preflight = await (await visitor.request.get(ORIGIN + '/api/visitor/status')).json();
    const report = { at: new Date().toISOString(), commit: health.commit, version: health.version,
      pdf: filename, sha256: digest, anonymous_upload: true, original_rendered: true, cross_session_isolation: true, preflight };
    const reportFile = path.join(folder, live ? 'live-result.json' : 'upload-result.json');
    await page.screenshot({ path: path.join(folder, 'original.png'), fullPage: true });
    await fs.writeFile(reportFile, JSON.stringify({ ...report, analysisPosts, secretHeaders }, null, 2));
    if (live) {
      assert.equal(preflight.provider, 'Cloudflare Workers AI');
      assert.equal(preflight.status, 'available');
      assert.equal(preflight.requested_model_id, MODEL);
      await page.getByRole('checkbox', { name: /I may share text from this nonsensitive document with Cloudflare/ }).check();
      const pending = page.waitForResponse(r => r.url() === route + '/visitor-analysis' && r.request().method() === 'POST', { timeout: 135000 });
      await page.getByRole('button', { name: 'Analyze with Gemma', exact: true }).click();
      const response = await pending;
      const result = await response.json();
      report.inference = { http: response.status(), status: result.status, error: result.error,
        failure: result.failure_evidence, provenance: result.provenance, raw: result.raw_output };
      await fs.writeFile(reportFile, JSON.stringify({ ...report, analysisPosts, secretHeaders }, null, 2));
      assert.equal(response.status(), 200);
      assert.equal(result.status, 'completed / review required', result.error);
      assert.equal(result.provenance.provider, 'Cloudflare Workers AI');
      assert.equal(result.provenance.http_status, 200);
      assert.equal(result.provenance.requested_model_id, MODEL);
      assert.match(result.provenance.response_hash, /^[a-f0-9]{64}$/);
      report.raw_lot_quality = Object.entries(lots).map(([id, expected]) => ({ id, expected,
        actual: result.raw_output.candidates.filter(candidate => candidate.value === id).map(candidate => candidate.incident_status) }));
      for (const id of Object.keys(lots)) {
        const proposed = result.draft.candidates.find(candidate => candidate.value === id);
        assert.equal(proposed?.inventory_status, 'unresolved / no inventory relationship supplied');
        assert.equal(proposed.source.original_hash || original.original_hash, digest);
        await page.getByText(id, { exact: true }).first().waitFor();
      }
      assert(result.raw_output.candidates.length, 'At least one visible proposal must originate in the real model response');
      assert.equal(result.draft.incident_scope, 'unknown');
      assert.equal((await visitor.request.post(route + '/apply', { data: {} })).status(), 403);
      assert.equal(analysisPosts, 1);
      await page.screenshot({ path: path.join(folder, 'verified-review.png'), fullPage: true });
    }
    assert.equal(secretHeaders, false);
    assert.deepEqual(pageErrors, []);
    await fs.writeFile(reportFile, JSON.stringify({ ...report, passed: true, analysisPosts, secretHeaders }, null, 2));
    console.log(JSON.stringify({ reportFile, commit: health.commit, analysisPosts, status: preflight.status }));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
