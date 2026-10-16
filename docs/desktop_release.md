# Windows release 0.1.1

Installer: releases/BatchFence-0.1.1-win-x64-setup.exe. Installed verification copy: work/installed-0.1.1/BatchFence.exe. SHA-256 and exact size are in releases/manifest-0.1.1.json and SHA256SUMS-0.1.1.txt. The earlier 0.1.0 installer remains unchanged.

The NSIS build and silent installation completed with exit 0 on Windows 11 build 26200 x64. Seven final installed workflow checks passed, no page errors. Electron 44.7.2 includes Node 24.21.0. This is an actual installed executable, not development Electron. The installer is unsigned; no OS protections were bypassed, second-machine install or native signing claimed.

The installed app opens the corrected live 800-unit packet and receipts offline against unreachable port 9 with child PATH restricted to C:\Windows\System32. Native file reading and packet validation execute; selection in automated checks/media is stubbed. Actual OS import/save/reopen passed previously at ed6a2b0 with 0.1.0. A real-dialog recheck of this exact 0.1.1 binary remains a human release action.

Current backend origin is loopback 8787. New inference/review/action requires the local Python backend. The renderer does not contain AMD credentials, Python or weights. Before external distribution, authorize/configure BATCHFENCE_BACKEND_ORIGIN to the chosen HTTPS host, rebuild, reinstall and recheck; do not advertise the local installer as a hosted service.

The same sandboxed, context-isolated fixed-origin transport and bounded native file bridge remain. Session capabilities stay in main-process memory and do not transfer in packets. Offline review is historical and read-only; promotion strips prior authority.

Rebuild with npm run package:desktop. Install to the project test directory, then set BATCHFENCE_TEST_EXE and run scripts/desktop-smoke.cjs and scripts/desktop-offline.cjs. Keep cache locations on D. No installer/download publication occurred.
