# Crop Protection Network — Seed Treatment Database

Start with **[seed-treatment-database](seed-treatment-database/)**. This is the database prepared in this project, including **880 active EPA registrations** from the supplied workbook, exact filters for the 14 requested sites, ingredient details, comparison, CSV export, and the EPA workbook updater.

The workbook creation metadata is **September 21, 2026**; the included snapshot was reimported **October 19, 2026**, with a blank status-date start and an October 19 cutoff. The newly attached workbook is byte-for-byte identical to the earlier upload, so the 880 registrations and their product information are unchanged. EPA's current download could not be retrieved in the build workspace; this is not a verified latest-release update. Opening or testing it does not refresh EPA data. Six known deltamethrin records were excluded. Two formulations and one percentage are missing and visibly flagged. Greenbook/CDMS references are saved observations, not active data feeds.

## Open it immediately — no installation

1. On this repository page, select **Code → Download ZIP**.
2. In Windows, right-click the downloaded ZIP and select **Extract All**.
3. Open the extracted folder, then open **seed-treatment-database**.
4. Double-click **CPN_Seed_Treatment_Preview.html**. It opens in your web browser with the complete imported snapshot.

Use the downloaded file to open the interface. GitHub's file page displays HTML source code rather than running the application. The retained “Preview” filename contains the actual imported catalog, not fictional examples.

The interface includes the supplied CPN logo, its green/lime/yellow palette, and matching sans-serif styling. The standalone HTML embeds its logo and heading font for offline use. Roboto Condensed is an approximation pending CPN's exact font specification; see [appearance details](seed-treatment-database/BRANDING.md).

## Treatment comparison and warnings

Open **Treatment guide** for a comparison of five treatment types, FRAC/IRAC guidance, EPA signal words and BMPs. [Download the three-page fact sheet](seed-treatment-database/static/assets/CPN_Seed_Treatment_Comparison.pdf), or use the PDF button inside the app. The standalone HTML includes the PDF for offline use.

New filters and comparison/export fields show FRAC fungicide groups, IRAC insecticide groups, EPA signal words and restricted-use flags. The reviewed reference covers 68 distinct ingredient codes; unmapped ingredients remain unclassified. Product-specific label precautions still require current-label review. [Coverage and update details](seed-treatment-database/SAFETY_AND_GROUPS.md).

## State feature

Choose a state to filter provider availability or state-authority registration evidence. Each product has a table for all 50 states, D.C. and Puerto Rico, with source and date details. Comparisons and CSV exports include state evidence.

**Coverage is partial:** three registrations have CDMS availability observations; no official state approvals have been independently verified. Other products show **Not verified**. The feature supports a separate authorized state feed for scheduled updates. [State coverage and setup](seed-treatment-database/STATE_REGISTRATIONS.md).

## Try these checks

| Check | Expected result for the included snapshot |
| --- | --- |
| Open the database | 880 products total; 25 on the first page |
| Search `100-1508` | Cruisermaxx Vibrance; four EPA active ingredients |
| Reset, then select Barley (seed treatment) | 299 matching registrations |
| Select Related base formulation under Ingredient data | 185 distributor records |
| Select two products and choose Compare | Side-by-side ingredients and source information |
| Export results | All filtered products, including results on other pages |
| Filter EPA signal word to None reported by EPA | 25 records; distinct from the 187 missing signal words |
| Filter EPA restricted-use flag to Yes | 19 records in the supplied workbook |
| Open Treatment guide | Comparison, signal words, BMPs and downloadable PDF |
| Open Sources & updates | Source date, import date, 14-site counts, and update status |

Product counts can change after an intentional import of a newer workbook.

## Run the hosted-style version locally

Install **Python 3.11 or newer** from https://www.python.org/downloads/ . No Python installation is needed for the immediate HTML preview above.

On Windows, double-click **START_DATABASE.bat** in the repository's outer folder. It starts a local server and opens the browser. Keep its command window open; press **Ctrl+C** in that window to stop the server.

Alternatively, open a terminal in the repository's outer folder:

```powershell
# Windows
py seed-treatment-database/serve.py
```

```sh
# macOS / Linux
python3 seed-treatment-database/serve.py
```

Open **http://127.0.0.1:8080** if the browser does not open automatically. If port 8080 is already in use, add `--port 8081` and use the displayed address. This server exposes only the application's static files and runs on your computer. It does not activate source collection or publish a CPN website.

## Run automated tests

On Windows, double-click **TEST_DATABASE.bat**, or run:

```powershell
py seed-treatment-database/test_project.py
```

On macOS/Linux:

```sh
python3 seed-treatment-database/test_project.py
```

This runs the Python importer/publication tests and rebuilds the standalone preview. If **Node.js 22 or newer** is installed, it also runs the JavaScript interface-logic tests. The test runner reports a clear skip when Node is absent. Node is only required for JavaScript development tests, not to open the tool.

The GitHub **Actions → Seed database tests** workflow runs the full Python and JavaScript checks on pushes and pull requests. To start a run manually, select that workflow, then **Run workflow**. A green check means the automated checks passed. These checks do not fetch new EPA data or prove live provider access.

Optional real-browser testing instructions are in [TESTING.md](seed-treatment-database/TESTING.md). The mocked-DOM checks do not substitute for browser/accessibility review.

## EPA updates and CPN hosting

The EPA collector and the daily host schedule are included. Run on a network-enabled host:

```sh
cd seed-treatment-database
python3 refresh_epa.py
python3 build_preview.py
```

For a workbook already on your computer, use `--workbook /path/to/apprildatadump_public.xlsx` (Windows: `py refresh_epa.py --workbook "C:\path\apprildatadump_public.xlsx"`). This changes the local catalog; it does not automatically commit the data to GitHub.

**GitHub Actions testing is active when GitHub runs the workflow; automatic EPA/Greenbook/CDMS collection is a separate setup.** The daily EPA host job is not installed by uploading this repository. Live Greenbook and CDMS updates still require supported feeds and configuration. The project does not publish a GitHub Pages site or replace the existing CPN website by itself.

Deployment details: [integration guide](seed-treatment-database/INTEGRATION.md), [project README](seed-treatment-database/README.md), [source references](seed-treatment-database/SOURCES.md), and [validation record](seed-treatment-database/VALIDATION.md).

## Repository layout

- `seed-treatment-database/`: imported EPA database, interface, updater and tests. **Use this folder for the instructions above.**
- `.github/workflows/seed-database-tests.yml`: automated checks for the imported database.

Only the selected public EPA catalog and reviewed reference links are committed. Original bulk workbooks, private SQLite histories, credentials and local test output are excluded by ignore rules. No open-source license or CPN endorsement is asserted by this repository.
