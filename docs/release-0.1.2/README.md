# BatchFence 0.1.2 — Windows and web presentation

The website offers Download for Windows. The installed app offers Open web app and has no download button. Redundant SANDBOX, demo, Human review slogan and footer version/platform badges are removed. Temporary storage, synthetic/recorded provenance and workspace-only action scope remain explicit.

The Windows x64 installer connects to https://batchfence.onrender.com without requiring local Python or a localhost server. The protected Live access key is passed only to the fixed backend analysis route; it is not bundled. Recorded packets now use the restricted desktop transport. Open web app delegates only the fixed public URL to the OS browser.

## Actual verification

- 52 pytest passed; 30/30 frozen deterministic domain scenarios passed.
- 12 web workflow checks; desktop/mobile landing inspection and platform-specific buttons.
- Installed 0.1.2: seven checks against the hosted backend, synthetic 500/800, stale approval, actual receipt/export, transport isolation and packet validation. Offline packet reading passed with no backend and restricted PATH.
- A fresh cloud MiMo-V2.6-Flash request from the installed app succeeded in 16,314 ms and populated source-backed, unresolved SUP-A candidate facts. This extra check performed no review or receipt. Raw response and qualifier ambiguity are preserved in desktop-live-candidates.json; it is not independent human validation.
- Wrong Live access key denied before model execution. Foreign URLs, write to replay, malformed and oversized token inputs rejected through the native bridge. Node and raw IPC remain unavailable to the renderer.
- Native file bytes/export/import execute in installed workflow tests, with file selection dialogs stubbed. No new physical Windows file-dialog acceptance or second-machine test is claimed.
- Installer ran with exit 0. Installed app.asar matches the build; known configured secrets absent. Get-AuthenticodeSignature returns NotSigned. No OS protection was bypassed.

## Limits

The installer is unsigned. Windows may show a publisher warning. Hosted SQLite remains temporary and records can be lost on inactivity, restart or redeployment; export packets. Holds update this workspace's inventory only, not an external inventory system. Existing AMD trial resources only; no purchase, account upgrade or paid signing/hosting.

The original local 0.1.0/0.1.1 installers and evidence remain unchanged. New release URLs and download digest are in installer.json; public availability is verified separately after upload. This release does not establish production readiness or independent domain validation.

## Published download

[Windows 0.1.2 and checksums](https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.1.2) are public. The complete anonymous download matches the original installer hash. See public-release.json. The first upload timed out; bounded streaming succeeded without any resource/permission change.
