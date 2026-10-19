# Automatic source updates

## What is configured

The default-branch GitHub Actions workflow **Seed database source updates** runs **Mondays at 06:37 America/Chicago**, checks EPA's weekly Excel dump, and supports manual runs. It is also triggered by updater-code changes so the first connection can be tested immediately. It has repository-content write permission to commit validated data and failed-check status; it never deploys the CPN website or sends messages.

The source is EPA's public export:
https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx

EPA describes APPRIL's weekly Excel download at https://www.epa.gov/pesticide-science-and-assessing-pesticide-risks/databases-related-pesticide-risk-assessment . The importer streams the complete export, including inactive rows, then reconciles the exact active-registration and 14-site scope. It does not query only recent registration dates: doing that would miss amendments and removals.

GitHub schedules can be delayed, and public-repository schedules can be disabled after 60 days without activity. Inspect the Actions run and the tool's Sources & updates tab for actual check results. Repository rules, Actions being disabled, or denied bot pushes will surface as failed runs. No claim of a successful retrieval should be made from a configured schedule alone.

## Connecting Greenbook and CDMS

These connections are optional and currently unconfigured. The existing saved observations are retained, with their original dates. A successful EPA check does not imply a successful provider check.

| Repository secret | Expected value |
| --- | --- |
| `GREENBOOK_FEED_URL` | HTTPS endpoint returning an authorized normalized Greenbook export |
| `GREENBOOK_FEED_TOKEN` | Optional bearer token for that endpoint |
| `CDMS_FEED_URL` | HTTPS endpoint returning an authorized normalized CDMS/TELUS export |
| `CDMS_FEED_TOKEN` | Optional bearer token for that endpoint |
| `STATE_REGISTRATION_FEED_URL` | Optional separate authorized state-evidence export; see STATE_REGISTRATIONS.md |

Add credentials through GitHub **Settings → Secrets and variables → Actions**, never to code or public JSON. Feed URLs are also secrets so a private adapter address is not published. Redirects are rejected to prevent forwarding credentials to another destination.

These names refer to **this project's normalized JSON contract**, not undocumented native Greenbook/TELUS endpoints. An adapter must map the provider's documented response and combine every page before marking the export complete. Provider documentation, credentials, and reuse rights have not been supplied, so native API authentication and mapping cannot yet be verified.

CDMS terms: https://www.cdms.net/Terms . Its database-reuse clause requires permission. The supported integration offering is https://www.telus.com/agcg/en-us/agriculture/agriculture-api . Greenbook's public site offers account-based access at https://www.greenbook.net/ ; a supported automated export must be arranged with the provider. The scheduled job does not scrape either public search page, bypass logins, or automatically extract scientific application instructions from PDF text.

Example normalized provider export (example placeholders, not product facts):

```json
{
  "schema_version": 1,
  "source": "CDMS",
  "complete": true,
  "retrieved_on": "YYYY-MM-DD",
  "products": [{
    "registration_number": "FULL-EPA-NUMBER",
    "name": "Provider product name",
    "source_url": "https://www.cdms.net/labelsSDS/home/prodidx?key=PROVIDER-ID",
    "source_updated": null,
    "ingredient_basis": "label",
    "ingredients": [],
    "documents": [{"type": "specimen_label", "url": "https://www.cdms.net/ldat/PROVIDER-DOCUMENT.pdf", "date": null, "revision": "PROVIDER-REVISION"}]
  }]
}
```

For Greenbook use `source: Greenbook` and Greenbook source/document URLs. Scheduled exports must declare `complete: true`, contain at least one record, have no duplicate full EPA identities, and be retrieved within seven days with no future date. An incomplete page, malformed record, stale feed, older known provider revision, or configured-feed failure stops the release. Missing records remain dated saved references; absence is not interpreted as cancellation or unavailability. Whole-provider removal needs explicit editorial review rather than a silent empty-feed deletion.

EPA formulation, crop sites, registration status, and hazards remain tied to the EPA row. Conflicting provider values are flagged. Distributor numbers are never collapsed into base numbers for provider joins. Label/SDS revision identifiers are retained separately from dates. State availability reports do not become official state approvals. FRAC/IRAC assignments and crop-specific rate/PPE extracts retain their separate editorial review process; a new label is a review signal, not permission to reuse an old extract.

## Publication and recovery

1. Validate code and the currently published catalog.
2. Restore the last successfully published SQLite artifact, then create an isolated staging directory seeded from the published catalog.
3. Download and parse EPA, then refresh any configured normalized feeds.
4. Reject older exports, malformed or incomplete data, and more than 30% disappearance from the prior scoped catalog. The unattended job never sets `--allow-large-change`.
5. Compare factual content and workbook hashes, then transactionally upsert persistent SQLite records and their change history. Retain source dates separately from check dates.
6. Validate the candidate and rebuild standalone HTML and viewport previews.
7. Commit the selected data files together. An ordinary push rejects concurrent branch changes instead of overwriting them.
8. Upload the successfully published SQLite database as `seed-catalog-sqlite` with 90-day retention. Later runs restore it; if no artifact remains, the worker rebuilds active records from the committed catalog. See [WEEKLY_WORKER.md](WEEKLY_WORKER.md) for schema and recovery limits.

On a source failure only `sync-status.json` is committed; catalog and downloadable files remain unchanged. If a later validation/build step fails, no candidate commit is pushed. Inspect the failed Actions run before retrying. GitHub commits retain complete old versions; `static/update-history.json` provides the latest 52 release summaries and changed registration fields. “Removed” means removed from this scoped catalog, not necessarily a cancellation.

For a CPN host use the provided cron wrapper instead of running a second writer over the same files. SQLite upserts are transactional and the host catalog replacement is atomic, but these are separate operations. If file publication fails after the database commits, rerun the worker to reconcile and republish; unchanged products are not rewritten. Ancillary audit/history/status files are also separate. Keep scripts, credentials, workbooks, and SQLite outside the public `static/` directory. The hosted UI fetches published catalog/status files every five minutes. GitHub publication does not automatically configure CPN hosting, and offline copies do not update in place.

## Verification

`python test_project.py --require-node` runs parser, failure-retention, rollback, fresh-runner, provider-change, current-catalog and JavaScript checks. A frozen compressed October 19 fixture keeps regression scenarios deterministic as the live catalog evolves. `tests/live_catalog_test.cjs` and Python published-catalog checks separately validate the real current snapshot. The Chromium suite uses the same interface with the frozen fixture for repeatable keyboard/filter comparisons.
