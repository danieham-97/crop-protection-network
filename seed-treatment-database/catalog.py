"""Validated seed-treatment catalog. Python 3.11+, standard library only.
Publications are immutable revisions; a failed ingestion never replaces the last good catalog.
APPRIL feed contract is in INTEGRATION.md. This is not an undocumented EPA API.
"""
import argparse, copy, csv, datetime as dt, hashlib, io, json, os, pathlib, re, sqlite3, sys, tempfile
import urllib.request, urllib.parse
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
SCOPE = json.loads((ROOT/'data/scope.json').read_text())
INGREDIENTS = json.loads((ROOT/'data/ingredients.json').read_text())
EDUCATION = json.loads((ROOT/'data/education.json').read_text())
MAX_BYTES = 100 * 1024 * 1024


def today():
    return dt.datetime.now(ZoneInfo(SCOPE['timezone'])).date().isoformat()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def norm(s):
    return re.sub(r'\s+', ' ', str(s).strip()).casefold()


def regno(value):
    s = str(value).strip()
    if not re.fullmatch(r'\d{1,6}-\d{1,5}(?:-\d{1,6})?', s):
        raise ValueError('Invalid EPA registration number')
    return '-'.join(str(int(x)) for x in s.split('-'))


def valid_date(s):
    if not isinstance(s, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        raise ValueError('Expected ISO date YYYY-MM-DD')
    dt.date.fromisoformat(s)
    return s


def source_url(value, hosts=None):
    p = urllib.parse.urlparse(str(value))
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Source link must use HTTPS without embedded credentials')
    if hosts and p.hostname not in hosts:
        raise ValueError('Unexpected source domain')
    return value


def download(url, token=None):
    source_url(url)
    headers = {'User-Agent': 'CPN-Seed-Treatment-Catalog/0.1', 'Accept': 'application/json, text/plain, application/zip'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    # Do not forward a feed token across a redirect.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            raise ValueError('Feed redirect rejected; configure the final HTTPS endpoint')
    with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers=headers), timeout=90) as r:
        raw = r.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Source exceeds 100 MiB limit')
    return raw


def read_feed(location, token=None):
    raw = download(location, token) if location.startswith('https://') else pathlib.Path(location).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('Feed is too large')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Feed must be a JSON object')
    return data


def snapshot_validate(feed, date_end):
    """Validate a COMPLETE, normalized APPRIL export; fail closed on changed scope."""
    if feed.get('schema_version') != 1 or feed.get('source') != 'EPA APPRIL':
        raise ValueError('Expected schema_version=1 and source=EPA APPRIL')
    if feed.get('complete') is not True:
        raise ValueError('Incomplete EPA snapshot: publication blocked')
    q = feed.get('query', {})
    if q.get('status_group') != 'Active Products' or q.get('status_date_start') is not None:
        raise ValueError('EPA query must use Active Products and blank status-date start')
    if q.get('status_date_end') != date_end:
        raise ValueError('EPA status-date end must equal this run date in America/Chicago')
    if len(q.get('sites', [])) != len(SCOPE['sites']) or {norm(s) for s in q['sites']} != {norm(s) for s in SCOPE['sites']}:
        raise ValueError('EPA snapshot does not cover exactly the 14 requested sites')
    retrieved = valid_date(feed.get('retrieved_on'))
    if retrieved != date_end:
        raise ValueError('EPA snapshot must have been retrieved on this run date')
    source_url(feed.get('source_url'), {'ordspub.epa.gov'})
    if not isinstance(feed.get('products'), list) or not feed['products']:
        raise ValueError('Empty or invalid EPA product list: publication blocked')


