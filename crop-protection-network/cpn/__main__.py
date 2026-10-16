import argparse
import json
import logging
import os

from aiohttp import web

from .config import Settings
from .normalize import SourceError
from .sources import iter_workbook
from .store import Store
from .sync import collect, publish, sync, sync_lock
from .web import create_app


def main():
    parser = argparse.ArgumentParser(description="CPN Seed Treatment Explorer")
    parser.add_argument("command", choices=["serve", "sync", "import-xlsx"], nargs="?", default="serve")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")))
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--demo", action="store_true", help="Fictional data in a separate database; live sync disabled")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    settings.demo = args.demo or settings.demo
    if args.command == "serve":
        web.run_app(create_app(settings), host=args.host, port=args.port)
        return
    store = Store(settings.db_path)
    if args.command == "sync":
        result = sync(store, settings)
        print(json.dumps(result, indent=2))
        if result.get("api_error"):
            raise SystemExit(1)
    elif args.command == "import-xlsx":
        if not args.file:
            parser.error("import-xlsx requires the full APPRIL weekly workbook path")
        if settings.demo:
            parser.error("Import is not available in demo mode")
        if store.metadata().get("api_last_success"):
            raise SourceError("Cannot replace a REST-verified catalog with a potentially older workbook. Use a new DATA_DIR for an independent offline snapshot.")
        with sync_lock(settings.data_dir / "sync.lock"):
            products, scanned = collect(iter_workbook(args.file), settings.today())
            publish(store, products, "EPA APPRIL Monday Excel snapshot (manual import)", settings.today(), scanned)
        print(f"Imported {len(products):,} matching products from {scanned:,} source rows.")


if __name__ == "__main__":
    main()
