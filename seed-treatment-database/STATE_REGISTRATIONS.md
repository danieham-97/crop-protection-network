# State availability and registration feature

Select **State / jurisdiction** in the product filters, then choose the evidence type. Product details show all 50 states plus D.C. and Puerto Rico. Comparisons and CSV exports include state-source registration reports, provider availability and the selected state's status.

## Initial coverage is limited

**No official state approvals have been independently verified in this release.** Three EPA registration numbers have 156 CDMS availability observations (52 jurisdictions per product). These were read from search-index excerpts on October 19, 2026; the live CDMS tables could not be retrieved, and source update/approval dates were not supplied.

| EPA registration | Source product name | CDMS source |
| --- | --- | --- |
| 7969-441 | Ilevo Seed Treatment | https://www.cdms.net/labelsSDS/home/prodidx?key=17665 |
| 55146-118 | Spirato M 185 FS | https://www.cdms.net/labelsSDS/home/prodidx?key=14720 |
| 55146-148 | Salient 372 FS | https://www.cdms.net/labelsSDS/home/prodidx?key=14718 |

The source product name remains visible because a federal registration may have alternate brands. A CDMS Yes means **provider-reported availability**, not a verified state approval. A CDMS No means **provider-reported unavailability**, not a legal prohibition. Other records remain **Not verified**. A missing record is never interpreted as not registered. Distributor numbers must match in full; they never inherit a base product's state status.

Federal EPA registration, state product registration, provider availability and permission for a particular crop/use are different questions. State evidence must be checked against the exact marketed product and the applicable label, treatment location and planting location. This feature does not adjudicate those legal requirements or special-local-need labels.

The state lookup link opens [NPIRS State Public](https://www.npirs.org/state/). [NPIRS describes its coverage and state-dependent update frequency here](https://www.npirs.org/public). Access to a public search does not establish permission for automated bulk collection. The app does not scrape or assume a supported API for that service.

## Feed contract

`data/state-registrations.json` is a reviewed, partial evidence collection. `data/us-states.json` defines the 52 supported jurisdictions. The canonical feed has `schema_version: 1`, `compiled_on: YYYY-MM-DD`, and a `records` array. Every record requires:

| Field | Meaning |
| --- | --- |
| registration_number | Exact full EPA number; preserve distributor suffix |
| jurisdiction | Two-letter state, DC or PR |
| status | `yes`, `no`, `restricted`, or `unknown`; explicit source report only |
| evidence_kind | `state_authority` or `provider_availability` |
| source / source_product_name | Responsible source and exact product/brand reported |
| source_status | Original status text, such as Yes, Active or Expired |
| source_url | HTTPS source for the specific record/export |
| observed_on | Date the evidence was retrieved or reviewed |
| source_updated_on | Actual source update date, or null; never use the observation date as a substitute |
| review_due | Internal deadline for checking freshness; not an approval expiration |
| expires_on | Actual source-supplied expiration date, or null |
| retrieval_basis | `direct_source`, `authorized_feed`, or `indexed_excerpt` |
| notes | Scope, brand differences, restrictions and evidence limitations |

An editor must verify source identity and provenance before marking a row `state_authority`. Indexed excerpts cannot be given that evidence type. Provider rows are always displayed separately. Status `restricted` requires explanatory notes; this feature does not infer that all uses are permitted. Conflicting active source statuses require review and are excluded from positive results. Evidence past `review_due` or `expires_on` is excluded from positive results and retained with its dates. The initial observations have a 30-day editorial review window, ending November 18; this is not a legal registration period.

Import a supported export:

```sh
python3 state_registry.py /path/to/state-evidence.json
python3 refresh_epa.py --workbook /path/to/apprildatadump_public.xlsx
python3 build_preview.py
```

For automatic updates, configure **STATE_REGISTRATION_FEED_URL** on the CPN host to an authorized HTTPS JSON export using this contract. The existing weekly job retrieves and validates that feed during catalog publication. The feed must be assembled by CPN or a provider; this repository does not invent an EPA/NPIRS/CDMS state API. No state feed is currently connected.

An invalid/inaccessible configured feed or an older compilation blocks that publication and preserves the last catalog. Successful state-feed retrieval does not restamp each record's observation or source date. A feed is the complete replacement for the current curated evidence collection, not a claim of complete U.S. registration coverage. Records omitted from a later collection become unknown; they do not become not-approved. Preserve needed historical observations in the feed or retained SQLite revisions. The frontend re-evaluates review deadlines against the local current date, including in the offline snapshot.
