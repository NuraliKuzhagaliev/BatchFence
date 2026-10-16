const { _electron: electron } = require("playwright");
const fs = require("node:fs/promises"),
  path = require("node:path"),
  assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
(async () => {
  const app = await electron.launch({
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
      .getByRole("button", { name: "Load synthetic incident", exact: false })
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
    path.join(root, "docs/verified-decision-packet.json"),
  );
  await page.getByRole("button", { name: "Open packet", exact: true }).click();
  await page
    .getByText("Offline evidence review · historical snapshot", { exact: true })
    .waitFor();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      "800",
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
    .getByRole("heading", { name: "Holds applied. Evidence preserved." })
    .waitFor();
  await page.screenshot({
    path: path.join(root, "docs/screenshots/13-installed-desktop-offline.png"),
    fullPage: true,
  });
  await fs.writeFile(
    path.join(root, "docs/desktop-offline-results.json"),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        packaged: true,
        backend: "Unreachable loopback port 9",
        child_PATH: "C:\\Windows\\System32",
        external_node_python_required: false,
        scope_units: 800,
        receipt_readable: true,
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
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
