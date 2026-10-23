# Validation — October 16, 2026

## Actual source import

The supplied 98,516,850-byte XLSX was read in full. Its registration worksheet has 366,837 data rows. An independent inspection pass and the production importer agree on all included registration IDs, exact matching sites, and converted status dates.

- 57,898 source registrations have STATUS_GROUP=Active; 308,939 are Inactive.
- 886 active registrations match at least one requested site.
- Six known deltamethrin records are excluded; 880 records published.
- 693 Sec3 records and 187 DP records; no duplicate full EPA identities.
- 185 DP formulations have explicit related-base provenance. Two DP formulations are unavailable, and their exclusion check remains unresolved.
- One record has a missing concentration; null is retained.
- All 14 site counts reconcile; counts overlap across sites.
- No displayed ingredient has the excluded deltamethrin name, PC code, or CAS number. This cannot independently clear the two missing-formulation records.
- Workbook creation metadata is September 21, 2026; import/cutoff is October 16, 2026. No live EPA freshness claim is made.
- The original uploaded workbook was not edited. Its SHA-256 is retained in the audit.

## Executed checks

36 Python tests passed. They cover the earlier feed adapters plus the real XLSX schema, exact edible-soybean name with its embedded comma, no crop-group expansion, full distributor identities, related-base formulations, deltamethrin exclusion through a base record, missing ingredients and percentages, Excel dates, changed columns, incomplete row extent, malformed ingredients, duplicate registrations, future/older workbooks, and failure preserving the last catalog.

JavaScript syntax and application logic passed in a mocked DOM using the actual 880-product catalog. Checks cover search, Metalaxyl-M/mefenoxam synonym search, crop and technology filters, EPA product categories, data-quality filters, dates, 25-record pagination, comparisons, source/date disclosure, missing-data warnings, HTML escaping, URL restrictions, CSV formula-cell protection, and exporting all filtered ingredient rows across all pages.

The production local-workbook command completed successfully and wrote the catalog, audit, status and SQLite revision. The standalone HTML embeds that imported catalog, with no external dependencies or live network calls.

## Limits

Real browser rendering/keyboard/accessibility checks were not executed because the workspace lacks an installed browser. `tests/ui_test.cjs` is updated for the imported catalog and can be run on a host with Playwright/Chromium. Mocked-DOM tests do not establish visual correctness.

The official EPA download was not tested successfully through the workspace's restricted network. Failure retention was tested with an injected download failure. The host schedule was not installed. Live Greenbook/CDMS feed refresh was not exercised; the existing source references retain their original observation dates.

Before publication on CPN, run the updater on the intended host, confirm source reachability and the weekly job, and complete browser/accessibility checks. No CPN deployment or source-provider credentials were available here.

## GitHub packaging — October 19, 2026

40 Python tests passed, including four checks on the complete committed catalog. The JavaScript interface and CSV checks passed. The new local launcher successfully served the interface and 880-record catalog over HTTP with no-cache headers and returned 404 for a private path. The one-command runner rebuilds the standalone file and detects missing Node/timezone dependencies. Real browser and Windows batch execution were not available here; their launch commands and Python target were inspected/tested separately.

The root README now provides download/open steps, expected manual checks, local launch commands, and GitHub Actions instructions. The existing repository application remains in its original folder. No EPA refresh was performed during repository packaging, and the original October 16 snapshot and September 21 source date remain unchanged.

## Workbook reimport — October 19, 2026

The newly attached `apprildatadump_public(1)(1).xlsx` was compared with the previous upload. Both are 98,516,850 bytes with SHA-256 `c8ae0c3f1d683914689d3b4e08904b4c617735b19120dc819412a70b652258bb`. They are byte-for-byte identical. The source creation metadata remains September 21, 2026, 11:58:19 UTC.

The production importer reread all 366,837 source rows with a blank status-date start and an October 19 cutoff. It published 880 registrations after six deltamethrin exclusions. A comparison of every product field, ignoring only the import timestamp, found zero additions, removals or changed product facts. SQLite's new revision likewise records zero substantive changes. The five Greenbook and three CDMS matches retain their exact prior values and observation dates. The two missing formulations and one missing percentage remain disclosed.

