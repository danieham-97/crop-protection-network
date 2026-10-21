> **Current interface (October 21, 2026):** State filtering has been removed from Products and Compare at the user’s request. State evidence remains reference information in product details, comparisons and exports. Any earlier filter instructions below describe the previous implementation.

# CPN testing and website integration handoff

Updated October 21, 2026. Repository: https://github.com/danieham-97/crop-protection-network

Start with a staging copy. This project is a static browser interface with a separate Python data-update process. CPN's CMS and hosting arrangement have not been identified. GitHub Actions has a weekly EPA update schedule; no live CPN website deployment or connection to CPN's CMS database has been installed. See [WEEKLY_WORKER.md](WEEKLY_WORKER.md).

## Approved presentation update

The October 21 layout follows the approved streamlined mockup and retains the full catalog and tools. It includes Adam Sisson's photograph with Iowa State University credit, a catalog-derived description and citation, three main tabs, grouped filters/downloads, and the abbreviation, signal-word, warning, and handling guides. See BRANDING.md for assets and rollback instructions. The preceding version is preserved in `checkpoint/seed-tool-before-streamlining-2026-10-21`.

The interface changes do not deploy to the separate CPN website. Check the Seed database tests workflow on the presentation commit before deployment. The browser suite emits review screenshots and a matrix print sample as workflow artifacts.

## 1. Earlier verification

Application revision `9b0572374f528230d4d786d8aeb0f27415644c2b` passed 54 Python tests, JavaScript logic checks and Chromium browser checks:

https://github.com/danieham-97/crop-protection-network/actions/runs/39271261355

The browser checks include comparison selections, downloads, mobile overflow and print visibility. They do not establish complete accessibility compliance, support in every browser, source availability, or successful CPN hosting integration. The automated source tests use fixtures; they do not download live EPA data.

The included catalog contains 880 matching registrations from the supplied workbook, whose creation metadata is September 21, 2026. Its October 19 import does not establish that it is the latest EPA release.

## 2. Owner acceptance test: no installation

1. Open the repository, choose **Code → Download ZIP**, and extract the archive.
2. Open `seed-treatment-database/CPN_Seed_Treatment_Preview.html` in a browser. Open the extracted file, not GitHub's source-code page.
3. Work through this table. Record the browser, date, result and a screenshot for any failure. Reset filters between cases.

| Check | Expected result in the included snapshot |
| --- | --- |
| Initial product list | 880 products; 25 on the first page; Next displays the next page |
| Search `100-1508` | Cruisermaxx Vibrance and four listed active ingredients |
| Crop filter: Barley (seed treatment) | 299 matching registrations |
| Search `mefenoxam` | Finds products using the reviewed Metalaxyl-M synonym |
| Ingredient data: Related base formulation | 185 distributor records; full EPA numbers and base-source disclosure |
| Search `5905-491-38167` and open details | Missing ingredients and incomplete exclusion-check warning; no invented composition |
| Filter FRAC 4, then reset and filter IRAC 4A | Matching reviewed group assignments; FRAC and IRAC are kept distinct |
| Signal word: None reported by EPA | 25 records; different from the 187 Not supplied records |
| Restricted-use flag: Yes | 19 records in this workbook |
| Comparison matrix | Add `100-1648`, `7969-441`, `352-937` and `100-1508`; four columns in that order, with Add disabled at four |
| Remove and replace a comparison column | Remove one, search a replacement and add it; the remaining selections are preserved |
| Matrix contents | Separate first-registration, status and label dates; ingredients, codes, targets, label specifications and sources; no efficacy ratings |
| Label extracts | Saltro and LumiTreo have scoped soybean extracts; other formulations clearly show unreviewed/missing details |
| Matrix CSV | Contains only selected formulations, comparison notes and source URLs; check that commas/newlines do not shift columns |
| Print / Save PDF | Uses landscape, retains selected columns and readable headings; inspect the actual PDF for clipping and excessive blank space |
| Export results | Includes every filtered result, including products beyond the current page |
| Treatment guide | Displays treatment types, signal-word guidance and BMPs; downloads the three-page fact sheet |
| State evidence | Separates provider availability from state-authority reports; unverified is not treated as approval or rejection |
| Sources & updates | Displays workbook/import dates and discloses that the standalone file does not refresh |

Counts are tied to this included workbook. Investigate and reconcile changes after a legitimate new import instead of requiring the old counts forever. State observations can move to Review due as time passes; the included observations have a November 18, 2026 review deadline, not a legal expiration date.

Also try a phone-sized window, keyboard-only navigation, browser zoom, and the browsers CPN supports. Check tab order, tab switching, dialog close behavior, filter labels, comparison scrolling and source links. CPN should review terminology, branding and the remaining content gaps before public release.

## 3. Run the repeatable tests

The simplest option is GitHub: **Actions → Seed database tests → Run workflow → master → Run workflow**. Repository write access is required to start it. Inspect the failed step if a run turns red. This workflow tests code; it does not refresh sources or deploy the website.

For local testing, install Python 3.11+ and Node.js 22+ and run from the repository root:

```sh
python3 seed-treatment-database/test_project.py --require-node
```

