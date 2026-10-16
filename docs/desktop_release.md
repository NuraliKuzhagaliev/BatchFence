# Windows release 0.1.0

Target: Windows 11 x64. Actual host: Windows 11 Home Single Language,10.0.26200,x64. Electron 44.7.2 bundles Node 24.21.0. The app launches from an actual installed NSIS package, not a development Electron window.

Installer: D:\projects\BatchFence\releases\BatchFence-0.1.0-win-x64-setup.exe

Installed executable: D:\projects\BatchFence\work\installed\BatchFence.exe

Installer size: 113,768,001 bytes. Signing: **unsigned**, checked with Get-AuthenticodeSignature. Do not disable OS protections. Public download is pending authorized publication.

SHA-256 is finalized in releases/SHA256SUMS.txt and release-manifest.json after the final packaging check. Those files identify the exact binary; no signature or second-machine installation is claimed.

## Observed verification

- NSIS installer exit0. App metadata reports BatchFence0.1.0.
- Seven installed-app workflow checks, zero page errors: 500РІвЂ вЂ™800 scope, stale approval rejection, real sandbox receipt, web/desktop normalized parity, bounded native file bytes, invalid-packet rejection and restricted transport.
- A separate installed offline launch opened a web-exported packet/receipt with backend unreachable and PATH restricted to C:\Windows\System32. The renderer required no external Node/Python executable. This is not a clean-machine test with development tools uninstalled.
- Request-draft copying initially failed. A bounded sender-validated native clipboard write fixed it, and the installed and web copy checks now pass. Existing clipboard content was never read.
- Device-scale overrides 1.0/1.25 passed in the installed app, with no horizontal overflow. These are renderer-scale tests; OS display settings were unchanged.
- Packet promotion strips prior action authority; offline approve/apply remain unavailable.

Actual Windows open/save dialog selection remains **unverified**. Automated native file tests supplied dialog results, then executed real file reads/writes and validation. Earlier Windows UI automation encountered desktop activity/minimization. No dialog test is represented as manual acceptance.

## Remaining manual check

Open the installed app. Use Add evidence to select one provided TXT/CSV/text-PDF fixture through the real OS dialog. Export a JSON packet through Save, then reopen it through Open packet. Confirm source text and read-only state. Keep the save location on D:.

## Backend configuration

The installer bakes only desktop/backend-origin.json. Before an authorized remote release, set BATCHFENCE_BACKEND_ORIGIN to the public HTTPS service and run npm run package:desktop. The packaging script validates and saves that public origin. It never reads AMD keys or private .env data. Current distribution uses loopback 8787 and requires the local backend for online operations.

The renderer is isolated/sandboxed with no raw Node,IPC,shell or filesystem bridge. Sessions remain in main-process memory. Closing/restarting desktop starts a fresh capability; use packets for historical handoff. Python and model weights are not embedded.

Final installer SHA-256: 37bd0d13878d11632ca3cd90538df1aa43299e636893770526a0106378ec7e80
