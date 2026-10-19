"""Stage, validate and reconcile a scheduled EPA/provider update.

GitHub publishes the resulting files in one commit. On a host, catalog.json is
the atomic publication pointer; the last good catalog survives source failures.
No provider website scraping, source credentials, or workbook files are published.
"""
import argparse
import copy
import json
import os
import pathlib
import shutil
import sys
import tempfile
from types import SimpleNamespace
from catalog import ROOT, atomic_write, now, product_facts, source_url
from refresh_epa import run as refresh

WORKFLOW='https://github.com/danieham-97/crop-protection-network/actions/workflows/seed-database-update.yml'
SCHEDULE={'kind':'GitHub Actions','cron':'37 6 * * *','timezone':'America/Chicago','workflow_url':WORKFLOW}
AUTOMATION='GitHub Actions: daily at 06:37 America/Chicago; checks for new EPA weekly exports'


def read_json(path,default=None):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)


def changes_between(old,new):
    before={p['id']:product_facts(p) for p in old['products']}
    after={p['id']:product_facts(p) for p in new['products']}
    changes=[]
    for rid in sorted(before.keys()|after.keys()):
        a,b=before.get(rid),after.get(rid)
        if a==b:continue
        fields=sorted(k for k in (a or {}).keys()|(b or {}).keys() if (a or {}).get(k)!=(b or {}).get(k))
        changes.append({'registration_number':rid,'action':'added' if a is None else 'removed' if b is None else 'changed','fields':fields})
    return changes


def needs_publication(old,new):
    if old.get('mode')!=new.get('mode'):return True
    if old['meta'].get('audit',{}).get('sha256')!=new['meta'].get('audit',{}).get('sha256'):return True
    if changes_between(old,new):return True
    # Classification, state evidence and editorial references may change even
    # when EPA's weekly file is byte-identical.
    for key in ('scope','ingredient_reference','education','label_specs','state_registration'):
        if old.get(key)!=new.get(key):return True
    for key in ('greenbook','cdms'):
        a=copy.deepcopy(old['meta'].get(key,{}));b=copy.deepcopy(new['meta'].get(key,{}))
        a.pop('retrieved_on',None);b.pop('retrieved_on',None)
        if a!=b:return True
    return False


def source_states(args,catalog,checked,success):
    states={'EPA':{'state':'checked' if success else 'update failed; last published data retained',
                   'checked_at':checked if success else None,'attempted_at':checked,'workbook_created':catalog['meta'].get('source_snapshot_date'),
                   'source_url':'https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx'}}
    for provider in ('Greenbook','CDMS'):
        configured=bool(getattr(args,provider.lower(),None))
        states[provider]={'state':('checked' if success else 'configured; update did not complete') if configured else 'not configured; saved references only',
                          'checked_at':checked if configured and success else None,
                          'retrieved_on':catalog['meta'].get(provider.lower(),{}).get('retrieved_on')}
    return states


def run(args):
    output=pathlib.Path(args.output);status_path=output.with_name('sync-status.json')
    old=read_json(output)
    if not old or not old.get('products'):raise ValueError('An existing validated catalog is required for a scheduled update')
    previous_status=read_json(status_path,{})
    checked=now();candidate=None
    try:
        # Scheduled URLs must be HTTPS; credentials belong in environment secrets.
        for name in ('greenbook','cdms'):
            value=getattr(args,name,None)
            if value:source_url(value)
        work=ROOT/'private';work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='scheduled-',dir=work) as directory:
            stage=pathlib.Path(directory);staged=stage/'catalog.json'
            shutil.copyfile(output,staged)
            job=SimpleNamespace(workbook=None,db=str(stage/'catalog.sqlite'),output=str(staged),
                                greenbook=args.greenbook,cdms=args.cdms,allow_large_change=False,require_complete_feeds=True,
                                automation=AUTOMATION if os.getenv('GITHUB_ACTIONS')=='true' else 'Manual / host runner; GitHub schedule configured separately')
            if refresh(job):raise RuntimeError('Source update did not complete')
            candidate=read_json(staged)
            changes=changes_between(old,candidate)
            changed=needs_publication(old,candidate)
            counts={k:sum(x['action']==k for x in changes) for k in ('added','changed','removed')}
            status={'state':'success','outcome':'updated' if changed else 'unchanged','checked_at':checked,
                    'last_successful_sync':checked,'last_publication_at':candidate['meta']['imported_at'] if changed else previous_status.get('last_publication_at',old['meta'].get('imported_at')),
                    'message':'New source data published.' if changed else 'Sources checked; no new data. Published catalog unchanged.',
                    'scheduler':SCHEDULE,'sources':source_states(args,candidate,checked,True),
                    'workbook_sha256':candidate['meta']['audit']['sha256'],'changes':counts}
            if changed:
                history_path=output.with_name('update-history.json')
                history=read_json(history_path,{'schema_version':1,'updates':[]})
                entry={'checked_at':checked,'workbook_created':candidate['meta']['source_snapshot_date'],
                       'workbook_sha256':candidate['meta']['audit']['sha256'],'counts':counts,'records':changes}
                history['updates']=([entry]+history['updates'])[:52]
                candidate['meta']['last_update_summary']=counts
                candidate['meta']['source_updates']=status['sources']
                # All acquisition and validation has completed before publication.
                atomic_write(history_path,json.dumps(history,ensure_ascii=False,indent=2))
                atomic_write(output.with_name('epa-import-audit.json'),json.dumps(candidate['meta']['audit'],ensure_ascii=False,indent=2))
                atomic_write(output,json.dumps(candidate,ensure_ascii=False))
            atomic_write(status_path,json.dumps(status,ensure_ascii=False,indent=2))
            print(json.dumps({'outcome':status['outcome'],'products':len(candidate['products']),'changes':counts}))
            return 0
    except Exception as exc:
        # Do not put endpoint URLs, tokens, or arbitrary server errors in public files.
        status={'state':'failed','checked_at':checked,'last_successful_sync':previous_status.get('last_successful_sync'),
                'last_publication_at':previous_status.get('last_publication_at',old['meta'].get('imported_at')),
                'message':'Update failed. Last published catalog retained; see the Actions run.',
                'scheduler':SCHEDULE,'sources':source_states(args,old,checked,False)}
        atomic_write(status_path,json.dumps(status,ensure_ascii=False,indent=2))
        print('Scheduled update failed ('+type(exc).__name__+'). The previous catalog is retained.',file=sys.stderr)
        return 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(ROOT/'static/catalog.json'))
    parser.add_argument('--greenbook',default=os.getenv('GREENBOOK_FEED_URL') or None)
    parser.add_argument('--cdms',default=os.getenv('CDMS_FEED_URL') or None)
    return run(parser.parse_args())


if __name__=='__main__':sys.exit(main())
