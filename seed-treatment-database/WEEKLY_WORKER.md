# Weekly EPA worker

The Python worker runs in **GitHub Actions every Monday at 06:37 America/Chicago**, with daylight saving handled by the workflow timezone. It also supports **Actions → Seed database source updates → Run workflow**. GitHub can delay scheduled starts; check the run result and `static/sync-status.json` for actual execution.

Source: [EPA's static APPRIL Excel export](https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx). No EPA credentials or third-party Python packages are required. EPA publishes a complete workbook, so every run downloads and streams that workbook and computes a logical delta locally. There is no assumed EPA delta endpoint.

## What is updated

`scheduled_update.py` uses the existing importer and the new `record_store.py` to:

1. Validate the complete workbook, then apply the existing 14 seed-treatment sites, active-registration scope, and deltamethrin exclusion.
2. Match by the **full EPA registration number**, preserving distributor suffixes.
3. Insert new products and update changed product facts or status with SQLite `INSERT ... ON CONFLICT DO UPDATE`. Retrieval dates and source-row positions alone do not count as changes; unchanged product rows retain their `updated_at` value.
4. Retain products leaving scope with `in_scope = 0`. For previously tracked registrations, the full workbook supplies any explicit inactive status or changed site evidence. A missing row is recorded as unknown, never inferred to be cancelled. Reactivation updates the original row.
5. Commit the upserts, before/after change records, workbook identity, and run counts in one database transaction. Schema errors, old workbooks, configured-feed failures, or loss of more than 30% of current scoped registrations stop the update.
6. Publish validated `static/catalog.json`, audit, status, and change-history files. The existing browser application reads this JSON; it does not connect directly to SQLite. GitHub additionally tests browser behavior, rebuilds downloadable HTML, and commits the public outputs.

New inactive or unrelated EPA rows are not imported into this seed-treatment catalog. Existing Greenbook/CDMS references, scientific source distinctions, hazard notices, reviewed label information, and label links retain their current handling. Live provider feeds remain optional and unconfigured unless supplied separately.

## Persistent SQLite tables

| Table | Purpose |
| --- | --- |
| `products` | One row per full registration identity; current scope flag, latest observed EPA status, JSON product payload, fact hash, first-seen and last-change times. |
| `product_changes` | Registration, run ID, action, and before/after JSON for each material change. Actions: added, changed, removed, reactivated. |
| `worker_runs` | Successful database transactions, check time, source creation time/hash, and counts. An unchanged check still records a run. |
| `worker_state` | Last accepted workbook creation time and hash, used to reject older sources. |

For an archived product, `payload` is its **last in-scope product record**. Use `latest_status_group`, `latest_epa_status`, `latest_status_date`, `scope_reason`, and `source_observation` for the later observation. An old payload is not evidence of current registration or permitted use. Unknown status is SQL `NULL`.

Example read queries:

```sql
SELECT registration_number, name, latest_epa_status, updated_at
FROM products WHERE in_scope = 1 ORDER BY registration_number;

SELECT checked_at, workbook_created, counts_json
FROM worker_runs ORDER BY id DESC LIMIT 10;

SELECT registration_number, action, before_json, after_json
FROM product_changes WHERE run_id = (SELECT MAX(id) FROM worker_runs);
```

## Storage in GitHub

The workflow restores the newest unexpired `seed-catalog-sqlite` artifact from `master` and saves a replacement only after validation and public publication succeed. Workflow concurrency serializes these runs. The artifact contains `catalog.sqlite` and has **90-day retention**; it contains public source records, not credentials, and is not confidential storage.

On the first run, or if all artifacts have expired, the worker initializes from the committed public catalog. Initialization is counted separately from new EPA records. This recovers the current active catalog, but cannot fully reconstruct archived database rows or their detailed change history. Keep independent database backups if that history needs permanent retention. Git commits retain published catalog versions; public JSON retains the latest 52 release summaries. Raw source workbooks and staging databases are not retained by this workflow.

## Run on a CPN server instead

Requirements: Python 3.11+, timezone data, outbound HTTPS to EPA, a writable persistent database location, and Linux `flock` for the supplied wrapper. Use one publication writer. The GitHub workflow does not install a cron task on CPN's server.

From a checkout containing the current validated public catalog:

```sh
cd seed-treatment-database
python3 scheduled_update.py --db /persistent/cpn-seed/catalog.sqlite
```

The database must be outside the public output directory. `CPN_SEED_DB` also sets its location; the default is `private/catalog.sqlite`. Preserve this file across deployments and include it in host backups. For weekly execution, adapt `deploy/crontab.example` with the real `CPN_SEED_ROOT`, set `CPN_SEED_DB`, and run `deploy/run-update.sh`. The wrapper holds a lock through publication and preview generation.

On acquisition/validation failure, the published catalog and existing database records are retained. SQLite changes roll back together on a database error. Database and filesystem publication are separate: if writing public files fails after a database commit, rerun the worker to reconcile the JSON without duplicating product changes. Monitor the exit status and Actions result as well as the public status file.

This is the repository application's SQLite worker and static-JSON publication path. **No connection to a separate CPN CMS, PostgreSQL, or MySQL database has been configured.** CPN's developer can publish the generated static files, run this worker with persistent storage, or adapt the transactional upsert layer to the site's actual database once its schema and connection are known.

## Verification

Run `python3 test_project.py --require-node`. Dedicated worker tests cover additions, status changes, unchanged repeat runs, distributor identities, inactive/missing observations, reactivation, initialization, transactional rollback, older exports, excessive removals, and failed-download retention. The GitHub job also validates the refreshed catalog and runs Chromium interface tests before publication.