def filter_products(feed, date_end):
    """Return accepted and quarantined records. Never infer an approved use from a crop name."""
    snapshot_validate(feed, date_end)
    scope = {norm(s): s for s in SCOPE['sites']}
    accepted, rejected, seen = [], [], set()
    for raw in feed['products']:
        if not isinstance(raw, dict):
            raise ValueError('Product must be an object')
        r = regno(raw.get('registration_number'))
        if r in seen:
            raise ValueError('Duplicate registration number: '+r)
        seen.add(r)
        if not isinstance(raw.get('name'), str) or not raw['name'].strip():
            raise ValueError('Product name required: '+r)
        reasons = []
        if raw.get('status_group') != 'Active Products':
            reasons.append('Not in Active Products status group')
        if not raw.get('status_date'):
            reasons.append('EPA status date missing')
        elif valid_date(raw['status_date']) > date_end:
            reasons.append('Status date after cutoff')
        uses = raw.get('sites')
        if not isinstance(uses, list):
            raise ValueError('sites must be an array of approved-use objects: '+r)
        selected = []
        for use in uses:
            if not isinstance(use, dict) or not isinstance(use.get('name'), str):
                raise ValueError('Invalid site object: '+r)
            key = norm(use['name'])
            if key in scope and use.get('status') == 'Approved':
                selected.append(scope[key])
        if not selected:
            reasons.append('No approved matching seed-treatment site; storage-only uses excluded')
        ais = raw.get('ingredients')
        if not isinstance(ais, list):
            raise ValueError('ingredients must be an array: '+r)
        if raw.get('ingredients_complete') is not True or not ais:
            reasons.append('Active ingredients incomplete')
        total = 0.0
        for ai in ais:
            if not isinstance(ai, dict) or not isinstance(ai.get('name'), str) or not ai['name'].strip():
                raise ValueError('Ingredient name missing: '+r)
            names = [ai['name']] + ai.get('synonyms', [])
            if any('deltamethrin' in norm(n) for n in names) or str(ai.get('cas', '')).strip() in SCOPE['excluded_cas'] or str(ai.get('pc_code', '')).zfill(6) in SCOPE['excluded_pc_codes']:
                reasons.append('Deltamethrin excluded by project scope')
            percent = ai.get('percent')
            if percent is not None:
                if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 < percent <= 100:
                    raise ValueError('Invalid active ingredient percentage: '+r)
                total += percent
        if total > 100.01:
            raise ValueError('Total ingredient percentage exceeds 100: '+r)
        if reasons:
            rejected.append({'registration_number': r, 'name': raw['name'], 'reasons': sorted(set(reasons))})
            continue
        purposes = sorted({INGREDIENTS.get(norm(ai['name']), {}).get('purpose', 'Unclassified') for ai in ais})
        accepted.append({
            'id': r, 'registration_number': r, 'name': raw['name'].strip(),
            'registrant': str(raw.get('registrant') or 'Not supplied'),
            'aliases': [str(a) for a in raw.get('aliases', [])],
            'record_type': 'Registered product', 'sites': sorted(set(selected)),
            'ingredients': [{'name': ai['name'], 'percent': ai.get('percent'), 'cas': ai.get('cas'), 'pc_code': ai.get('pc_code')} for ai in ais],
            'purposes': purposes, 'status': 'Active Products', 'status_date': raw['status_date'],
            'epa_verified': True, 'ingredient_quality': 'verified', 'notes': '',
            'source': 'EPA APPRIL', 'source_url': feed['source_url'],
            'source_updated': valid_date(raw['source_updated']) if raw.get('source_updated') else None, 'retrieved_at': feed['retrieved_on'],
            'greenbook': None
        })
    return accepted, rejected


