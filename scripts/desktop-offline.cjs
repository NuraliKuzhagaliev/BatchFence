const { _electron: electron } = require("playwright");
const fs = require("node:fs/promises"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const out = process.env.BATCHFENCE_DESKTOP_REPORT_DIR || path.join(root, "docs");
let activeApp;
(async () => {
  await fs.mkdir(path.join(out, "screenshots"), {recursive:true});
  const app = activeApp = await electron.launch({
    executablePath: process.env.BATCHFENCE_TEST_EXE || path.join(root, "work/installed/BatchFence.exe"),
    env: {
      ...process.env,
      PATH: "C:\\Windows\\System32",
      BATCHFENCE_BACKEND_ORIGIN: "http://127.0.0.1:9",
      BATCHFENCE_USER_DATA: path.join(root, "work/desktop-offline-profile"),
    },
  });
  const page = await app.firstWindow();
  await page.getByText("Backend offline", { exact: true }).waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Open example incident", exact: false })
      .isEnabled(),
    false,
  );
  await app.evaluate(
    ({ dialog }, dest) => {
      dialog.showOpenDialog = async () => ({
        canceled: false,
        filePaths: [dest],
      });
    },
    process.env.BATCHFENCE_OFFLINE_PACKET || path.join(root, "docs/verified-decision-packet.json"),
  );
  await page.getByRole("button", { name: "Open packet", exact: true }).click();
  await page
    .getByText("Offline evidence review · historical snapshot", { exact: true })
    .waitFor();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      process.env.BATCHFENCE_EXPECTED_UNITS || "800",
    ),
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Approve exact plan", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Return to live desk", exact: true })
      .isEnabled(),
    false,
  );
  await page.getByRole("tab", { name: "Receipt", exact: true }).click();
  await page
    .getByRole("heading", { name: "Holds applied. Evidence preserved." }).first()
    .waitFor();
  assert.equal(await page.getByRole("heading", {name:"Holds applied. Evidence preserved.",exact:true}).count(),Number(process.env.BATCHFENCE_EXPECTED_RECEIPTS||1));
  await page.screenshot({
    path: path.join(out, "screenshots/13-installed-desktop-offline.png"),
    fullPage: true,
  });
  if(process.env.BATCHFENCE_ENTERPRISE_PACKET){
    await page.getByRole('tab',{name:'Recovery',exact:true}).click();
    await page.getByRole('heading',{name:'Saved restrictions and recovery receipts',exact:true}).waitFor();
    await page.getByText('Recovery receipts',{exact:true}).click();
    assert((await page.locator('body').innerText()).includes('became_available'));
    for(const section of ['Overview','Signals','Knowledge','Actions']){
      await page.getByRole('button',{name:section,exact:true}).click();
      await page.getByRole('heading',{name:'Saved evidence · no current action authority',exact:true}).waitFor();
      assert.equal(await page.locator('form').count(),0);
    }
    await page.screenshot({path:path.join(out,'screenshots/14-offline-modules.png'),fullPage:true});
  }
  await fs.writeFile(
    path.join(out, "desktop-offline-results.json"),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        packaged: true,
        backend: "Unreachable loopback port 9",
        child_PATH: "C:\\Windows\\System32",
        external_node_python_required: false,
        scope_units: Number(process.env.BATCHFENCE_EXPECTED_UNITS || 800),
        source_packet: path.basename(process.env.BATCHFENCE_OFFLINE_PACKET || "verified-decision-packet.json"),
        receipt_readable: true,
        receipt_count: Number(process.env.BATCHFENCE_EXPECTED_RECEIPTS||1),
        writes_disabled: true,
        native_dialog: "Stubbed result; bridge read and validation executed",
      },
      null,
      2,
    ),
  );
  await app.close();
  console.log(
    "Installed app opens web packet and historical receipt without backend or external Node/Python on PATH.",
  );
})().catch(async (e) => {
  await activeApp?.close();
  console.error(e);
  process.exitCode = 1;
});