On Windows, use `py` instead of `python3`. `TEST_DATABASE.bat` also runs the local tests, but permits JavaScript checks to be skipped when Node is missing. If Windows reports missing timezone data, run `py -m pip install tzdata`.

To test the hosted interface locally:

```sh
python3 seed-treatment-database/serve.py
```

Or double-click `START_DATABASE.bat` on Windows. Open http://127.0.0.1:8080 and keep the terminal open. Stop it with Ctrl+C. This server is for local development; use CPN's production web hosting for publication.

Local Chromium instructions are in [TESTING.md](TESTING.md). GitHub already installs its browser dependency. After changing data, update any snapshot-specific test expectations only after reconciling the new source.

## 4. Decisions for CPN's web developers

Please supply these project details through the normal developer workflow, without posting passwords or API keys in the repository:

- CMS and hosting platform, staging URL, proposed public route and deployment process.
- Whether an approved server can run Python 3.11+, has persistent storage and outbound HTTPS, and supports a scheduled task. The supplied shell wrapper additionally requires Linux `flock`; the cron example requires timezone support.
- Whether the update process can write the site's data directory directly or must publish through a deployment/upload step.
- Existing Greenbook and CDMS/TELUS data-service arrangements, provider documentation and access scope; identify who will implement the format adapters.
- Owners for data review, source failures, hosting maintenance and approval to replace/link the current What's on Your Seed page.

## 5. Recommended website integration

Publish the contents of `seed-treatment-database/static/` at a dedicated CPN route such as `/seed-treatment-database/` (proposed route, not an existing deployment). Preserve the relative layout:

- `index.html`
- `catalog.json`
- `sync-status.json`
- `epa-import-audit.json`
- `assets/` including the logo, Adam Sisson seed photograph and fact-sheet PDF

The trailing-slash route should resolve `catalog.json` and assets within the same directory. Keep these files together when moving the tool into the CMS. The hosted page fetches `./catalog.json`; it does not contain the embedded snapshot used in the standalone preview.

Expose only the public static directory. Keep Python scripts, the `data/` editorial references, `private/` SQLite history, logs, credentials and source archives outside the web root. The updater needs the complete project privately and permission to publish its outputs. Persist the SQLite history across deployments.

A dedicated route can be linked from the current What's on Your Seed page. If CPN requires embedding in an existing page, developers can evaluate an iframe or a CMS template integration on staging. Test framing policy, keyboard access, responsive sizing, downloads and printing; an iframe is not already configured by this repository.

Check the current inline JavaScript/styles against CPN's Content Security Policy. Adapt the application to permitted external files or approved hashes/nonces as appropriate; do not disable the site's policy to make the page load. A CMS editor may remove inline scripts, so pasting the entire HTML into a rich-text field is not a deployment plan.

Configure the server/CDN so catalog and status JSON responses are not stuck in a long-lived cache; `Cache-Control: no-store` is a straightforward starting policy for those changing files. Verify the actual served responses. The app requests fresh JSON and checks for a new published catalog every five minutes; a reload checks immediately. Replacing JSON on the updater machine alone will not update a separately hosted copy.

For code deployment, preserve the last published live catalog rather than overwriting it with the older committed snapshot. Use a release process that publishes compatible code and data together and can restore both. Rebuild the standalone HTML only if CPN also offers a downloadable snapshot.

## 6. Verify a real EPA update on staging

The implemented EPA source is its full APPRIL workbook, not automation of the public search-page dropdowns. From the application directory, start an isolated test with the optional provider feed variables unset unless those connections are intentionally being tested:

```sh
cd seed-treatment-database
python3 refresh_epa.py --db private/source-test.sqlite --output private/source-test/catalog.json
```

This makes an actual network request and writes separate test outputs. It does not replace `static/catalog.json`. Allow several minutes for a full workbook. Treat an unsuccessful download as a failed source connection, not a successful update because the old interface still loads.

Check the output files:

| Evidence | Required result |
| --- | --- |
| Command exit status | Zero and a success summary |
| `private/source-test/sync-status.json` | `state` is `success` with the current attempt time |
| `private/source-test/catalog.json` | `mode` is `live`; `meta.source_acquisition` is `Official EPA download`; `meta.source_checked` records the retrieval |
| `private/source-test/epa-import-audit.json` | Source SHA-256, workbook creation metadata, full row counts, exact-site scope, exclusions and published counts reconcile |
| Product samples | Compare exact registration numbers, ingredients, dates and matched sites against the downloaded source; reconcile additions/removals |

A successful check may return the same workbook and identical product facts. Retrieval time can advance without a new source release. Do not substitute retrieval time for workbook creation or label dates.

After the isolated test passes, run `python3 scheduled_update.py --db private/catalog.sqlite` in the staged deployment. If the web server serves this `static/` directly, the outputs are in place. If it serves another location, publish the generated catalog, audit and status files there using the developers' deployment mechanism. Only the catalog itself is replaced atomically by this code; coordinate multi-file publication in the hosting process.

