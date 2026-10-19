# EPA source mapping and deployment

## Primary source: official APPRIL workbook

URL: https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx

The user supplied `apprildatadump_public(2).xlsx`. `appril_workbook.py` implements its observed schema, using the `ACTIVE_REGISTRATIONS5_PUBLIC_V` sheet. The SQL sheet is informational and is never executed. Despite the sheet name, the source contains both active and inactive registrations.

| Source field | Database use |
| --- | --- |
| REG_NUM | Full identity, including distributor suffix; normalize leading zeros only |
| REG_TYPE | Sec3 or DP; retain separately |
| PRODUCT_NAME / ABNS | Primary name / unsplit alternate-name search text |
| COMPANY_NAME | Registrant; missing values stay explicit |
| STATUS_GROUP | Exactly `Active`, displayed as Active Products |
| STATUS / STATUS_DESC | Preserve the underlying registration status |
| STATUS_DT | Actual status date; Excel date conversion with workbook date system |
| SITES | Exact matches to all 14 requested site names as an OR query |
| AIS | Ingredient name, EPA PC code, CAS number, and percentage |
| PEST_CAT | Source product categories, or explicitly identified related base categories |
| PESTICIDE_TYPE | Source technology type |
| MAX_LABEL_DT | Latest label date; never used as a status or update date |
| Workbook created metadata | Source provenance only; not proof of data currency |

Sites are case/whitespace insensitive, with comma boundaries; the comma within `Soybeans, Edible (Seed and Pod Vegetable) (seed treatment)` is part of the exact name. No broad crop-group expansion or extra crop names are added. The SITES column does not supply per-site approval flags or dates, so the UI calls these **EPA-listed sites**, not independently verified current label authorizations.

All rows are streamed and their sequential row numbers checked against the worksheet extent. Missing required columns, unexpected status groups, malformed ingredient strings, duplicate active identities, and truncated workbooks stop publication. `STATUS_GROUP=Active` includes the different active statuses in the source, including conditional registration. The start date is blank; the end date is the current date in America/Chicago on each run.

## Distributor records and missing source fields

The export leaves AIS blank for the 187 matching DP records. EPA's supplemental-distribution guidance identifies the base registration as the first two number components and requires the same composition, while allowing narrower claims on the distributor label:

https://www.epa.gov/pesticide-registration/pesticide-registration-manual-chapter-9-supplemental-distribution-registered

For 185 records, the same workbook supplies related base-product ingredients. The catalog retains the distributor's own identity, sites and status, and marks its ingredient basis as **Related EPA base registration**, with the base number and source row. This is a transparent relationship, not an exact-number Greenbook/CDMS join or evidence that every base use appears on the distributor label.

Two records have no available base formulation and remain missing-data records. They are included to preserve the active-product census; their deltamethrin check is explicitly unresolved. One otherwise parsed AIS entry has an empty percentage; it stays null, never zero or an invented value. A malformed, nonempty AIS value aborts the import rather than silently dropping a component.

Known deltamethrin is excluded by name, CAS 52918-63-5, or PC code 097805, including when discovered in a related base formulation. Products that have only grain-storage uses cannot match the exact site scope. Products with both storage and matching seed sites remain unless deltamethrin excludes them.

## Import and publish

```sh
python3 refresh_epa.py --workbook /private/apprildatadump_public.xlsx
python3 refresh_epa.py
```

With no `--workbook`, the importer downloads the official workbook over HTTPS with a 300 MiB compressed-size limit. Unexpected redirects are rejected for operator review. It never sends feed credentials to EPA. The expanded archive is bounded to 3 GiB. Downloaded temporary workbooks are removed after processing; retain source archives separately if CPN policy requires them.

The SQLite database contains revisions, change history and run outcomes. Reconciliation covers the entire catalog, including removals; it never relies solely on changed status dates. More than 30% of previous registrations disappearing stops publication. An operator may use `--allow-large-change` only after reviewing a legitimate source change. A workbook older than the previous creation date cannot overwrite newer data.

