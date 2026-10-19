"""Persistent SQLite records for the scoped seed catalog; standard library only.

The public JSON remains the browser's read model. Removed records are retained
with in_scope=0; their last in-scope payload is not a current-use authorization.
"""
import copy
import hashlib
import json
import pathlib
import sqlite3
from catalog import product_facts, regno


def connect_records(path):
    path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=60)
    db.executescript('''
    CREATE TABLE IF NOT EXISTS products (
      registration_number TEXT PRIMARY KEY, name TEXT NOT NULL,
      in_scope INTEGER NOT NULL CHECK(in_scope IN (0,1)),
      latest_status_group TEXT, latest_epa_status TEXT, latest_status_date TEXT,
      scope_reason TEXT, source_observation TEXT, payload TEXT NOT NULL,
      facts_hash TEXT NOT NULL, first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS worker_runs (
      id INTEGER PRIMARY KEY, checked_at TEXT NOT NULL, workbook_sha256 TEXT NOT NULL,
      workbook_created TEXT, counts_json TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS product_changes (
      id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, registration_number TEXT NOT NULL,
      action TEXT NOT NULL, before_json TEXT, after_json TEXT);
    CREATE TABLE IF NOT EXISTS worker_state (
      id INTEGER PRIMARY KEY CHECK(id=1), workbook_created TEXT, workbook_sha256 TEXT);
    ''')
    return db


def tracked_registrations(path):
    if not pathlib.Path(path).exists():return []
    db=connect_records(path)
    try:return [r[0] for r in db.execute('SELECT registration_number FROM products')]
    finally:db.close()


def snapshot(product,in_scope=True,observation=None):
    return {'product':product,'in_scope':bool(in_scope),'observation':observation}


def fingerprint(item):
    facts=copy.deepcopy(item);facts['product']=product_facts(item['product'])
    if facts['observation']:facts['observation'].pop('source_row',None)
    return hashlib.sha256(json.dumps(facts,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def write_record(db,item,checked):
    p=item['product'];obs=item['observation'] or {}
    db.execute('''INSERT INTO products(registration_number,name,in_scope,
        latest_status_group,latest_epa_status,latest_status_date,scope_reason,
        source_observation,payload,facts_hash,first_seen_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(registration_number) DO UPDATE SET name=excluded.name,
        in_scope=excluded.in_scope,latest_status_group=excluded.latest_status_group,
        latest_epa_status=excluded.latest_epa_status,latest_status_date=excluded.latest_status_date,
        scope_reason=excluded.scope_reason,source_observation=excluded.source_observation,
        payload=excluded.payload,facts_hash=excluded.facts_hash,updated_at=excluded.updated_at
        WHERE products.facts_hash<>excluded.facts_hash''',
        (p['id'],p['name'],int(item['in_scope']),
         'Active' if item['in_scope'] else obs.get('status_group'),
         p.get('epa_status') if item['in_scope'] else obs.get('epa_status'),
         p.get('status_date') if item['in_scope'] else obs.get('status_date'),
         None if item['in_scope'] else obs.get('reason','Not present in scoped catalog'),
         json.dumps(item['observation']),json.dumps(p,ensure_ascii=False),fingerprint(item),checked,checked))


def upsert_catalog(path,candidate,baseline,checked):
    """Commit one full validated comparison atomically; unchanged rows are untouched."""
    products=candidate['products'];ids=[p['id'] for p in products]
    if not ids or len(set(ids))!=len(ids) or any(regno(p['registration_number'])!=p['id'] for p in products):
        raise ValueError('Empty, duplicate or inconsistent product identities')
    meta=candidate['meta'];audit=meta['audit'];created=meta.get('source_snapshot_date')
    observations={x['registration_number']:x for x in audit.get('tracked_out_of_scope',[])}
    db=connect_records(path)
    try:
        db.execute('BEGIN IMMEDIATE')
        counts={'initialized':0,'added':0,'changed':0,'removed':0,'reactivated':0,'unchanged':0}
        state=db.execute('SELECT workbook_created FROM worker_state WHERE id=1').fetchone()
        if state and state[0] and (not created or created<state[0]):raise ValueError('Older workbook than persistent database')
        if not db.execute('SELECT 1 FROM products LIMIT 1').fetchone():
            previous=baseline.get('products',[])
            if len({p['id'] for p in previous})!=len(previous):raise ValueError('Duplicate baseline identities')
            for p in previous:write_record(db,snapshot(p),checked)
            counts['initialized']=len(previous)
        old={r[0]:{'item':snapshot(json.loads(r[1]),bool(r[2]),json.loads(r[3])), 'hash':r[4]}
             for r in db.execute('SELECT registration_number,payload,in_scope,source_observation,facts_hash FROM products')}
        active={rid for rid,r in old.items() if r['item']['in_scope']}
        if active and len(active-set(ids))/len(active)>.30:raise ValueError('More than 30% of database records would leave scope')
        run_id=db.execute('INSERT INTO worker_runs(checked_at,workbook_sha256,workbook_created,counts_json) VALUES(?,?,?,?)',
                          (checked,audit['sha256'],created,'{}')).lastrowid
        incoming={p['id']:snapshot(p) for p in products}
        for rid,oldrow in old.items():
            if rid not in incoming:
                # Only an explicit workbook observation establishes a changed EPA
                # status. Absence never becomes a guessed cancellation.
                obs=observations.get(rid,{'registration_number':rid,'found':False,'reason':'Not present in scoped catalog; status not established'})
                incoming[rid]=snapshot(oldrow['item']['product'],False,obs)
        for rid,item in sorted(incoming.items()):
            previous=old.get(rid)
            if previous and previous['hash']==fingerprint(item):counts['unchanged']+=1;continue
            action='added' if previous is None else 'reactivated' if item['in_scope'] and not previous['item']['in_scope'] else 'removed' if not item['in_scope'] and previous['item']['in_scope'] else 'changed'
            write_record(db,item,checked);counts[action]+=1
            db.execute('INSERT INTO product_changes(run_id,registration_number,action,before_json,after_json) VALUES(?,?,?,?,?)',
                       (run_id,rid,action,json.dumps(previous['item']) if previous else None,json.dumps(item)))
        db.execute('UPDATE worker_runs SET counts_json=? WHERE id=?',(json.dumps(counts),run_id))
        db.execute('INSERT INTO worker_state(id,workbook_created,workbook_sha256) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET workbook_created=excluded.workbook_created,workbook_sha256=excluded.workbook_sha256',(created,audit['sha256']))
        db.commit()
        return counts
    except Exception:
        db.rollback();raise
    finally:db.close()
