# CPN Seed Treatment Database

The uploaded EPA APPRIL workbook is now loaded. Open **CPN_Seed_Treatment_Preview.html** for the standalone searchable database. Despite its retained filename, it contains the imported EPA catalog, not the earlier seven-example dataset.

## Side-by-side comparison matrix

Open **Comparison matrix** to select up to four formulations. Compare first-registration/status/label dates, ingredients, FRAC/IRAC codes, target pests, label specifications, warnings. Search and add directly in this tab, or use the product-list Compare checkboxes. Export the selected matrix to CSV or use Print / Save PDF. Efficacy is excluded.

First-registration dates and EPA pest indexes now come from the workbook. Crop-specific label extracts cover two registrations; unreviewed details stay explicitly marked. [How to use the matrix and interpret its sources](COMPARISON_MATRIX.md).

## Initial imported snapshot (October 19, 2026)

- **880 active registrations**, covering all 14 requested seed-treatment sites.
- **366,837 source rows** checked; 886 active registrations matched the site scope; six deltamethrin records excluded.
- 693 Section 3 registrations and 187 distributor registrations, retaining full EPA numbers.
- 185 distributor formulations explicitly linked to related EPA base registrations. Their crop sites and status come from the distributor's own row, not from the base product.
- Two records have no available formulation and cannot be independently checked for deltamethrin. They remain listed with prominent missing-data flags: 5905-491-38167 and 5905-491-51036. One record, 7969-506, has an ingredient identity but no percentage.
- 187 distinct EPA ingredient codes. Unreviewed ingredient classifications remain unclassified.
- Five exact-number Greenbook references and three CDMS references retained. These are saved observations, not live source connections.

The workbook's creation metadata is **September 21, 2026, 11:58:19 UTC**. It was reimported **October 19, 2026**, with a blank status-date start and October 19 cutoff. The newly supplied file is byte-for-byte identical to the previous upload: no registrations or product facts changed. The creation date is not a verified “current through” date. At the initial file import, EPA's live download had not been verified. For subsequent automatic retrievals, consult the Actions runs and the interface's actual source-check dates. Source row numbers, workbook SHA-256, counts by site, exclusions, and date provenance are in `static/epa-import-audit.json` and the interface's Sources & updates tab. The October 19 comparison is recorded in `data/refresh-history/2026-10-19.json`.

## Use the database

### Product label downloads

Each product card, detail view and comparison column provides **Open / download label (PDF)** when the EPA export supplies a matching file, or **Find product label** when a lookup is needed. The October 19 catalog has 628 direct EPA PDFs and 252 lookup-only records. PDFs open at EPA in a new tab; use the browser's PDF download/save control. Documents require internet access even when the catalog HTML is saved locally.

**Export label links** downloads one CSV row per matching product across every results page. Reset filters first to include all 880 records. The file contains direct PDF URLs where available, dates, EPA lookup links, full registration numbers and retrieval instructions; it is a link index, not a ZIP of PDFs.

PDF buttons only use existing EPA URLs matching the full registration and file date. Distributor records retain their full numbers and use EPA search plus instructions to obtain the marketed label from the registrant; a base label is never presented as the distributor label. EPA documents may include master, supplemental or historical labeling. Check the marketed container label, seed tag and state requirements. Existing Greenbook/CDMS references remain unchanged.

