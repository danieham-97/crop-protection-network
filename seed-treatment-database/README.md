# CPN Seed Treatment Database

The uploaded EPA APPRIL workbook is now loaded. Open **CPN_Seed_Treatment_Preview.html** for the standalone searchable database. Despite its retained filename, it contains the imported EPA catalog, not the earlier seven-example dataset.

## Imported data

- **880 active registrations**, covering all 14 requested seed-treatment sites.
- **366,837 source rows** checked; 886 active registrations matched the site scope; six deltamethrin records excluded.
- 693 Section 3 registrations and 187 distributor registrations, retaining full EPA numbers.
- 185 distributor formulations explicitly linked to related EPA base registrations. Their crop sites and status come from the distributor's own row, not from the base product.
- Two records have no available formulation and cannot be independently checked for deltamethrin. They remain listed with prominent missing-data flags: 5905-491-38167 and 5905-491-51036. One record, 7969-506, has an ingredient identity but no percentage.
- 187 distinct EPA ingredient codes. Unreviewed ingredient classifications remain unclassified.
- Five exact-number Greenbook references and three CDMS references retained. These are saved observations, not live source connections.

The workbook's creation metadata is **September 21, 2026, 11:58:19 UTC**. It was imported **October 16, 2026**, with a blank status-date start and October 16 cutoff. The creation date is not a verified “current through” date. No claim is made that the uploaded file is the latest EPA release today. Source row numbers, workbook SHA-256, counts by site, exclusions, and date provenance are in `static/epa-import-audit.json` and the interface's Sources & updates tab.

## Use the database

Search primary/alternate product names, EPA numbers, ingredient names, and reviewed mode-of-action groups. Select any combination of the 14 exact EPA sites. Filter by EPA product category, technology type, company, ingredient quality, or actual EPA status date. Results display 25 at a time. Compare up to four products and export all filtered results, not just the visible page, as CSV.

The complete matching export can include plant-incorporated protectants and products with other uses as well as conventional seed-treatment formulations. Inclusion is based on the requested EPA fields. EPA product category is not a claim that each ingredient has that function or that the category describes every seed-treatment use. Follow the label for crop and pest uses. Commercial package recipes are not inferred from product names.

## Automatic updates

**The EPA updater is implemented. A live CPN schedule is not activated.**

`refresh_epa.py` downloads the official APPRIL workbook, streams every row, applies the same scope, preserves full registration identities, checks known deltamethrin exclusions, and reconciles the catalog. SQLite retains revisions and added/changed/removed records. Failed downloads, schema errors, malformed ingredients, older workbooks, or excessive record loss preserve the last published catalog.

The included host schedule polls daily at **6:15 a.m. America/Chicago**. It picks up changes after EPA republishes its workbook; it is not an instant update trigger. The hosted interface checks the published JSON every five minutes. The standalone HTML remains a fixed snapshot.

The CPN host must install the project and schedule. Live Greenbook/CDMS refreshes additionally require supported, authorized feeds; saved references are never restamped as newly retrieved. No hosting credentials or connection were supplied in this conversation, and the live EPA download could not be tested through this workspace's restricted network.

## Run locally

Python 3.11+ and an IANA timezone database are sufficient. No Python third-party packages are required. Allow several minutes and reasonable memory for the large workbook.

```sh
# Import a supplied export without accessing the network.
python3 refresh_epa.py --workbook /absolute/path/to/apprildatadump_public.xlsx

# Fetch and import the official EPA workbook on a network-enabled CPN host.
python3 refresh_epa.py

# Build a new standalone snapshot after importing.
python3 build_preview.py

# Serve the hosted form locally.
python3 -m http.server 8080 --directory static
```

Deploy only `static/` publicly. Keep scripts, source files, credentials, SQLite, and logs outside the web root. Configure `CPN_SEED_ROOT` and install `deploy/crontab.example` with the real absolute path. `deploy/run-update.sh` uses Linux `flock` to avoid concurrent writers. Back up the private SQLite database.

```sh
python3 -m unittest discover -s tests -v
node tests/logic_test.cjs
```

The tests cover the actual workbook schema, exact sites including the embedded comma in edible soybeans, distributor provenance, missing data, exclusions, dates, failed refresh retention, rollback protection, and interface logic. Browser rendering tests are supplied but were not run because this workspace has no installed browser. See `VALIDATION.md` and `INTEGRATION.md`.