def enrich(products, feed, date_end, provider='Greenbook'):
    """Join by FULL registration number. EPA facts win; conflicts remain visible."""
    if provider not in ('Greenbook', 'CDMS'):
        raise ValueError('Unsupported enrichment provider')
    key = provider.lower()
    hosts = {'www.greenbook.net', 'greenbook.net'} if provider == 'Greenbook' else {'www.cdms.net', 'cdms.net', 'www.telus.com'}
    if not feed:
        return products, {'state': 'Not connected', 'matched': 0, 'unmatched': 0}
    if feed.get('schema_version') != 1 or feed.get('source') != provider:
        raise ValueError('Expected normalized '+provider+' schema v1')
    retrieved = valid_date(feed.get('retrieved_on'))
    if retrieved > date_end or (dt.date.fromisoformat(date_end)-dt.date.fromisoformat(retrieved)).days > 7:
        raise ValueError(provider+' enrichment is older than seven days or future dated')
    entries = feed.get('products')
    if not isinstance(entries, list):
        raise ValueError('Invalid '+provider+' products array')
    byreg = {}
    for g in entries:
        r = regno(g.get('registration_number'))
        if r in byreg:
            raise ValueError('Duplicate '+provider+' registration requires review: '+r)
        source_url(g.get('source_url'), hosts)
        for doc in g.get('documents', []):
            if doc.get('type') not in ('specimen_label', 'supplemental_label', 'sds'):
                raise ValueError('Invalid document type')
            source_url(doc.get('url'), hosts)
            if doc.get('date'):
                valid_date(doc['date'])
                if doc['date'] > date_end:
                    raise ValueError('Future document date')
        if g.get('source_updated'):
            valid_date(g['source_updated'])
            if g['source_updated']>date_end:raise ValueError('Future provider source date')
        byreg[r] = g
    matched = 0
    for p in products:
        g = byreg.get(p['id'])
        if not g:
            continue
        previous_updated=(p.get(key) or {}).get('source_updated')
        if previous_updated and g.get('source_updated') and g['source_updated']<previous_updated:
            raise ValueError(provider+' source revision is older than the published reference')
        matched += 1
        warnings = []
        gi = g.get('ingredients', [])
        if provider == 'CDMS' and g.get('ingredient_basis') != 'label':
            gi = []
            warnings.append('CDMS label formulation not supplied; SDS composition is not a complete active ingredient list')
        if not gi:
            warnings.append(provider+' ingredients not supplied')
        else:
            epa_set = {norm(x['name']) for x in p['ingredients']}
            gb_set = {norm(x['name']) for x in gi}
            if epa_set != gb_set:
                warnings.append('Source ingredient lists differ; EPA formulation displayed')
            ep = {norm(x['name']): x.get('percent') for x in p['ingredients']}
            if any(x.get('percent') is not None and ep.get(norm(x['name'])) is not None and abs(float(x['percent'])-float(ep[norm(x['name'])])) > 0.01 for x in gi if norm(x['name']) in ep):
                warnings.append('Source ingredient percentages differ; EPA values displayed')
        if g.get('status') and g['status'] != 'Active Registration':
            warnings.append(provider+' status differs; check current label')
        p[key] = {k: g.get(k) for k in ('name', 'source_url', 'source_updated')}
        p[key]['documents'] = g.get('documents', [])
        p[key].update(retrieved_at=retrieved, warnings=warnings)
    return products, {'state': 'Connected', 'retrieved_on': retrieved, 'matched': matched, 'unmatched': len(byreg)-matched}


