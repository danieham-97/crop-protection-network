import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS products (
                  reg TEXT PRIMARY KEY, name TEXT COLLATE NOCASE, search TEXT, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS crops (reg TEXT, crop TEXT, PRIMARY KEY(reg,crop));
                CREATE INDEX IF NOT EXISTS crop_lookup ON crops(crop,reg);
                CREATE TABLE IF NOT EXISTS ingredients (reg TEXT, name TEXT, purpose TEXT,
                  PRIMARY KEY(reg,name,purpose));
                CREATE INDEX IF NOT EXISTS ingredient_lookup ON ingredients(name,reg);
                CREATE INDEX IF NOT EXISTS purpose_lookup ON ingredients(purpose,reg);
                CREATE INDEX IF NOT EXISTS product_sort ON products(name,reg);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=60)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def metadata(self):
        with self.connect() as db:
            return {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM metadata")}

    def set_metadata(self, **values):
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)",
                           [(k, json.dumps(v)) for k, v in values.items()])

    def publish(self, products, **metadata):
        # Entire catalog and its version change together. Readers keep the prior snapshot.
        with self.connect() as db:
            db.execute("DELETE FROM ingredients")
            db.execute("DELETE FROM crops")
            db.execute("DELETE FROM products")
            for p in products:
                search = " ".join([p["name"], p["reg_num"], p["company"], p["alternate_names"],
                                   p["raw_ingredients"]]).casefold()
                db.execute("INSERT INTO products VALUES (?,?,?,?)", (p["reg_num"], p["name"], search, json.dumps(p)))
                db.executemany("INSERT INTO crops VALUES (?,?)", [(p["reg_num"], c) for c in p["crops"]])
                db.executemany("INSERT OR IGNORE INTO ingredients VALUES (?,?,?)",
                               [(p["reg_num"], a["name"], purpose) for a in p["ingredients"] for purpose in a["purposes"]])
            metadata.update(version=uuid.uuid4().hex, published_at=now(), count=len(products))
            db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)", [(k, json.dumps(v)) for k, v in metadata.items()])

    @staticmethod
    def where(q="", crop="", ingredient="", purpose=""):
        clauses, args = [], []
        if q:
            escaped = q.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("p.search LIKE ? ESCAPE '\\'")
            args.append("%" + escaped + "%")
        if crop:
            clauses.append("EXISTS (SELECT 1 FROM crops c WHERE c.reg=p.reg AND c.crop=?)")
            args.append(crop)
        if ingredient:
            clauses.append("EXISTS (SELECT 1 FROM ingredients i WHERE i.reg=p.reg AND i.name LIKE ? ESCAPE '\\')")
            args.append("%" + ingredient.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        if purpose:
            clauses.append("EXISTS (SELECT 1 FROM ingredients i WHERE i.reg=p.reg AND i.purpose=?)")
            args.append(purpose)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), args

    def search(self, filters, page=1, page_size=24):
        where, args = self.where(**filters)
        with self.connect() as db:
            db.execute("BEGIN")
            total = db.execute("SELECT count(*) FROM products p" + where, args).fetchone()[0]
            rows = db.execute("SELECT p.data FROM products p" + where + " ORDER BY p.name,p.reg LIMIT ? OFFSET ?", [*args, page_size, (page-1)*page_size])
            return {"items": [json.loads(r[0]) for r in rows], "total": total, "page": page, "page_size": page_size,
                    "pages": (total + page_size - 1) // page_size}

    def all_products(self, filters):
        where, args = self.where(**filters)
        with self.connect() as db:
            for r in db.execute("SELECT p.data FROM products p" + where + " ORDER BY p.name,p.reg", args):
                yield json.loads(r[0])

    def get(self, reg):
        with self.connect() as db:
            row = db.execute("SELECT data FROM products WHERE reg=?", (reg,)).fetchone()
            return json.loads(row[0]) if row else None

    def get_many(self, registrations):
        # A comparison must use one snapshot, even while a sync commits.
        with self.connect() as db:
            db.execute("BEGIN")
            result = []
            for reg in registrations:
                row = db.execute("SELECT data FROM products WHERE reg=?", (reg,)).fetchone()
                result.append(json.loads(row[0]) if row else None)
            return result

    def facets(self):
        with self.connect() as db:
            return {"crops": [dict(r) for r in db.execute("SELECT crop AS name, count(*) AS count FROM crops GROUP BY crop ORDER BY crop")],
                    "ingredients": [dict(r) for r in db.execute("SELECT name, count(DISTINCT reg) AS count FROM ingredients GROUP BY name ORDER BY name COLLATE NOCASE")],
                    "purposes": [dict(r) for r in db.execute("SELECT purpose AS name, count(DISTINCT reg) AS count FROM ingredients GROUP BY purpose ORDER BY purpose")]}
