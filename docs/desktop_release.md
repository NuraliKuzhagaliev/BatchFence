# Windows release 0.1.2

Current installer: [BatchFence-0.1.2-win-x64-setup.exe](https://github.com/NuraliKuzhagaliev/BatchFence/releases/download/v0.1.2/BatchFence-0.1.2-win-x64-setup.exe). [Release notes and SHA-256](https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.1.2).

Connects to the hosted HTTPS backend without requiring local Python. Protected Live access and read-only historical replay are supported. Desktop shows Open web app only; the website shows Download for Windows only. Provider credentials are never bundled. Installed workflow and additional genuine AMD candidate checks are in [release checks](release-0.1.2/README.md).

The installer is unsigned. It installed with exit 0 on the current Windows 11 x64 host, and the installed app.asar matches the built payload. Automated file dialogs use selection stubs; physical OS dialog acceptance and a second-machine installation remain unverified for this exact build. Server storage is ephemeral; export receipts before closing or redeployment. No paid signing or hosting was introduced.

---

Historical local installer details follow unchanged.

# Windows release 0.1.1

Installer: releases/BatchFence-0.1.1-win-x64-setup.exe. Installed verification copy: work/installed-0.1.1/BatchFence.exe. SHA-256 and exact size are in releases/manifest-0.1.1.json and SHA256SUMS-0.1.1.txt. The earlier 0.1.0 installer remains unchanged.

The NSIS build and silent installation completed with exit 0 on Windows 11 build 26200 x64. Seven final installed workflow checks passed, no page errors. Electron 44.7.2 includes Node 24.21.0. This is an actual installed executable, not development Electron. The installer is unsigned; no OS protections were bypassed, second-machine install or native signing claimed.

The installed app opens the corrected live 800-unit packet and receipts offline against unreachable port 9 with child PATH restricted to C:\Windows\System32. Native file reading and packet validation execute; selection in automated checks/media is stubbed. Actual OS import/save/reopen passed previously at ed6a2b0 with 0.1.0. A real-dialog recheck of this exact 0.1.1 binary remains a human release action.

Current backend origin is loopback 8787. New inference/review/action requires the local Python backend. The renderer does not contain AMD credentials, Python or weights. Before external distribution, authorize/configure BATCHFENCE_BACKEND_ORIGIN to the chosen HTTPS host, rebuild, reinstall and recheck; do not advertise the local installer as a hosted service.

The same sandboxed, context-isolated fixed-origin transport and bounded native file bridge remain. Session capabilities stay in main-process memory and do not transfer in packets. Offline review is historical and read-only; promotion strips prior authority.

Rebuild with npm run package:desktop. Install to the project test directory, then set BATCHFENCE_TEST_EXE and run scripts/desktop-smoke.cjs and scripts/desktop-offline.cjs. Keep cache locations on D. No installer/download publication occurred.
