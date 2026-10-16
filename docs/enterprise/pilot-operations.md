# Private pilot operations (development branch)

Public 0.2.0 remains the verified release. The new pilot profile is under acceptance; do not treat the foundation checkpoint as all four modules delivered. Initial supported scope is one organization/site on owner-controlled hardware. Tests also exercise a second organization/site. No production SaaS certification is claimed.

## Private setup

Run from the repository on the D: drive. Docker Desktop must be available to the authorized process. The earlier `npipe:////./pipe/dockerDesktopLinuxEngine` permission error was the execution sandbox: an authorized read reached Docker Desktop 4.91.0 / Engine 29.8.0 without permission changes. Existing unrelated containers were left untouched.

```
python -m scripts.pilot-config
docker compose -f ops/compose.pilot.yml up --build -d
docker compose -f ops/compose.pilot.yml exec app python -m scripts.pilot create-user --username YOUR_NAME --org northstar --site plant1 --roles administrator
```

The create-user command prompts twice without echo. Repeat for explicit reporter, quality_reviewer, release_approver and auditor roles as appropriate. Never assign default reusable passwords. Administrator does not imply operational review/release capability. Named test accounts do not prove independent review. The owner must create and accept real distinct identities before operational recovery.

The configuration generator refuses existing configuration and writes three ignored files under `work/pilot-config`: PostgreSQL initialization credentials, a migration-only connection, and a restricted runtime connection plus random session signing key. The app never receives migration credentials. The database has no published port. Web binds only `127.0.0.1:8788`. Source data, database and backup directories are under `work/pilot-data`. Linux bind mounts need owner-approved write access for application UID 10001; do not apply blanket permission changes. Windows desktop can use `BATCHFENCE_BACKEND_ORIGIN=http://127.0.0.1:8788` once client acceptance passes.

Configure the actual AMD endpoint/model/key privately in the app env file only after the owner approves the provider processing of the intended data. No private plant-data approval is inferred from synthetic testing. The pilot defaults to fixture mode with persisted 20 organization / 8 user live-job limits; failed/cancelled attempts count. Provider request fees/credits remain governed by existing authorized resources. Do not increase limits or buy resources automatically.

## Migration and rollback

Migration version 2 adds repository, membership/session, immutable audit, original-source and scoped record tables. Existing case/receipt JSON remains byte-identical. SQLite version 1 is backed up to `.pre-v2-backup` before upgrade. PostgreSQL DDL runs using the migration-only identity; the runtime has no schema DDL or audit UPDATE/DELETE privileges. App audit triggers are defense in depth, not protection from a database administrator.

To import an existing SQLite store into a fresh PostgreSQL pilot: set `PILOT_DATABASE_URL` privately to the migration connection, run `python -m scripts.pilot migrate`, then `python -m scripts.pilot migrate-sqlite --sqlite-source PATH`. The command backs up the source and refuses a nonempty target. Legacy anonymous owners/approvals remain inaccessible historical records; they are not assigned to a named user. Exported packets can create new drafts with no transferred approval authority. Old stores may lack original bytes; do not reconstruct and claim them as originals.

Rollback keeps the protected 0.2.0 code and its pre-migration store together. Never point old code at the new schema or replace active files while the application is running. Keep the current expanded branch and restored backup separately for investigation. Do not rewrite published tags.

## Backup and isolated restore

```
docker compose -f ops/compose.pilot.yml exec app python -m scripts.pilot backup --path /var/data/backups/UNIQUE-NAME.zip
```

Backup covers a consistent database snapshot, all referenced original source bytes, checksums and configuration **names**, not configuration secrets. It excludes active sessions. It contains document data and password hashes: restrict access and use an owner-controlled encrypted off-device destination. Same-disk persistence/backup is not disaster recovery. Environment secrets require a separate owner-managed secure recovery process.

Create a separate empty PostgreSQL database with the migration command, set its private runtime connection, then run:

```
python -m scripts.pilot restore --path PRIVATE-BACKUP.zip --source-directory NEW-ISOLATED-DIRECTORY
```

It refuses nonempty databases/existing source directories, checks archive paths/content, restores original bytes and all record values, and compares counts/content. Start a separately bound application with this database/source path; sign in again and verify receipts and a representative workflow. `python -m scripts.verify-pilot` exercises this against real isolated PostgreSQL databases using ignored evaluation configuration. Actual results: `foundation-postgres.json`. No RPO/RTO is claimed until owner targets and an off-device recovery drill are accepted.

## Boundaries and jobs

One committing writer is serialized across PostgreSQL web/worker processes using a transaction-scoped advisory lock. Model calls occur outside write transactions. This prioritizes correctness within a bounded pilot, not high-throughput claims. Jobs persist a single attempt, finite budgets and a 120-second lease. Cancellation suppresses result acceptance; it cannot undo a provider request already dispatched. An expired worker becomes interrupted and requires an explicit new request; no automatic paid retry or fixture fallback occurs.

Session lifetime is eight hours, HttpOnly/SameSite Strict, Secure on HTTPS. Membership changes revoke sessions and pending named authority. Server-side organization/site scope applies before object access. Document downloads are binary attachments after scoped lookup and hash verification. Local HTTP is loopback-only. Public TLS or remote plant deployment is a separate owner-reviewed operating decision.
