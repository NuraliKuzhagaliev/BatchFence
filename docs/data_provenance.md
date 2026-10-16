# Data provenance

All fixture company names, notices, records, order dates, inventory and prices are synthetic. They describe a non-safety-critical cosmetic coating problem in decorative housings at fictional Northstar Enclosures. No customer record, supplier communication or field outcome was used.

The main fixture follows the supplied master specification. inventory.csv contains the six current terminal pools and integer unit carrying values. lineage.csv contains confirmed and possible relations with row IDs and revisions. order_allocations.csv allocates existing stock, not additional inventory. Supporting TXT documents record the bounded completeness assumption and unresolved original receipt.

Ground-truth classification sets for 30 separate graph cases were authored as literal sets in scripts/freeze_eval.py independently of the traversal implementation. The generator never imports the engine. Each of six buckets contains three development cases and two held-out cases. evals/manifest.json freezes SHA-256 values before the first evaluation. Expected currency accounting is computed independently from those literal membership sets.

This is a single-author synthetic check, not independently audited industrial ground truth. The held-out results have now been inspected. Do not tune on them and continue calling them untouched. No model prompt tuning took place on held-out model outputs because live inference was unavailable.

The adversarial bucket tests malformed graph/record integrity. Prompt injection and citation rejection are separate provider tests. The 30-case domain evaluation must not be described as 30 live narrative-extraction tests.

System fonts are used. Product screenshots depict this actual local application. No customer logos, awards, endorsements or measured customer ROI are claimed.
