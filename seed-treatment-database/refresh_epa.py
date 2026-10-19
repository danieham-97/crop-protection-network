"""Import an EPA workbook or download/reconcile the official APPRIL workbook.
Failure preserves the last published catalog. Use deployment cron for unattended updates.
"""
import argparse, copy, datetime as dt, json, os, pathlib, sys, tempfile, urllib.request
from catalog import ROOT, now, today, connect, publish, atomic_write, status_file, read_feed, enrich, seed_published_baseline
from appril_workbook import SOURCE_URL, read_workbook


def download_workbook(destination):
    # Never send source-feed credentials to EPA. Reject unexpected redirects.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): raise ValueError('EPA download redirected; review the official download URL')
    request=urllib.request.Request(SOURCE_URL,headers={'User-Agent':'CPN-Seed-Treatment-Catalog/1.0','Accept':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
    with urllib.request.build_opener(NoRedirect).open(request,timeout=90) as r, open(destination,'wb') as out:
        total=0
        while chunk:=r.read(1024*1024):
            total+=len(chunk)
            if total>300*1024*1024:raise ValueError('EPA workbook exceeds 300 MiB download limit')
            out.write(chunk)
    if total<1000:raise ValueError('EPA workbook response is too small')


def reference_links(products,previous=None):
    """Retain reviewed exact-number links, preserving original observation dates."""
    path=ROOT/'data/source-references.json'
    if not path.exists():return {'Greenbook':0,'CDMS':0}
    refs=json.loads(path.read_text());counts={'Greenbook':0,'CDMS':0}
    for old in (previous or {}).get('products',[]):
        entry=refs.setdefault(old['id'],{})
        for key in ('greenbook','cdms'):
            if old.get(key):entry[key]=copy.deepcopy(old[key])
    for p in products:
        old=refs.get(p['id'],{})
        for provider in ('Greenbook','CDMS'):
            key=provider.lower()
            if old.get(key):
                p[key]=copy.deepcopy(old[key]);p[key]['state']='Saved reference; not automatically refreshed'
                counts[provider]+=1
    return counts


def publish_workbook(products,audit,args,downloaded=False):
    date_end=audit['status_date_end'];checked=now() if downloaded else None
    previous=json.loads(pathlib.Path(args.output).read_text()) if pathlib.Path(args.output).exists() else None
    refs=reference_links(products,previous)
    gb_status={'state':'Saved references only; no live feed','matched':refs['Greenbook']}
    cdms_status={'state':'Saved references only; no live feed','matched':refs['CDMS']}
    for provider in ('Greenbook','CDMS'):
        location=getattr(args,provider.lower(),None)
        if not location:continue
        feed=read_feed(location,os.getenv(provider.upper()+'_FEED_TOKEN'))
        if getattr(args,'require_complete_feeds',False) and (feed.get('complete') is not True or not feed.get('products')):
            raise ValueError(provider+' scheduled feed must be a complete, nonempty export; partial pages cannot be published')
        products,status=enrich(products,feed,date_end,provider)
        if provider=='Greenbook':gb_status=status
        else:cdms_status=status
    metadata={'source_checked':checked,'last_successful_sync':now(),'imported_at':now(),
              'source_snapshot_date':(audit.get('workbook_created_at') or '')[:10] or None,
              'source_acquisition':'Official EPA download' if downloaded else 'User-supplied EPA workbook',
              'epa':'EPA workbook imported','automation':'Host updater; scheduler activation required',
              'complete':True,'complete_for_uploaded_workbook':True,'audit':audit,
              'coverage_note':'All matching Active registrations in this complete workbook, after the requested deltamethrin exclusion. This is not a claim of current EPA website parity.'}
    db=connect(args.db)
    try:
        seed_published_baseline(db,args.output)
        old=db.execute('SELECT payload FROM revisions ORDER BY id DESC LIMIT 1').fetchone()
        if old:
            prev=json.loads(old[0]);prevdate=prev.get('meta',{}).get('source_snapshot_date')
            newdate=metadata['source_snapshot_date']
            if prevdate and (not newdate or newdate<prevdate):raise ValueError('Older or undated EPA workbook would replace newer source data')
        if getattr(args,'automation',None):metadata['automation']=args.automation
        public=publish(db,products,[],date_end,gb_status,getattr(args,'allow_large_change',False),cdms_status,metadata,'live' if downloaded else 'snapshot')
        atomic_write(args.output,json.dumps(public,ensure_ascii=False))
        atomic_write(pathlib.Path(args.output).with_name('epa-import-audit.json'),json.dumps(audit,ensure_ascii=False,indent=2))
        status_file(args.output,'success','EPA workbook imported; creation date and import date retained separately.',public['meta']['last_successful_sync'])
    finally:db.close()
    return public


def run(args):
    try:
        if args.workbook:
            products,audit=read_workbook(args.workbook,today(),True)
        else:
            private=pathlib.Path(args.db).parent;private.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='epa-download-',dir=private) as d:
                file=pathlib.Path(d)/'apprildatadump_public.xlsx'
                download_workbook(file)
                products,audit=read_workbook(file,today(),True)
        result=publish_workbook(products,audit,args,not bool(args.workbook))
        print(json.dumps({'outcome':'success','products':len(result['products']),'excluded':len(audit['excluded_records']),'workbook_created_at':audit['workbook_created_at'],'live_download':not bool(args.workbook)}))
        return 0
    except Exception as exc:
        db=connect(args.db)
        with db:db.execute('INSERT INTO runs(started_at,outcome,detail) VALUES(?,?,?)',(now(),'failed',str(exc)))
        db.close()
        status_file(args.output,'failed','EPA update failed. The last published catalog has been retained.')
        print('EPA update failed: '+str(exc),file=sys.stderr);return 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',help='Read this local EPA XLSX instead of downloading the official workbook')
    parser.add_argument('--greenbook',default=os.getenv('GREENBOOK_FEED_URL'))
    parser.add_argument('--cdms',default=os.getenv('CDMS_FEED_URL'))
    parser.add_argument('--db',default=str(ROOT/'private/catalog.sqlite'))
    parser.add_argument('--output',default=str(ROOT/'static/catalog.json'))
    parser.add_argument('--allow-large-change',action='store_true')
    return run(parser.parse_args())

if __name__=='__main__':sys.exit(main())

