# Opening and testing the imported database

The repository-root README contains the simplest Windows instructions. Open `CPN_Seed_Treatment_Preview.html` directly for an offline review, or run `python serve.py` from this directory for the hosted-style interface. Neither command refreshes source data.

Open `CPN_Design_Previews.html` for interactive desktop (1440px), tablet (768px), and mobile (390px) views of that same snapshot. Each view fits the available window and scrolls internally. These are working HTML previews, not captured screenshots. After rebuilding the snapshot, run `python build_design_previews.py` to regenerate this review file.

## Automated checks

Run `python test_project.py` (Windows may use `py`). Python 3.11+ is required; JavaScript checks additionally use Node.js 22+. No JavaScript packages are needed for the logic tests. If the timezone check fails on Windows, run `py -m pip install tzdata` and rerun. Use `--require-node` to require the complete test suite.

The runner executes Python tests, rebuilds the offline HTML from `static/catalog.json`, and checks the interface logic. It reports failures with a nonzero exit status. Expected error messages from tests that deliberately simulate failed downloads do not indicate a failed suite; read the final `OK`/`PASS` status.

The original workbook is not required. The importer is exercised using small generated fixtures, while published-catalog checks inspect the actual included 880-record dataset. A successful unit test run does not establish current EPA availability or source licensing.

In GitHub, select **Actions → Seed database tests**. Pushes and pull requests touching this database trigger the workflow. **Run workflow** starts it manually. This workflow runs Python, JavaScript and Chromium browser tests only and has read-only repository permission. It does not collect sources or deploy a website.

## Optional browser checks

The script `tests/ui_test.cjs` exercises the included snapshot in Chromium. It checks search, filters, pagination, comparisons, CSV download, desktop/mobile screenshots, and browser console errors. Its expected counts match the September 21 source workbook, reimported October 19; update the scenario if you intentionally import a different dataset.

From this directory, install the browser test dependency in your development environment:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node tests/ui_test.cjs
```

On Linux, system dependencies may require `npx playwright install --with-deps chromium`. This installs development dependencies; it is not needed for ordinary use. Screenshots and CSV output stay in `.test-artifacts/`, which Git ignores. The local build workspace has no browser installation. GitHub Actions installs Chromium and runs these checks on the published commit.

## Source import checks

Use `python refresh_epa.py --workbook /path/to/apprildatadump_public.xlsx` to import a supplied full export, or `python refresh_epa.py` to retrieve the official EPA workbook on a host with source access. These commands do update the local catalog and private revision history. Run `python build_preview.py` afterward to rebuild the standalone file.

For an isolated source test that leaves the displayed catalog unchanged:

```sh
python refresh_epa.py --db private/source-test.sqlite --output private/source-test/catalog.json
```

Review the printed counts, `private/source-test/epa-import-audit.json`, and `private/source-test/sync-status.json`. An official download can take several minutes. A source failure preserves the preceding published catalog. The source test can contact configured enrichment feeds; leave the optional Greenbook/CDMS environment variables unset unless you intend to test those feeds too.

## Deployment is separate

Opening HTML or passing GitHub tests does not activate the daily source job. CPN hosting and the provider feeds still need configuration as described in `INTEGRATION.md`. GitHub code pages do not execute HTML/Python applications. The repository is not a live CPN deployment.

## Treatment guide and state feature checks

- Filter FRAC to 4 or IRAC to 4A; inspect ingredient assignments and source versions.
- Filter signal word to None reported by EPA: 25 records. Not supplied: 187 records. Restricted-use Yes: 19 records.
- Open Treatment guide and download the PDF. It should have three pages, including the state-approval note.
- Select Iowa and Provider availability reports: three records while the included observations are within their review window. State-authority registration reports: zero. Other products remain Not verified. These are not current legal approval determinations.
- Open 7969-441 and expand its state table. Iowa shows a provider availability report; California a provider unavailability report. The source brand, observation date and incomplete verification note remain visible.
- A different distributor registration must not inherit these state statuses. Past a review deadline, observations should move to Review due rather than remain in positive results.

State logic tests use a fixed October 19, 2026 clock for the included observations; production uses the current date.

## Matrix checks

1. Open Comparison matrix and add `100-1648`, `7969-441`, `352-937` and `100-1508`. Four columns should appear in that order; Add is then disabled.
2. Remove a column, search `Ilevo`, and verify the exact `7969-441` match. Search a nonexistent name and verify that Add is disabled.
3. Check separate first-registration, status and label dates; expand the product-wide pest index. No efficacy row or score should appear.
4. Saltro and LumiTreo have reviewed soybean extracts, with sources and crop scope. Other products show an unreviewed state, never an assumed rate or PPE.
5. Export matrix CSV; it should include only selected formulations with source links. Print / Save PDF uses landscape and expands pest indexes.
6. At a narrow viewport, the matrix scrolls within the page; the page itself should not overflow.

Automated checks cover shared selections, the four-column cap, selection order, missing values, label changes, formula changes, distributor identity, review deadlines, CSV escaping and HTML escaping. Browser checks additionally cover downloads, print layout visibility and mobile overflow.

## Accessibility checks

The browser suite also checks the skip link, a single active tab stop, arrow/Home/End tab navigation, dialog heading focus and return focus, comparison checkbox focus, matrix header associations, mobile filter focus and Escape, 320px reflow, mobile crop/export visibility, and reduced-motion behavior. The JavaScript logic test uses DOM stubs and does not replace these browser checks.

The visual redesign adds browser checks for both hero search shortcuts, initially collapsed advanced filters, and successfully loaded decorative artwork. Expand **Company & ingredient evidence** before changing ingredient quality; state controls are under **State registration & availability**. All prior filter options remain available.

Redesign validation in the implementation workspace: 54 Python tests and the JavaScript catalog, comparison and CSV suites passed. A separate lightweight DOM harness passed 15 interaction workflows. The original embedded catalog, logo, font, fact sheet and existing control attributes were checked for equality. Sampled new small-text color pairs have contrast ratios from 5.69:1 to 10.39:1. These checks do not establish rendered layout or full accessibility conformance. Browser execution was unavailable in that workspace; the Chromium suite still requires a browser-enabled environment.

Before CPN publication, complete manual keyboard and screen-reader checks (including NVDA/Firefox or VoiceOver/Safari), 200% text enlargement, 400% zoom, text spacing, forced colors, and printed output. The interface improvements and automated checks are not a WCAG conformance certification. The existing embedded fact sheet is unchanged by the HTML accessibility update.

