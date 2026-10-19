# Opening and testing the imported database

The repository-root README contains the simplest Windows instructions. Open `CPN_Seed_Treatment_Preview.html` directly for an offline review, or run `python serve.py` from this directory for the hosted-style interface. Neither command refreshes source data.

## Automated checks

Run `python test_project.py` (Windows may use `py`). Python 3.11+ is required; JavaScript checks additionally use Node.js 22+. No JavaScript packages are needed for the logic tests. If the timezone check fails on Windows, run `py -m pip install tzdata` and rerun. Use `--require-node` to require the complete test suite.

The runner executes Python tests, rebuilds the offline HTML from `static/catalog.json`, and checks the interface logic. It reports failures with a nonzero exit status. Expected error messages from tests that deliberately simulate failed downloads do not indicate a failed suite; read the final `OK`/`PASS` status.

The original workbook is not required. The importer is exercised using small generated fixtures, while published-catalog checks inspect the actual included 880-record dataset. A successful unit test run does not establish current EPA availability or source licensing.

In GitHub, select **Actions → Seed database tests**. Pushes and pull requests touching this database trigger the workflow. **Run workflow** starts it manually. This workflow runs tests only and has read-only repository permission. It does not collect sources or deploy a website.

## Optional browser checks

The script `tests/ui_test.cjs` exercises the included snapshot in Chromium. It checks search, filters, pagination, comparisons, CSV download, desktop/mobile screenshots, and browser console errors. Its expected counts match the September 21 source workbook, reimported October 19; update the scenario if you intentionally import a different dataset.

From this directory, install the browser test dependency in your development environment:

```sh
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node tests/ui_test.cjs
```

On Linux, system dependencies may require `npx playwright install --with-deps chromium`. This installs development dependencies; it is not needed for ordinary use. Screenshots and CSV output stay in `.test-artifacts/`, which Git ignores. Browser checks have not been executed in the build workspace because its browser installation is unavailable.

## Source import checks

Use `python refresh_epa.py --workbook /path/to/apprildatadump_public.xlsx` to import a supplied full export, or `python refresh_epa.py` to retrieve the official EPA workbook on a host with source access. These commands do update the local catalog and private revision history. Run `python build_preview.py` afterward to rebuild the standalone file.

For an isolated source test that leaves the displayed catalog unchanged:

```sh
python refresh_epa.py --db private/source-test.sqlite --output private/source-test/catalog.json
```

Review the printed counts, `private/source-test/epa-import-audit.json`, and `private/source-test/sync-status.json`. An official download can take several minutes. A source failure preserves the preceding published catalog. The source test can contact configured enrichment feeds; leave the optional Greenbook/CDMS environment variables unset unless you intend to test those feeds too.

## Deployment is separate

Opening HTML or passing GitHub tests does not activate the daily source job. CPN hosting and the provider feeds still need configuration as described in `INTEGRATION.md`. GitHub code pages do not execute HTML/Python applications. The repository is not a live CPN deployment.
