# Crop Protection Network · Seed Treatment Explorer

A complete, lightweight web application for exploring EPA seed-treatment registrations and comparing 2–3 products. Python + aiohttp serves a responsive vanilla-JavaScript frontend and read-only JSON API. SQLite is the durable catalog cache. There is no frontend build step, external font, analytics service, account requirement, or paid API dependency.

**Integration status:** The application starts locally and all 24 backend tests passed, including a 10,037-record import. JavaScript syntax checks passed. EPA's live host returned HTTP 403 from the build environment, so a live import and the current weekly workbook layout could not be verified here. Browser rendering and end-to-end checks could not run because no browser was installed and browser downloads were blocked. Docker is provided but was not built in this environment. The adapter implements EPA's documented APPRIL REST contract. The Excel adapter validates its required headers and stops on an unsupported layout. Production never substitutes fictional data for EPA records. A separately labeled demo lets you review the interface immediately.

## Start with Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Open **http://localhost:8080**. The background worker starts a complete EPA import immediately; the interface reports progress and any source errors. The first import can take several minutes. Later visits read the local cache without contacting EPA.

For an immediate interface preview, set `DEMO_MODE=true` in `.env` and restart with `docker compose up -d`. All nine products in this mode are fictional, have `DEMO-` identifiers, and have no label links. Demo data lives in a separate database. Return `DEMO_MODE=false` for production.

## Start with Python

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m cpn serve --demo
```

Windows activation: `.venv\Scripts\activate`. For live data, omit `--demo`. Plain Python reads operating-system environment variables; `.env` is read by Docker Compose, not automatically by the Python entry point.

## What is implemented

- All 14 requested seed-treatment sites, matched as complete labels. No broad substring matches or inferred crop-group expansion.
- Active Products, normalized from EPA's API value `Active`. Status-date upper bound recalculated at each sync using `APP_TIMEZONE` (default America/Chicago).
- Every API page, not just the first 500 or 10,000 rows. No maximum product count. Every data row on every complete APPRIL workbook data sheet is processed.
- Crop dropdown; search across product, alternate name, registrant, ingredient, PC/CAS text, and registration number; ingredient autocomplete and partial-name lookup; purpose filters.
- Product detail with separately parsed ingredients, formulation percentages, PC/CAS numbers, classifications, exact matching crop sites, source warnings, and EPA label-history links.
- Two- or three-registration comparison, including all ingredients, percentages, target sites, and registration numbers. Selections persist between visits and across search pages.
- Educational ingredient guide with common fungicide, insecticide, and nematicide classifications. A biostimulant category is explained, but ingredients are never assigned that category without a reviewed entry. Unknowns remain visible and unclassified.
- Export **all** filtered results to CSV, independent of the visible page. CSV values are protected against spreadsheet formula injection.
- Keyboard-accessible dialogs and form labels, mobile layout, reduced-motion support, escaped source text, and a restrictive Content Security Policy.

## Data rules that matter

**Status Date – End = Today** is implemented as `status_dt <= today`, with no lower date bound. It is the upper end of a date range, not equality to today's date and not a registration expiration date. Requiring a status action exactly today would drop older registrations that are still active.

`Cereal crops` and `Small grains` appear as their own crop options. A specific Corn filter returns explicit corn seed-treatment sites; it does not assume that an entire cereal-crops registration applies to corn.

A registration is included only if its own source record explicitly lists an allowed site. Both Section 3 and distributor records are eligible. Sites or ingredients are not silently inherited from a parent registration. Distributor label links point to the identified base registration in PPLS; read the distributor's actual product label before use.

APPRIL lists registrations, not every physical seed-treatment mixture, retail package, non-pesticidal inoculant, or unregistered biostimulant. Educational component categories are not crop-specific efficacy recommendations. The PPLS link opens the label history so users can inspect the current label; the application does not invent PDF URLs or claim to parse label PDFs.

## Automatic synchronization and caching

1. Every six hours by default, request the documented endpoint `https://ordspub.epa.gov/ords/pesticides/apprilapi/` with `status_group=Active` and deterministic registration sorting.
2. Follow ORDS `hasMore` and `next` links until exhausted; use an actual-row offset if a next link is absent. Validate reported counts/totals when present. Repeated pages, duplicate registrations, missing pagination fields, malformed dates, or changed schemas stop publication.
3. Filter and normalize locally. Replace the full SQLite catalog and its version in **one transaction**. Readers continue to see the previous complete catalog while new data is fetched. Complete replacements remove registrations canceled or changed since the previous sync.
4. Discover the full weekly Excel link on the APPRIL landing page, or use `EPA_DUMP_URL`. Check on the same six-hour interval, so Monday refreshes are picked up without relying on an assumed publication time. Conditional requests use ETag/Last-Modified where available; otherwise download and SHA-256 detect changes. No changes means no repeat workbook parsing.
5. The weekly file can bootstrap a catalog if REST is unavailable. After any successful API import, a weekly snapshot **never rolls back** that catalog. An API failure keeps the previous snapshot and is shown in the UI.

SQLite persists on the Docker volume across app restarts and upgrades. Search pages query indexed crop/component relations. Responses use content ETags and compression; conditional requests return 304 when unchanged. The frontend sends debounced searches, cancels superseded requests, and renders 24 records at a time with unlimited pages and a page-number jump. Static files use aiohttp's conditional file responses. No source data must be downloaded to a user's browser before they can search.

