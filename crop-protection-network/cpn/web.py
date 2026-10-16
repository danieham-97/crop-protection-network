import asyncio
import csv
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from aiohttp import web

from .classification import CATEGORIES, MAP
from .config import ROOT, SITES, Settings
from .demo import seed_demo
from .store import Store
from .sync import sync

log = logging.getLogger(__name__)
SETTINGS = web.AppKey("settings", Settings)
STORE = web.AppKey("store", Store)


@web.middleware
async def headers(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException:
        raise
    except Exception:
        log.exception("Request failed")
        response = web.json_response({"error": "Request failed. Try again shortly."}, status=500)
    return response


async def security_headers(request, response):
    response.headers.update({
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    })


def filters(request):
    return {k: request.query.get(k, "")[:300] for k in ("q", "crop", "ingredient", "purpose")}


def cached_json(request, value):
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
    h = {"ETag": etag, "Cache-Control": "public, max-age=0, must-revalidate"}
    if request.headers.get("If-None-Match") == etag:
        return web.Response(status=304, headers=h)
    response = web.Response(body=body, content_type="application/json", headers=h)
    response.enable_compression()
    return response


async def status(request):
    settings, store = request.app[SETTINGS], request.app[STORE]
    metadata = await asyncio.to_thread(store.metadata)
    last = metadata.get("last_success")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() if last else None
    is_weekly = "Excel" in metadata.get("source", "")
    stale = not metadata.get("demo") and (age is None or age > (8*86400 if is_weekly else max(86400, settings.sync_seconds*2)))
    if is_weekly:
        # Checking an unchanged old export does not make the source fresh.
        try:
            modified = parsedate_to_datetime(metadata.get("dump_metadata", {}).get("last_modified", ""))
            stale = stale or (datetime.now(timezone.utc) - modified).total_seconds() > 8*86400
        except (ValueError, TypeError):
            stale = True
    return web.json_response({**metadata, "stale": stale, "today": settings.today().isoformat(),
                              "timezone": settings.timezone, "sync_interval_seconds": settings.sync_seconds,
                              "allowed_sites": list(SITES), "classifications": len(MAP)}, headers={"Cache-Control": "no-store"})


async def search(request):
    try:
        page, size = int(request.query.get("page", 1)), int(request.query.get("page_size", 24))
        if page < 1 or size < 1 or size > 100:
            raise ValueError()
    except ValueError:
        raise web.HTTPBadRequest(text="page must be positive; page_size must be 1–100 (no limit on total results)")
    result = await asyncio.to_thread(request.app[STORE].search, filters(request), page, size)
    return cached_json(request, result)


async def facets(request):
    return cached_json(request, await asyncio.to_thread(request.app[STORE].facets))


async def detail(request):
    product = await asyncio.to_thread(request.app[STORE].get, request.match_info["reg"])
    if product is None:
        raise web.HTTPNotFound(text="Registration not in the current catalog")
    return cached_json(request, product)


async def compare(request):
    ids = request.query.getall("id", [])
    if not 2 <= len(ids) <= 3 or len(set(ids)) != len(ids):
        raise web.HTTPBadRequest(text="Select 2 or 3 distinct registrations")
    products = await asyncio.to_thread(request.app[STORE].get_many, ids)
    if any(p is None for p in products):
        raise web.HTTPNotFound(text="A selected registration is no longer in this catalog. Refresh your selection.")
    return cached_json(request, {"items": products})


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


async def export(request):
    response = web.StreamResponse(headers={"Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="seed-treatment-results.csv"', "Cache-Control": "no-store"})
    await response.prepare(request)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Product", "EPA registration", "Company", "Crops (matching sites)", "Exact matching sites", "Active ingredients", "Purpose", "Status date", "EPA label record"])
    await response.write(("\ufeff" + buffer.getvalue()).encode())
    buffer.seek(0); buffer.truncate(0)
    for i, p in enumerate(request.app[STORE].all_products(filters(request)), 1):
        writer.writerow([csv_safe(v) for v in [p["name"], p["reg_num"], p["company"], "; ".join(p["crops"]),
            "; ".join(p["sites"]), p["raw_ingredients"], "; ".join(p["purposes"]), p["status_date"], p["label_url"] or "Demo only"]])
        if i % 200 == 0:
            await response.write(buffer.getvalue().encode())
            buffer.seek(0); buffer.truncate(0)
    await response.write(buffer.getvalue().encode())
    await response.write_eof()
    return response


async def learning(request):
    return cached_json(request, {"categories": CATEGORIES, "ingredients": MAP})


async def health(request):
    metadata = await asyncio.to_thread(request.app[STORE].metadata)
    ready = bool(metadata.get("count"))
    return web.json_response({"alive": True, "ready": ready, "demo": request.app[SETTINGS].demo})


async def worker(app):
    settings = app[SETTINGS]
    if settings.demo:
        seed_demo(app[STORE], settings.today())
        yield
        return
    async def loop():
        while True:
            try:
                await asyncio.to_thread(sync, app[STORE], settings)
            except Exception:
                log.exception("Background sync failed")
            await asyncio.sleep(max(60, settings.sync_seconds))
    task = asyncio.create_task(loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app(settings=None, background=True):
    settings = settings or Settings()
    app = web.Application(middlewares=[headers])
    app.on_response_prepare.append(security_headers)
    app[SETTINGS], app[STORE] = settings, Store(settings.db_path)
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/products", search)
    app.router.add_get("/api/products/{reg}", detail)
    app.router.add_get("/api/facets", facets)
    app.router.add_get("/api/compare", compare)
    app.router.add_get("/api/export.csv", export)
    app.router.add_get("/api/learning", learning)
    app.router.add_get("/healthz", health)
    async def index(request):
        return web.FileResponse(ROOT / "static" / "index.html", headers={"Cache-Control": "no-cache"})
    app.router.add_get("/", index)
    app.router.add_static("/static/", ROOT / "static", show_index=False)
    if background:
        app.cleanup_ctx.append(worker)
    return app
