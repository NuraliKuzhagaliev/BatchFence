# BatchFence

BatchFence helps a quality manager reconcile a supplier defect notice with exported inventory and production lineage. The working prototype links proposed lot scope to exact source passages, keeps unresolved receiving identity visible, and calculates the required hold under an explicit containment policy.

In the disclosed synthetic Northstar Enclosures scenario, the first notice produces 400 documented units and 100 uncertain units, so the plan holds 500 of 1,200 units. A supplier correction adds a branch and raises the hold to 800. Three then four allocated open orders need review. An evidence request identifies 100 units whose receiving identity remains unresolved.

Human approval binds exact evidence, inventory, policy and actions. Server-side checks reject stale or edited requests. An atomic SQLite transaction writes a real sandbox receipt. A shared React workbench runs in the browser and an installable Windows shell. Versioned packets preserve evidence and receipts for offline read-only review.

The local web and installed desktop fixture flows have been tested. The server-side AMD adapter is implemented, but private endpoint access was unavailable and no successful live AMD request is claimed. Hosted distribution, actual native dialog acceptance and final submission remain open. All data are synthetic. Carrying value excluded from a proposed hold is not measured savings. This prototype does not certify safety or compliance.
