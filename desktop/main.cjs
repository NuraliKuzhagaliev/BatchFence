const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  protocol,
  net,
  session,
  clipboard,
  shell,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");
const { pathToFileURL } = require("node:url");
const { validatePacket } = require("./packet.cjs");
// Fixed backend origin; the renderer cannot select endpoints or external URLs.
const origin = process.env.BATCHFENCE_BACKEND_ORIGIN || require("./backend-origin.json").origin;
const url = new URL(origin);
if (
  !(
    url.protocol === "https:" ||
    (url.protocol === "http:" &&
      ["127.0.0.1", "localhost"].includes(url.hostname))
  ) ||
  url.username ||
  url.password ||
  url.pathname !== "/" ||
  url.search ||
  url.hash
)
  throw Error("Invalid backend origin");
app.setPath(
  "userData",
  process.env.BATCHFENCE_USER_DATA ||
    path.join(path.dirname(app.getPath("exe")), "BatchFenceData"),
);
protocol.registerSchemesAsPrivileged([
  {
    scheme: "batchfence",
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);
let win,
  capability = "";
const apiPattern =
  /^\/api\/(?:health|replay|challenges|audit|inspections|intake\/profiles|jobs(?:\/[a-f0-9-]+\/cancel)?|auth\/(?:login|logout|me|membership)|cases(?:\/(?:demo|import|[a-f0-9]{32}(?:\/(?:documents(?:\/DOC-[a-f0-9]{12}\/pages\/[1-8])?|revision|analyze|reviews|approve|apply|export|simulate|reply-preview|reply-review|comparison|intake-preview|intake-review|ocr-review))?))?)$/;
function sender(event) {
  if (
    !win ||
    event.sender !== win.webContents ||
    event.senderFrame?.url !== "batchfence://app/"
  )
    throw Error("Sender denied");
}
function packetSize(p) {
  if (JSON.stringify(p).length > 6000000) throw Error("Packet exceeds 6 MB");
  return validatePacket(p);
}
app.whenReady().then(() => {
  ipcMain.handle("bf:copyDraft", (event, draft) => {
    sender(event);
    if (
      typeof draft !== "string" ||
      !draft.length ||
      Buffer.byteLength(draft, "utf8") > 4000
    )
      throw Error("Invalid request draft");
    clipboard.writeText(draft);
  });
  session.defaultSession.setPermissionRequestHandler((_w, _p, cb) => cb(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  protocol.handle("batchfence", (request) => {
    const u = new URL(request.url);
    const relative = decodeURIComponent(
      u.pathname === "/" ? "/index.html" : u.pathname,
    );
    const base = path.resolve(__dirname, "../dist");
    const target = path.resolve(base, "." + relative);
    if (u.host !== "app" || !target.startsWith(base + path.sep))
      return new Response("Denied", { status: 403 });
    return net.fetch(pathToFileURL(target).href);
  });
  ipcMain.handle("bf:openWebApp", async (event) => {
    sender(event);
    await shell.openExternal("https://batchfence.onrender.com");
  });
  ipcMain.handle("bf:request", async (event, method, route, body, accessToken) => {
    sender(event);
    if (
      !["GET", "POST"].includes(method) ||
      typeof route !== "string" ||
      !apiPattern.test(route) ||
      (route === "/api/replay" && method !== "GET") ||
      (accessToken !== undefined && (typeof accessToken !== "string" || accessToken.length > 200 || /[\r\n]/.test(accessToken))) ||
      (method === "GET" && body !== undefined) ||
      JSON.stringify(body || {}).length > 8000000
    )
      throw Error("Transport request denied");
    const response = await fetch(origin + route, {
      method,
      redirect: "error",
      signal: AbortSignal.timeout(route.endsWith("/documents") ? 120000 : 55000),
      headers: {
        "Content-Type": "application/json",
        "X-BF-Client": "desktop",
        ...(capability ? { "X-BF-Session": capability } : {}),
        ...(method === "POST" && route.endsWith("/analyze") && accessToken ? { "X-BF-Demo-Token": accessToken } : {}),
      },
      ...(method === "POST" ? { body: JSON.stringify(body || {}) } : {}),
    });
    if (response.headers.has("x-bf-session"))
      capability = response.headers.get("x-bf-session");
    const text = await response.text();
    if (text.length > 8000000) throw Error("Backend response too large");
    const result = JSON.parse(text);
    if (!response.ok)
      throw Error(result.detail?.message || "Backend request failed");
    return result;
  });
  ipcMain.handle("bf:chooseFiles", async (event) => {
    sender(event);
    const selection = await dialog.showOpenDialog(win, {
      title: "Import evidence",
      properties: ["openFile", "multiSelections"],
      filters: [
        { name: "Supported evidence", extensions: ["txt", "csv", "pdf"] },
      ],
    });
    if (selection.canceled) return [];
    if (selection.filePaths.length > 8) throw Error("Choose at most 8 files");
    const results = [];
    for (const filename of selection.filePaths) {
      if (
        ![".txt", ".csv", ".pdf"].includes(
          path.extname(filename).toLowerCase(),
        ) ||
        (await fs.stat(filename)).size > 2000000
      )
        throw Error("Unsupported file or size above 2 MB");
      results.push({
        filename: path.basename(filename),
        content_base64: (await fs.readFile(filename)).toString("base64"),
      });
    }
    return results;
  });
  ipcMain.handle("bf:savePacket", async (event, packet) => {
    sender(event);
    packetSize(packet);
    const selection = await dialog.showSaveDialog(win, {
      title: "Save decision packet",
      defaultPath: "BatchFence-decision.json",
      filters: [{ name: "Decision packet", extensions: ["json"] }],
    });
    if (selection.canceled) return false;
    if (path.extname(selection.filePath).toLowerCase() !== ".json")
      throw Error("Packet must have .json extension");
    await fs.writeFile(
      selection.filePath,
      JSON.stringify(packet, null, 2),
      "utf8",
    );
    return true;
  });
  ipcMain.handle("bf:openPacket", async (event) => {
    sender(event);
    const selection = await dialog.showOpenDialog(win, {
      title: "Open offline decision packet",
      properties: ["openFile"],
      filters: [{ name: "Decision packet", extensions: ["json"] }],
    });
    if (selection.canceled) return null;
    const filename = selection.filePaths[0];
    if (
      path.extname(filename).toLowerCase() !== ".json" ||
      (await fs.stat(filename)).size > 6000000
    )
      throw Error("Invalid packet type or size");
    return packetSize(JSON.parse(await fs.readFile(filename, "utf8")));
  });
  win = new BrowserWindow({
    width: 1366,
    height: 768,
    minWidth: 960,
    minHeight: 600,
    title: "BatchFence",
    backgroundColor: "#F4F6F8",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event, u) => {
    if (u !== "batchfence://app/") event.preventDefault();
  });
  win.loadURL("batchfence://app/");
});
app.on("window-all-closed", () => app.quit());