def connect(path):
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''CREATE TABLE IF NOT EXISTS revisions (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, digest TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS changes (id INTEGER PRIMARY KEY, revision INTEGER, registration TEXT, action TEXT, before_json TEXT, after_json TEXT);''')
    return db


def seed_published_baseline(db, output):
    """Fresh runners must enforce rollback/loss guards against the published file."""
    if db.execute('SELECT 1 FROM revisions LIMIT 1').fetchone() or not pathlib.Path(output).exists():
        return
    old=json.loads(pathlib.Path(output).read_text())
    products=old.get('products')
    if not isinstance(products,list) or not products or len({p['id'] for p in products})!=len(products):
        raise ValueError('Invalid published baseline; cannot safely initialize update history')
    with db:
        db.execute('INSERT INTO revisions(created_at,digest,payload) VALUES(?,?,?)',
                   (now(),hashlib.sha256(json.dumps(products,sort_keys=True).encode()).hexdigest(),json.dumps(old)))


def product_facts(product):
    """Ignore retrieval bookkeeping, but retain all scientific and provider facts."""
    q=copy.deepcopy(product)
    if q:
        for key in ('retrieved_at','imported_at','source_snapshot_date','source_row','base_source_row'):
            q.pop(key,None)
        for key in ('greenbook','cdms'):
            if q.get(key):q[key].pop('retrieved_at',None)
    return q


def atomic_write(path, text):
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.catalog-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(text); out.flush(); os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def publish(db, products, quarantine, date_end, greenbook_status, allow_large_change=False, cdms_status=None, metadata=None, mode='live'):
    if not products:
        raise ValueError('No publishable products; keeping last good snapshot')
    oldrow = db.execute('SELECT payload FROM revisions ORDER BY id DESC LIMIT 1').fetchone()
    old = json.loads(oldrow[0]) if oldrow else {'products': []}
    oldids = {p['id'] for p in old['products']}; newids = {p['id'] for p in products}
    if oldids and len(oldids-newids)/len(oldids) > 0.30 and not allow_large_change:
        raise ValueError('More than 30% of existing registrations would disappear; review source then use --allow-large-change')
    from state_registry import load_state_layer
    # State evidence has its own observation clock, independent of EPA's cutoff.
    state_layer=load_state_layer(today(),os.getenv('STATE_REGISTRATION_FEED_URL'))
    old_state_date=old.get('state_registration',{}).get('compiled_on')
    if old_state_date and state_layer['compiled_on']<old_state_date:
        raise ValueError('Older state evidence would replace newer compilation')
    from comparison_evidence import load_label_specs
    catalog = {'mode': mode, 'scope': SCOPE, 'ingredient_reference': INGREDIENTS, 'education': EDUCATION, 'label_specs':load_label_specs(), 'state_registration':state_layer, 'products': products,
        'meta': {'last_successful_sync': now(), 'source_checked': date_end, 'status_date_end': date_end,
                 'automation': 'External scheduler required', 'complete': True,
                 'epa': 'Connected', 'greenbook': greenbook_status, 'cdms': cdms_status or {'state':'Not connected'}, 'quarantined_count': len(quarantine),
                 'coverage_note': 'Validated records from configured APPRIL export. No efficacy or state-authorization assessment.'}}
    if metadata: catalog['meta'].update(metadata)
    digest = hashlib.sha256(json.dumps(products, sort_keys=True).encode()).hexdigest()
    # Exact state, including deletions, published transactionally; no incremental-date shortcut.
    with db:
        cur = db.execute('INSERT INTO revisions(created_at,digest,payload) VALUES (?,?,?)', (now(), digest, json.dumps(catalog)))
        rid = cur.lastrowid
        before = {p['id']: p for p in old['products']}; after = {p['id']: p for p in products}
        for k in sorted(before.keys() | after.keys()):
            a, b = before.get(k), after.get(k)
            # Retrieval timestamps are provenance changes, not substantive product changes.
            if product_facts(a) != product_facts(b):
                db.execute('INSERT INTO changes(revision,registration,action,before_json,after_json) VALUES(?,?,?,?,?)',
                    (rid,k,'added' if a is None else 'removed' if b is None else 'changed',json.dumps(a),json.dumps(b)))
        db.execute('INSERT INTO runs(started_at,outcome,detail) VALUES (?,?,?)', (now(),'success',json.dumps({'revision':rid,'published':len(products),'quarantined':quarantine})))
    return catalog


def status_file(output, state, detail, last_success=None):
    atomic_write(pathlib.Path(output).with_name('sync-status.json'), json.dumps({'state': state, 'checked_at': now(), 'message': detail, 'last_successful_sync': last_success}))


def sync(args):
    date_end = today(); db = connect(args.db)
    try:
        if not args.epa:
            raise ValueError('EPA APPRIL export endpoint/file not configured')
        feed = read_feed(args.epa, os.getenv('EPA_FEED_TOKEN'))
        products, quarantined = filter_products(feed, date_end)
        gb = read_feed(args.greenbook, os.getenv('GREENBOOK_FEED_TOKEN')) if args.greenbook else None
        products, gb_status = enrich(products, gb, date_end)
        cdms_location = getattr(args, 'cdms', None)
        cdms = read_feed(cdms_location, os.getenv('CDMS_FEED_TOKEN')) if cdms_location else None
        products, cdms_status = enrich(products, cdms, date_end, 'CDMS')
        catalog = publish(db, products, quarantined, date_end, gb_status, args.allow_large_change, cdms_status)
        atomic_write(args.output, json.dumps(catalog, ensure_ascii=False))
        status_file(args.output, 'success', 'Source check completed', catalog['meta']['last_successful_sync'])
        print(json.dumps({'outcome':'success','published':len(products),'quarantined':len(quarantined),'greenbook':gb_status,'cdms':cdms_status}))
        return 0
    except Exception as exc:
        # Do not put credentials, private feed URLs, or complete remote error bodies in public status.
        with db:
            db.execute('INSERT INTO runs(started_at,outcome,detail) VALUES (?,?,?)', (now(),'failed',str(exc)))
        status_file(args.output, 'failed', 'The last source check failed. Existing published data has been retained.')
        print('Source check failed: '+str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epa', default=os.getenv('EPA_FEED_URL'), help='Normalized APPRIL JSON file or approved feed URL; not the public search page')
    parser.add_argument('--greenbook', default=os.getenv('GREENBOOK_FEED_URL'), help='Normalized Greenbook JSON file or approved feed URL')
    parser.add_argument('--cdms', default=os.getenv('CDMS_FEED_URL'), help='Normalized authorized CDMS/TELUS feed URL or JSON file')
    parser.add_argument('--db', default=str(ROOT/'private/catalog.sqlite'))
    parser.add_argument('--output', default=str(ROOT/'static/catalog.json'))
    parser.add_argument('--allow-large-change', action='store_true')
    args = parser.parse_args()
    return sync(args)

if __name__ == '__main__':
    sys.exit(main())