The built-in poll runs while the service is running; it is not an external scheduled reminder. Deploy as an **always-on service**, with one application process per database and a persistent disk. Serverless platforms that freeze execution or discard local files are unsuitable without moving the worker and database to persistent services. Polling detects changes within the configured interval plus import time; it is not an EPA webhook.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_TIMEZONE` | `America/Chicago` | IANA timezone for the inclusive “today” cutoff |
| `SYNC_INTERVAL_SECONDS` | `21600` | Delay between full source-check cycles; minimum 60 seconds |
| `EPA_DUMP_URL` | blank | Optional exact HTTPS `epa.gov` full weekly XLSX download URL |
| `DATA_DIR` | `data` | Persistent writable directory; `/app/data` in Docker |
| `DEMO_MODE` | `false` | Explicit isolated fictional interface demonstration |
| `HOST` | `0.0.0.0` | Listening interface |
| `PORT` | `8080` | HTTP port |

If automatic download-link discovery fails (for example, EPA switches to a JavaScript download), copy the **weekly data dump** link from the APPRIL home page into `EPA_DUMP_URL`. A results-table Excel export is unsuitable because it omits Sites, pests, and alternate names. The adapter supports flat full-data sheets with documented API or human-readable column names, including exports split across multiple sheets. It deliberately rejects a relational workbook or new schema until the column adapter is reviewed; it never reports a truncated import as complete.

## Hosting and updates

Run the Docker service on an always-on VM or container host with a mounted volume. Put it behind your host's HTTPS reverse proxy. Restrict direct access to the container port to that proxy on a public deployment. No public write/admin endpoint is exposed. A filesystem lock prevents overlapping CLI and web sync jobs.

```bash
# Deploy updated source while keeping the data volume
docker compose up --build -d
# Inspect sync problems
docker compose logs --tail=100 explorer
# Request a full sync immediately
docker compose exec explorer python -m cpn sync
```

`GET /healthz` returns process liveness and a separate `ready` boolean. Liveness stays healthy while EPA is unavailable, preventing source outages from causing restart loops. Check `/api/status` to monitor API/Excel failures, last success, stale state, source row counts, and the published catalog count. Back up SQLite using its backup API or stop the service before copying the database; do not copy a live WAL database file alone.

An independently downloaded full workbook can bootstrap an offline snapshot:

```bash
python -m cpn import-xlsx /path/to/APPRIL-weekly.xlsx
```

This command refuses to overwrite a newer API-verified database. Set a new `DATA_DIR` for a separate offline catalog. Imports with zero matching records are blocked for review because that would be unexpected for this scope. If EPA legitimately reaches zero matches, review the source and update this guard explicitly.

## API

| Endpoint | Behavior |
| --- | --- |
| `GET /api/products` | Filters: `q`, `crop`, `ingredient`, `purpose`; `page` and `page_size` (1–100) |
| `GET /api/products/{registration}` | One complete normalized registration |
| `GET /api/facets` | All ingredient, crop, and purpose values and counts |
| `GET /api/compare?id=…&id=…[&id=…]` | Exactly 2–3 distinct registrations |
| `GET /api/export.csv` | All rows matching the same filters; no pagination cap |
| `GET /api/learning` | Reviewed ingredient dictionary and purpose definitions |
| `GET /api/status` | Provenance, date cutoff, sync health, and exact site allowlist |
| `GET /healthz` | Liveness and catalog readiness |

## Test

```bash
python -m unittest discover -s tests -v
```

The suite includes more than 10,000 API records, missing next-link fallback, pagination loops, truncated totals, complex ingredient names, all exact crop sites, inclusive date boundaries, multi-sheet workbooks, stale-source retention, atomic rollback, complete CSV export, and API comparison validation. It uses fixtures, not live EPA requests.

Browser verification (optional developer dependency): run `python -m cpn serve --demo`, install Playwright (`npm install --no-save playwright` and `npx playwright install chromium`), then run `node tests/browser.cjs`. The script exercises crop and component filters, details, comparison limits, export, keyboard dialogs, error recovery, and mobile overflow.

## Source references

- [EPA APPRIL REST API user guide](https://ordspub.epa.gov/ords/pesticides/r/cswu/338/files/static/v213/APPRIL_REST_API_User_Guide.pdf): endpoint, `reg_num`, `status_group`, `status_dt`, `ais`, `sites`, sorting, pagination.
- [EPA APPRIL user guide](https://ordspub.epa.gov/ords/pesticides/r/cswu/338/files/static/v205/APPRIL_User_Guide_Public.pdf): full Monday Excel dump versus incomplete results-table exports.
- [EPA APPRIL overview](https://www.epa.gov/ingredients-used-pesticide-products/how-search-information-about-pesticide-ingredients-and-labels).
- [EPA PPLS label-link format](https://www.epa.gov/pesticide-labels/pesticide-product-label-system-ppls-more-information).
- [IRAC mode-of-action classification](https://irac-online.org/mode-of-action/), [FRAC ingredient lookup](https://www.frac.info/fungicide-resistance-management/by-fungicide-common-name/), and [FRAC SDHI working group](https://www.frac.info/frac-teams/working-groups/sdhi-fungicides/).
- [EPA cyclobutrifluram registration](https://www.epa.gov/pesticides/epa-registers-new-pesticide-active-ingredient-cyclobutrifluram) documents its fungicide/nematicide uses.

Classification entries live in `cpn/classification.py`; source adapters and aliases live in `cpn/sources.py` and `cpn/normalize.py`. Review additions rather than inferring purpose from chemical-name substrings. This is a development implementation using the requested project name, not a statement of endorsement by EPA or the Crop Protection Network.