The lookup URLs follow [EPA's documented PPLS linking format](https://www.epa.gov/pesticide-labels/pesticide-product-label-system-ppls-more-information). Source refreshes automatically update the available PDF links from the workbook. The tool does not download/rehost label files or claim every external link has been checked live.

Search primary/alternate product names, EPA numbers, ingredient names, and reviewed mode-of-action groups. Select any combination of the 14 exact EPA sites. Filter by EPA product category, technology type, company, ingredient quality, or actual EPA status date. Results display 25 at a time. Compare up to four products and export all filtered results, not just the visible page, as CSV.

The complete matching export can include plant-incorporated protectants and products with other uses as well as conventional seed-treatment formulations. Inclusion is based on the requested EPA fields. EPA product category is not a claim that each ingredient has that function or that the category describes every seed-treatment use. Follow the label for crop and pest uses. Commercial package recipes are not inferred from product names.

## Automatic updates

The repository includes an enabled GitHub Actions schedule in `.github/workflows/seed-database-update.yml`: **Mondays at 6:37 a.m. America/Chicago**, plus **Run workflow** and an initial run when updater code is pushed. It checks EPA's weekly APPRIL Excel export. The latest run status, not the presence of this file, establishes whether source retrieval succeeded. [View update runs](https://github.com/danieham-97/crop-protection-network/actions/workflows/seed-database-update.yml).

`scheduled_update.py` downloads and validates the entire workbook through the existing parser, compares it to the published catalog, and records added/changed/removed scoped registrations in `static/update-history.json`. An unchanged workbook does not become a new release unless provider, classification, state, reviewed-reference content, or automation metadata changes. Every check updates `static/sync-status.json`. Successful validated changes rebuild both downloadable HTML files and are committed to GitHub. The job does not deploy the CPN website; hosting must consume these published files. Downloaded HTML copies remain fixed snapshots.

A fresh runner seeds its checks from the committed catalog, so older workbooks and loss of more than 30% of registrations cannot bypass the existing safeguards. Source failures preserve the last published catalog and record a failed status. A failed validation/build prevents the candidate from reaching GitHub. The worker upserts full EPA registration identities into a persistent SQLite product table, retaining out-of-scope records and before/after changes. GitHub restores and saves this database as a 90-day Actions artifact after a successful publication. Git commits retain published catalog versions, and the latest 52 releases have a compact public change log. Raw workbooks and staging databases are temporary. See [WEEKLY_WORKER.md](WEEKLY_WORKER.md) for storage, recovery, and host setup.

EPA requires no credential. Live **Greenbook and CDMS updates are not connected yet**. Their public search pages are not assumed to be machine feeds. CDMS's terms require permission for database reuse, and TELUS offers a supported Label API. Configure authorized normalized exports using the repository secrets listed in [AUTOMATIC_UPDATES.md](AUTOMATIC_UPDATES.md); provider-native API mapping still requires the provider's documentation and access. The job refreshes configured feeds even when the EPA workbook is unchanged. Existing source observations retain their dates; newer EPA label references cause old reviewed label extracts to display a review warning.

## Run locally

Python 3.11+ and an IANA timezone database are sufficient. No Python third-party packages are required. Allow several minutes and reasonable memory for the large workbook.

```sh
# Import a supplied export without accessing the network.
python3 refresh_epa.py --workbook /absolute/path/to/apprildatadump_public.xlsx

# Fetch and import the official EPA workbook on a network-enabled CPN host.
python3 scheduled_update.py --db private/catalog.sqlite

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

The tests cover the actual workbook schema, exact sites including the embedded comma in edible soybeans, distributor provenance, missing data, exclusions, dates, failed refresh retention, rollback protection, and interface logic. Chromium browser checks are included in GitHub Actions; local browser installation is optional. See `VALIDATION.md` and `INTEGRATION.md`.

## Comparison fact sheet and product hazards

Open **Treatment guide** for the treatment-type comparison, FRAC/IRAC explanation, signal-word guide and BMPs. Download the printable PDF from that tab, including when using the offline HTML. Product filters, details, side-by-side comparisons and CSV exports now include separate resistance groups, EPA signal words and restricted-use flags.

There are 70 curated ingredient-name entries, covering 68 distinct ingredient codes in this EPA snapshot. Unreviewed ingredients stay unclassified. EPA hazard fields retain exact product-row provenance, with explicit `None` kept separate from missing data. Product-specific label precautions have not been independently reviewed. See [SAFETY_AND_GROUPS.md](SAFETY_AND_GROUPS.md) for sources, coverage and update behavior.

