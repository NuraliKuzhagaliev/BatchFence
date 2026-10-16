# Limitations and release blockers

- AMD live inference is unverified because private endpoint/model/key/provider evidence are absent. Fixture extraction is synthetic deterministic parsing and accepts the documented вЂњAffected lots:вЂќ format. It is not a general natural-language model.
- Hosted web and public installer download are pending authorization and hosting access. Both clients currently use the local backend at 127.0.0.1:8787. A prepared Dockerfile is not a deployed service.
- The Windows x64 installer is unsigned. Installation and packaged runtime were tested on Windows 11 build 26200. Signing, a different physical computer, macOS/Linux and automatic updates are unverified.
- Native bridge file bytes/save/open passed automated installed-app tests with dialog result stubs. Actual OS dialog selection remained incomplete after native UI automation encountered desktop interaction/minimization. That acceptance gate remains open.
- The app uses anonymous session review, not verified enterprise identity. Desktop capability exists only in main-process memory; restarting the desktop app starts a new session. Use decision packets for historical handoff. Sessions do not synchronize automatically across web and desktop.
- Text/CSV records and selectable-text PDF are supported within bounded sizes. Image-only scans receive an explicit unsupported result. No OCR or arbitrary spreadsheet/PDF-table interpretation exists.
- Inventory, lineage and allocation CSV imports replace their respective reviewed datasets. Use the fixture headers. They are staged until review, preserve existing holds, and reject contradictions. This is a bounded exported-record workflow, not an ERP connector.
- Data and test cases are synthetic. No manufacturing professional has validated the workflow. No customer interview, measured operator speedup, production accuracy, financial savings or physical safety/compliance certification is claimed.
- Inventory outside the current evidenced scope is not certified safe. Completeness is an explicit reviewed assumption. Releasing existing held goods is unsupported.
- The desktop shell bundles a runtime and has a substantial installer size. Network is required for new analysis, approval and application. Offline packets are historical and read-only.
- Model citation validation establishes quote existence, not semantic entailment. Human review can still be wrong. LLM output cannot grant action authority.
- npm audit identified eight moderate advisories in the development-only Electron packaging dependency chain, originating in sprintf-js. Production dependency audit has to be recorded separately. No forced major/downgrade fix was applied blindly.
- The Docker daemon was not running. Container build/run verification and hosted restart checks remain incomplete.
- A silent recorded demonstration and editable deck are prepared. Final video/pitch review, public publication and event submission have not occurred.

Docker Desktop was launched but its Linux-engine pipe remained unavailable. No further unchanged retries were made. Clipboard copy failed in the initial installed check and passed after the bounded native-write fix; that initial failure is retained.
