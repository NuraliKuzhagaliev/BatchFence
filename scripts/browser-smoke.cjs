const { chromium } = require("playwright");
const fs = require("node:fs/promises");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const out = path.join(root, "docs/screenshots");
async function main() {
  await fs.mkdir(out, { recursive: true });
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const checks = [];
  const shot = async (name) =>
    page.screenshot({ path: path.join(out, name + ".png"), fullPage: true });
  const click = async (name) =>
    page.getByRole("button", { name, exact: true }).click();
  const review = async () => {
    await page
      .getByLabel(
        "I checked lot IDs, exclusions, qualifiers and whether this notice supersedes prior scope.",
      )
      .check();
    await click("Confirm scope & calculate");
    await page
      .getByRole("button", { name: "Approve exact plan", exact: true })
      .waitFor();
  };
  await page.goto("http://127.0.0.1:8787/");
  await page
    .getByRole("button", { name: "Load synthetic incident", exact: false })
    .waitFor();
  await shot("01-intake-1440");
  await page
    .getByRole("button", { name: "Load synthetic incident", exact: false })
    .click();
  await click("Extract selected notice");
  await page
    .getByRole("heading", { name: "Confirm the affected supplier lots." })
    .waitFor();
  await shot("02-critical-review-1440");
  await page
    .getByRole("button", {
      name: "SUP-A Affected candidate Inspect quote",
      exact: false,
    })
    .click();
  assert(
    (await page.locator(".source-block.highlight").textContent()).includes(
      "Affected lots: SUP-A",
    ),
  );
  checks.push("Exact source citation reachable from candidate");
  await review();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      "500",
    ),
  );
  assert(
    (await page.locator(".decision-main p").textContent()).includes(
      "100 uncertain",
    ),
  );
  if (
    await page
      .getByRole("button", { name: "Close inspector", exact: true })
      .isVisible()
  )
    await click("Close inspector");
  await shot("03-exposure-1440");
  await page.getByRole("tab", { name: "Evidence requests" }).click();
  assert(
    (await page.locator(".queue-summary").textContent()).includes("100 units"),
  );
  assert(
    (await page.locator(".queue-summary").textContent()).includes("€4,000"),
  );
  checks.push("Evidence queue 100 units / €4,000");
  await page.getByRole("tab", { name: "Order review" }).click();
  assert(
    (await page.locator(".queue-summary").textContent()).includes(
      "3 open orders",
    ),
  );
  checks.push("V1 order review 3 orders");
  await page.getByRole("tab", { name: "Exposure", exact: true }).click();
  await click("Lineage table");
  assert.equal(await page.locator("tbody tr").count(), 6);
  await click("Graph view");
  await page.getByRole("button", { name: /FG-C, 100 units/ }).click();
  assert(
    (await page.locator(".inspector-stock").textContent()).includes(
      "Possible ancestry",
    ),
  );
  await click("Approve exact plan");
  await page
    .getByRole("button", { name: "Apply sandbox holds", exact: true })
    .waitFor();
  await click("Test excluding uncertain stock");
  await page.getByRole("alert").waitFor();
  assert(
    (await page.getByRole("alert").textContent()).includes(
      "Exact required hold set",
    ),
  );
  checks.push("Uncertain exclusion rejected server-side through UI");
  await click("Add supplier v2");
  await page
    .getByRole("button", { name: "Test stale approval", exact: true })
    .waitFor();
  await shot("04-stale-revision-1440");
  await click("Test stale approval");
  await page.getByRole("alert").waitFor();
  assert((await page.getByRole("alert").textContent()).includes("stale"));
  checks.push("Stale approval rejected through UI");
  await click("Review current evidence");
  await review();
  assert(
    (await page.locator(".comparison .required strong").textContent()).includes(
      "800",
    ),
  );
  await page.getByRole("tab", { name: "Order review" }).click();
  assert(
    (await page.locator(".queue-summary").textContent()).includes(
      "4 open orders",
    ),
  );
  checks.push("V2 800-unit plan and 4 orders");
  await page.getByRole("tab", { name: "Revisions", exact: true }).click();
  await shot("05-revision-diff-1440");
  await click("Approve exact plan");
  await click("Apply sandbox holds");
  await page
    .getByRole("heading", { name: "Holds applied. Evidence preserved." })
    .waitFor();
  await shot("06-receipt-1440");
  const downloadPromise = page.waitForEvent("download");
  await click("Export packet");
  const download = await downloadPromise;
  const packetPath = path.join(root, "docs", "verified-decision-packet.json");
  await download.saveAs(packetPath);
  const packet = JSON.parse(await fs.readFile(packetPath, "utf8"));
  assert.equal(packet.case.receipts.length, 1);
  assert.equal(
    packet.case.receipts[0].changes.reduce((n, c) => n + c.units, 0),
    800,
  );
  const id = packet.case.id;
  await page.reload();
  await page
    .getByRole("heading", { name: "Northstar Enclosures", exact: true })
    .waitFor();
  assert(
    (await page.locator(".decision-main strong").textContent()).includes(
      "Applied to sandbox",
    ),
  );
  checks.push("Exported packet includes actual receipt; refresh persists case");
  await page.getByRole("tab", { name: "Exposure", exact: true }).click();
  await page.setViewportSize({ width: 1280, height: 720 });
  await shot("07-exposure-1280");
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await shot("08-exposure-mobile-390");
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.getByRole("button", { name: "Sources", exact: true }).click();
  await shot("09-sources-mobile-390");
  await page.getByRole("button", { name: "Decision", exact: true }).click();
  await shot("10-decision-mobile-390");
  checks.push("Responsive layout no horizontal overflow at 1280 and 390");
  await page.setViewportSize({ width: 1440, height: 900 });
  const before = await page.locator("input[type=file]").count();
  assert.equal(before, 2);
  await page
    .locator('input[type=file][accept=".json"]')
    .setInputFiles(packetPath);
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
  await shot("11-offline-packet-web-1440");
  checks.push("Web packet opens read-only without approval/apply authority");
  await context.setOffline(true);
  assert(
    await page
      .getByText("Offline evidence review · historical snapshot", {
        exact: true,
      })
      .isVisible(),
  );
  checks.push("Already opened packet remains readable without network");
  assert.deepEqual(errors, []);
  await fs.writeFile(
    path.join(root, "docs/browser-results.json"),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        browser: "Microsoft Edge, Playwright headless",
        checks,
        errors,
        case_id: id,
        packet: packetPath,
      },
      null,
      2,
    ),
  );
  await browser.close();
  console.log(
    JSON.stringify(
      { checks: checks.length, errors, packet: packetPath },
      null,
      2,
    ),
  );
}
main().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