Public files are `static/catalog.json`, `static/epa-import-audit.json`, and `static/sync-status.json`. The catalog file is replaced atomically, so a reader sees either the old or the new catalog. Ancillary audit/status files follow separately. If the process stops between database commit and file publication, the next successful run repairs publication. Private SQLite is the revision authority. Do not expose it publicly.

A local upload is marked `snapshot` with an import date and no claimed official retrieval date. An actual successful EPA download is marked `live` with its retrieval time, while retaining the workbook's own creation date. Neither state by itself proves a cron job is installed. The standalone builder always labels its output as a fixed snapshot.

## Daily host schedule

Use `deploy/run-update.sh` and `deploy/crontab.example`. Set the real `CPN_SEED_ROOT` and path. The example is daily at 06:15 America/Chicago and requires cron timezone support plus Linux `flock`. Run once successfully on the host before installing the schedule. Confirm a failed refresh retains the prior publication. Connect the job exit status or `sync-status.json` to existing host monitoring if desired; this code sends no messages.

No live schedule was installed here. Workspace network restrictions prevented testing the official download. All initial data came from the user-supplied workbook. The hosted UI checks published catalog updates every five minutes. This does not make an offline HTML file or the original CPN website update automatically.

## Greenbook and CDMS

`data/source-references.json` preserves the previously reviewed exact-number links and their original observation dates. Five Greenbook and three CDMS records match this EPA catalog. Unmatched example products are not added to the EPA census. These static references are visibly labeled and never treated as newly fetched.

For live enrichment, supply `GREENBOOK_FEED_URL` and/or `CDMS_FEED_URL`, or use `--greenbook` / `--cdms` with normalized JSON files. Optional bearer tokens use the corresponding `_TOKEN` environment variable. CPN must obtain supported source access; the public home pages are not asserted to be API endpoints. TELUS describes a supported agriculture label API at https://www.telus.com/agcg/en/agriculture/agriculture-api . No endpoint schema or credentials were provided here.

Normalized enrichment contract (our schema, not the provider's native API):

```json
{
  "schema_version": 1,
  "source": "CDMS",
  "retrieved_on": "YYYY-MM-DD",
  "products": [{
    "registration_number": "full EPA registration number",
    "name": "source product name",
    "source_url": "https://www.cdms.net/labelsSDS/home/prodidx?key=provider-id",
    "source_updated": null,
    "ingredient_basis": "label",
    "ingredients": [{"name": "ingredient", "percent": 1.0}],
    "documents": [{"type": "specimen_label", "url": "https://www.cdms.net/ldat/document.pdf", "date": null}]
  }]
}
```

For Greenbook use `source: Greenbook` and Greenbook URLs. Join full EPA numbers only. EPA formulation wins; conflicts are flagged. Feed retrieval dates may be no more than seven days old or future-dated. A configured feed failure prevents publication and retains previous data. Unconfigured feeds remain explicit saved-reference or disconnected states.

Allowed document types are `specimen_label`, `supplemental_label`, and `sds`. SDS composition is not assumed to equal a complete active-ingredient statement. Provider revision identifiers remain distinct from dates. `sources.py` includes an older optional Greenbook HTML collector and PPIS staging collector; neither is the primary EPA updater, and neither has been verified live here.

`catalog.py` also retains the earlier strict normalized APPRIL JSON adapter for a future supported API integration. The actual workbook path uses `refresh_epa.py` and its explicit source semantics, not fabricated per-site approval flags. Do not run both import routes concurrently.

## Remaining CPN integration

Deploy the static catalog in the CPN CMS or approved hosting environment and install the scheduler. Confirm live source reachability and provider feed arrangements. Complete browser/accessibility QA on that host. Reviewed ingredient classification coverage can be expanded using authoritative references. Commercial package versions and nonregistered components require their own manufacturer evidence and are not inferred from this registration inventory.