The public catalog, audit, import status and standalone HTML were rebuilt. Forty Python tests and the JavaScript interface/export checks passed against the rebuilt catalog. No new real-browser test was run. The detailed source comparison is in `data/refresh-history/2026-10-19.json`.

EPA's current download could not be retrieved in this workspace: the direct request returned HTTP 403, and the browsing reader could not import the XLSX response. No successful live retrieval date or latest-release claim was added. This refresh uses the supplied attachment; it does not establish that it is EPA's newest available data. The CPN source schedule remains unactivated.

## CPN appearance — October 19, 2026

Added the supplied CPN PNG logo at its original proportions and sampled its dark green, lime and yellow colors for the headers and accents. Updated the page background, section headings, navigation, cards and dialog typography. The heading font is locally bundled Roboto Condensed, a documented approximation pending CPN's exact font specification. Details and source references are in `BRANDING.md`.

The standalone builder embeds the exact logo bytes, complete font and font license. Checks confirmed that the standalone file needs no external image, script or font asset requests, and that the local server serves the logo, font and license correctly. The tested primary text/background pairs have contrast ratios from 5.04:1 to 7.15:1. This is a limited color check, not a complete accessibility audit.

All 40 Python tests and the JavaScript logic/export checks passed after the change. The application JavaScript and EPA catalog were unchanged. The original logo was inspected, but real-browser visual/responsive checks remain unavailable because this workspace has no installed browser executable. Responsive rules are included for desktop, tablet and phone widths.

## Treatment guide, groups and hazards — October 19, 2026

Re-read the full supplied EPA workbook with the production importer to retain signal words, restricted-use flags/reasons and exact-registration label filenames. The same 880 registrations and six deltamethrin exclusions remain. All 880 signal words, flags, reasons and source-row identities agree with an independent projection read from the workbook before implementation. Counts reconcile to 594 CAUTION, 41 WARNING, 33 DANGER, 25 explicit None and 187 missing; 19 restricted-use Yes and 861 No; 628 exact-registration label-file links.

Added 70 curated ingredient-name entries based on FRAC 2026 and IRAC v11.5, covering 68 distinct EPA ingredient codes in this snapshot. Other ingredients remain unclassified. Product hazards never inherit from related base formulations. Missing, unrecognized and explicit None signal values remain distinct. Label links reject unrelated registration numbers, malformed names, invalid dates and dates after the cutoff; distributor labels are not guessed.

All 45 Python tests passed, including new hazard provenance, label filename/date safeguards, classification-source consistency and published guide checks. JavaScript logic tests passed with the actual catalog, including exact FRAC/IRAC filters, missing versus None signal filters, restricted-use filtering, guide rendering, product/compare hazard display and new CSV fields. The embedded PDF download was checked in the standalone HTML. Optional Playwright checks were extended; they remain unexecuted because no browser executable is installed.

The three-page PDF was generated from the same guide content, rendered with Poppler and all three page images visually inspected. Tables, source links, headers, footer and pagination were readable without clipping. PDF and source dates are separate from EPA workbook freshness. The PDF is not a complete pesticide label or efficacy recommendation. Browser visual, accessibility and download interactions still need a host-side browser check. Neither CPN hosting nor live provider collection was activated.


## Comparison matrix update — October 19, 2026

The new tab compares up to four formulations and excludes efficacy ratings. The same uploaded workbook was reimported to retain `FIRST_REG_DT`, `PESTS`, `PHYS_FORM` and `USE_PATTERN`; the census remains 880. All 880 have a first-registration date; 879 have a product-wide pest index. These are separate from crop-specific label claims. Reviewed soybean label extracts are loaded for two exact registrations, with composition/version/review-deadline checks.

Local verification: 54 Python tests, standalone build and JavaScript interface logic passed. Matrix tests cover the four-selection cap, removal/order, missing data, exact distributor identity, changed-label and changed-composition guards, source links, CSV and escaping. The local environment has no Chromium executable. The GitHub workflow now installs Chromium and runs interaction, download, print-visibility and responsive checks; its run status is the authority for those browser checks.
