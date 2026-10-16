// Tests our installed application through Electron's test interface.
// Native dialogs are stubbed for deterministic bridge tests; manual OS dialogs are tracked separately.
const { _electron: electron } = require("playwright");
const fs = require("node:fs/promises");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
async function main() {
  const app = await electron.launch({
    executablePath: process.env.BATCHFENCE_TEST_EXE || path.join(root, "work/installed/BatchFence.exe"),
    env: {
      ...process.env,
      BATCHFENCE_USER_DATA: path.join(root, "work/desktop-smoke-profile"),
    },
    timeout: 30000,
  });
  const page = await app.firstWindow();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const checks = [];
  await page
    .getByRole("button", { name: "Load synthetic incident", exact: false })
    .waitFor();
  await page
    .getByRole("button", { name: "Load synthetic incident", exact: false })
    .click();
  await page.getByLabel('Run mode', {exact:true}).selectOption('fixture');
  await page
    .getByRole("button", { name: "Extract selected notice", exact: true })
    .click();
  await require('./review-controls.cjs').fixture(page, ['SUP-A']);
  await page
    .getByRole("button", { name: "Confirm scope & calculate", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Approve exact plan", exact: true })
    .waitFor();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      "500",
    ),
  );
  checks.push(
    "Installed UI → restricted main transport → backend → 500-unit v1",
  );
  await page
    .getByRole("button", { name: "Approve exact plan", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Add supplier v2", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Test stale approval", exact: true })
    .click();
  await page.getByRole("alert").waitFor();
  assert((await page.getByRole("alert").textContent()).includes("stale"));
  await page
    .getByRole("button", { name: "Review current evidence", exact: true })
    .click();
  await require('./review-controls.cjs').fixture(page, ['SUP-A', 'SUP-C']);
  await page
    .getByRole("button", { name: "Confirm scope & calculate", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Approve exact plan", exact: true })
    .waitFor();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      "800",
    ),
  );
  checks.push("Installed v2 800 units and stale approval rejection");
  await page
    .getByRole("button", { name: "Approve exact plan", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Apply sandbox holds", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Holds applied. Evidence preserved." })
    .waitFor();
  const nativePacket = path.join(root, "docs/desktop-decision-packet.json");
  await app.evaluate(({ dialog }, dest) => {
    dialog.showSaveDialog = async () => ({ canceled: false, filePath: dest });
  }, nativePacket);
  await page
    .getByRole("button", { name: "Export packet", exact: true })
    .click();
  await page
    .getByText(
      "Decision packet saved with source extracts, review history and receipts.",
      { exact: true },
    )
    .waitFor();
  const packet = JSON.parse(await fs.readFile(nativePacket, "utf8"));
  assert.equal(
    packet.case.receipts[0].changes.reduce((n, c) => n + c.units, 0),
    800,
  );
  const webPacket = JSON.parse(
    await fs.readFile(
      path.join(root, "docs/verified-decision-packet.json"),
      "utf8",
    ),
  );
  for (const field of [
    "hold_units",
    "hold_cents",
    "documented_units",
    "uncertain_units",
    "outside_units",
    "broad_cents",
    "excluded_cents",
  ])
    assert.equal(
      packet.case.plan.result[field],
      webPacket.case.plan.result[field],
    );
  assert.deepEqual(packet.case.plan.actions, webPacket.case.plan.actions);
  checks.push(
    "Web/desktop normalized scope, cents, quantities and policy actions equivalent",
  );
  const intake = path.join(root, "work/native-intake.txt");
  await fs.writeFile(
    intake,
    "Synthetic bridge test. Receiving record remains unresolved.",
  );
  await app.evaluate(({ dialog }, dest) => {
    dialog.showOpenDialog = async () => ({
      canceled: false,
      filePaths: [dest],
    });
  }, intake);
  await page.getByRole("button", { name: "Add evidence", exact: true }).click();
  await page
    .getByText(
      "New evidence added. Re-extract the current notice and review. CSV replacements await review.",
      { exact: true },
    )
    .waitFor();
  checks.push(
    "Native file byte bridge and shared server validation (dialog stubbed)",
  );
  const security = await page.evaluate(async () => {
    const bridge = window.batchfence;
    const result = {
      node: typeof window.require,
      rawIPC: typeof bridge.ipcRenderer,
      rawFS: typeof bridge.readFile,
      denied: false,
    };
    try {
      await bridge.request("GET", "https://evil.example/");
    } catch {
      result.denied = true;
    }
    return result;
  });
  assert.deepEqual(security, {
    node: "undefined",
    rawIPC: "undefined",
    rawFS: "undefined",
    denied: true,
  });
  checks.push(
    "No renderer Node/raw IPC/filesystem; unauthorized transport URL rejected",
  );
  await app.evaluate(
    ({ dialog }, dest) => {
      dialog.showOpenDialog = async () => ({
        canceled: false,
        filePaths: [dest],
      });
    },
    path.join(root, "docs/verified-decision-packet.json"),
  );
  await page.getByRole("button", { name: "Open packet", exact: true }).click();
  await page
    .getByText("Offline evidence review · historical snapshot", { exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Approve exact plan", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Apply sandbox holds", exact: true })
      .count(),
    0,
  );
  const windowSize = await app.evaluate(({ BrowserWindow }) =>
    BrowserWindow.getAllWindows()[0].getBounds(),
  );
  await page.screenshot({
    path: path.join(root, "docs/screenshots/12-installed-desktop-packet.png"),
    fullPage: true,
  });
  checks.push(
    "Web-exported historical packet opened by installed desktop; action authority absent",
  );
  // Reject changed packets before opening them.
  const invalid = path.join(root, "work/invalid-packet.json");
  await fs.writeFile(invalid, '{"schema_version":999}');
  await app.evaluate(({ dialog }, dest) => {
    dialog.showOpenDialog = async () => ({
      canceled: false,
      filePaths: [dest],
    });
  }, invalid);
  await page.getByRole("button", { name: "Open packet", exact: true }).click();
  await page.getByRole("alert").waitFor();
  assert((await page.getByRole("alert").textContent()).includes("Invalid"));
  checks.push("Invalid packet schema rejected through installed native bridge");
  const releaseInfo = await app.evaluate(({ app }) => ({
    electron: process.versions.electron,
    node: process.versions.node,
    platform: process.platform,
    arch: process.arch,
    packaged: app.isPackaged,
    exe: app.getPath("exe"),
  }));
  await fs.writeFile(
    path.join(root, "docs/desktop-results.json"),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        releaseInfo,
        windowSize,
        checks,
        security,
        errors,
        dialog_testing:
          "Programmatic dialog result stubs; actual OS dialog selection is recorded separately",
      },
      null,
      2,
    ),
  );
  await app.close();
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({ checks: checks.length, errors, releaseInfo }, null, 2),
  );
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