Reload the staging page. Confirm that its served `catalog.json` and visible source dates match the successful run. Repeat with the scheduled task's service account and environment, not just a developer's interactive shell. Record one successful unattended execution at the intended schedule before describing automatic updates as active.

Use the existing fixture tests to confirm that failed downloads and malformed input retain the previous catalog. For an operational failure drill, use an isolated staging copy: confirm the failed job is detected, the prior data still displays, and the failure status reaches the hosted page. Never test by deliberately breaking production sources.

## 7. Connect Greenbook, CDMS and state data

The current saved Greenbook/CDMS references do not update themselves. `GREENBOOK_FEED_URL` and `CDMS_FEED_URL` expect the repository's normalized JSON contract described in [INTEGRATION.md](INTEGRATION.md), not the public website URLs and not an arbitrary provider API response.

Obtain supported source access, implement and test the adapter from each provider's format, and inject any credentials through the host's protected configuration. Use `GREENBOOK_FEED_TOKEN` and `CDMS_FEED_TOKEN` for the optional bearer authentication supported by this client. The normalized product source links must use the supported provider hosts.

For each feed, test an exact full-registration match, an unmatched registration, a distributor number and a conflicting formulation. Confirm the source dates remain intact and EPA formulation data takes precedence. A configured feed failure or invalid response blocks that catalog publication; verify the failure behavior and decide how the operations team will respond.

State registration requires the separate `STATE_REGISTRATION_FEED_URL` contract in [STATE_REGISTRATIONS.md](STATE_REGISTRATIONS.md). The included provider observations do not establish official state approvals. Label summaries, FRAC/IRAC assignments, BMPs and the fact sheet have an editorial review process; automatic EPA import does not rewrite them. The comparison module suppresses reviewed label extracts when a changed formulation, changed label reference or review deadline calls for review.

## 8. Install and verify the schedule

The GitHub source workflow runs Mondays at 6:37 a.m. America/Chicago. As an alternative for CPN hosting, the supplied `deploy/crontab.example` uses the same weekly schedule. It is a template only. Developers must set real paths, `CPN_SEED_ROOT`, and a persistent `CPN_SEED_DB` outside the web root, ensure the scheduler supports the timezone setting, and install it in the approved service account's scheduler. Make sure Python, timezone data, outbound access, write permissions and provider configuration are available in that environment.

`deploy/run-update.sh` uses a lock to prevent overlapping runs, then imports EPA and any configured feeds. If the website is hosted elsewhere, add a publishing step after successful generation, plus a way to deliver failure status while retaining the last good catalog. This publishing connection is not supplied for an unknown CMS/host.

Use existing host monitoring for failed jobs and missed runs. Distinguish last attempt, last successful retrieval, source workbook date and last successful public publication. A displayed success timestamp or an example cron file alone is not proof of an installed scheduler. The current UI also contains setup wording that developers should update to reflect the verified deployment, without claiming an unconfigured source is connected.

If the CPN web host cannot execute Python, use an approved external runner with persistent revision storage and a controlled publishing connection. The separate GitHub Actions source workflow already downloads EPA data, upserts SQLite, and commits validated public JSON. Its SQLite artifact has 90-day retention. Connect the published JSON to CPN hosting or implement an adapter for the actual CPN database; no CMS database connection is assumed. Avoid running both GitHub and host jobs as writers to the same publication.

## 9. Release acceptance

Ask the developers to return a staging URL and the completed owner-test table, plus:

- A passing code/browser test run and manual checks in CPN's supported browsers and accessibility process.
- One successful real source retrieval and one successful unattended scheduled run, with proof that the staged website serves the resulting data.
- Explicit status for each source: EPA, Greenbook, CDMS and state evidence. Sources still pending stay visibly pending.
- A tested failure/retention path, named maintenance owner, monitoring route, and documented code/data rollback.
- CPN editorial approval of data coverage, source wording and brand presentation, followed by CPN's normal production-release approval.

Useful repository documents: [TESTING.md](TESTING.md), [INTEGRATION.md](INTEGRATION.md), [COMPARISON_MATRIX.md](COMPARISON_MATRIX.md), [STATE_REGISTRATIONS.md](STATE_REGISTRATIONS.md), [SAFETY_AND_GROUPS.md](SAFETY_AND_GROUPS.md), [BRANDING.md](BRANDING.md).

Implementation references: [GitHub manual workflow runs](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [Python development HTTP server](https://docs.python.org/3/library/http.server.html), [MDN script CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src).

## October 21: state registration and proposed notice

The default state filter now requires both active federal status in the EPA snapshot and current state-authority registration evidence, including documented restricted registrations. Provider availability is separate and cannot establish approval. Zero state-authority records are currently loaded; see STATE_REGISTRATIONS.md for the feed contract and coverage limitation. Source details, restrictions and federal evidence are retained in comparison and CSV output. Optional effective dates are validated and future registrations do not qualify early.

LEGAL_NOTICE_DRAFT.md contains proposed data-accuracy and liability language, also visible as a draft in the tool footer. It is not an adopted CPN policy or a guarantee against liability. Institutional legal review is needed before public deployment. No new public CPN deployment or legal-policy adoption is performed by this repository change.
