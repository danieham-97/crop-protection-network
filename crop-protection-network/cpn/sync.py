import hashlib
import json
import logging
from contextlib import contextmanager

from .normalize import SourceError, normalize
from .sources import download_dump, iter_api, iter_workbook
from .store import now

log = logging.getLogger(__name__)


@contextmanager
def sync_lock(path):
    """OS releases the lock on process exit; CLI and web worker share it."""
    with path.open("a+b") as handle:
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
        handle.seek(0)
        try:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            # Closing the file releases either platform's lock.
            pass


def collect(rows, today):
    products, registrations = [], set()
    scanned = 0
    for row in rows:
        scanned += 1
        product = normalize(row, today)
        if product:
            if product["reg_num"] in registrations:
                raise SourceError("Duplicate matching registration; import stopped to avoid ambiguous data")
            registrations.add(product["reg_num"])
            products.append(product)
    if not scanned:
        raise SourceError("Source is empty")
    if not products:
        raise SourceError("No matching seed treatments; retaining previous snapshot for schema review")
    return products, scanned


def publish(store, products, source, today, scanned):
    fingerprint = hashlib.sha256(json.dumps(sorted(products, key=lambda p: p["reg_num"]), sort_keys=True).encode()).hexdigest()
    metadata = {"source": source, "as_of_date": today.isoformat(), "source_rows_scanned": scanned,
                "fingerprint": fingerprint, "last_success": now(), "demo": False}
    current = store.metadata()
    if current.get("fingerprint") == fingerprint and current.get("source") == source:
        store.set_metadata(**metadata)
    else:
        store.publish(products, **metadata)


def sync(store, settings):
    if settings.demo:
        raise SourceError("Live sync is disabled in demo mode")
    try:
        with sync_lock(settings.data_dir / "sync.lock"):
            return _sync(store, settings)
    except BlockingIOError:
        return {"skipped": "Another sync is running"}


def _sync(store, settings):
    today = settings.today()
    store.set_metadata(sync_running=True, last_attempt=now())
    api_error = dump_error = None
    api_success = False
    try:
        try:
            products, scanned = collect(iter_api(), today)
            publish(store, products, "EPA APPRIL REST API", today, scanned)
            store.set_metadata(api_last_success=now(), api_error=None)
            api_success = True
        except Exception as exc:
            log.exception("API sync failed")
            api_error = str(exc)
            store.set_metadata(api_error=api_error)
        # Check every cycle, including after Monday. ETag / Last-Modified prevent
        # repeat transfer where supported; SHA-256 prevents duplicate processing.
        try:
            path, metadata, changed = download_dump(settings.data_dir, settings.dump_url)
            previous = store.metadata()
            if changed or previous.get("dump_valid_sha256") != metadata["sha256"]:
                weekly, scanned = collect(iter_workbook(path), today)
                store.set_metadata(dump_valid_sha256=metadata["sha256"], dump_count=len(weekly), dump_rows_scanned=scanned)
            else:
                weekly = None
            store.set_metadata(dump_checked=now(), dump_error=None, dump_metadata=metadata)
            # A weekly snapshot must never roll back a catalog previously verified by REST.
            if not api_success and not previous.get("api_last_success"):
                if weekly is None:
                    weekly, scanned = collect(iter_workbook(path), today)
                publish(store, weekly, "EPA APPRIL Monday Excel snapshot", today, scanned)
        except Exception as exc:
            log.exception("Weekly export check failed")
            dump_error = str(exc)
            store.set_metadata(dump_error=dump_error)
        return {"api_ok": api_success, "api_error": api_error, "dump_error": dump_error, "count": store.metadata().get("count", 0)}
    finally:
        store.set_metadata(sync_running=False, last_checked=now())
