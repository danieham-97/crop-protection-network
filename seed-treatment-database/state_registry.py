"""Separate, provenance-bearing state evidence; never infer approval from EPA status.
A provider availability report is not an official state registration decision.
"""
import copy,datetime as dt,json,pathlib,re,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parent
STATES=json.loads((ROOT/'data/us-states.json').read_text())
DEFAULT=ROOT/'data/state-registrations.json'
STATUS={'yes','no','restricted','unknown'}
KINDS={'state_authority','provider_availability'}

def date(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('State evidence requires ISO dates')
    return dt.date.fromisoformat(value)

def validate(payload,as_of):
    cutoff=date(as_of)
    if payload.get('schema_version')!=1 or not isinstance(payload.get('records'),list):raise ValueError('Invalid state evidence feed')
    if date(payload.get('compiled_on'))>cutoff:raise ValueError('Future state compilation date')
    records=[];seen=set()
    for item in payload['records']:
        r=copy.deepcopy(item)
        registration=r.get('registration_number','')
        if not re.fullmatch(r'\d{1,6}-\d{1,5}(?:-\d{1,6})?',registration):raise ValueError('Invalid state evidence EPA registration')
        registration='-'.join(str(int(x)) for x in registration.split('-'));r['registration_number']=registration
        if r.get('jurisdiction') not in STATES:raise ValueError('Invalid state / jurisdiction')
        if r.get('status') not in STATUS or r.get('evidence_kind') not in KINDS:raise ValueError('Invalid state status / evidence kind')
        for key in ('source','source_product_name','source_status','notes'):
            if not isinstance(r.get(key),str) or not r[key].strip():raise ValueError('Missing state evidence '+key)
        for key in ('source_url',):
            u=urllib.parse.urlparse(r.get(key,''))
            if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('State evidence source must be HTTPS')
        observed=date(r.get('observed_on'))
        review=date(r.get('review_due'))
        if observed>cutoff or review<observed:raise ValueError('Invalid state observation / review dates')
        for key in ('source_updated_on','expires_on','effective_on'):
            if r.get(key):date(r[key])
        if r.get('effective_on') and r.get('expires_on') and date(r['effective_on'])>date(r['expires_on']):raise ValueError('State effective date is after expiration')
        if r.get('source_updated_on') and date(r['source_updated_on'])>observed:raise ValueError('Future state source update')
        if r.get('retrieval_basis') not in ('direct_source','indexed_excerpt','authorized_feed'):raise ValueError('Invalid state retrieval basis')
        if r['evidence_kind']=='state_authority' and r['retrieval_basis']=='indexed_excerpt':raise ValueError('Indexed availability cannot establish state-authority evidence')
        identity=(registration,r['jurisdiction'],r['source'],r['source_product_name'])
        if identity in seen:raise ValueError('Duplicate state evidence record')
        seen.add(identity)
        r['review_state']='not-yet-effective' if r.get('effective_on') and date(r['effective_on'])>cutoff else 'expired' if r.get('expires_on') and date(r['expires_on'])<cutoff else 'review-due' if review<cutoff else 'within-review-window'
        records.append(r)
    return {'schema_version':1,'compiled_on':payload['compiled_on'],'evaluated_on':as_of,'jurisdictions':STATES,'records':records,
            'coverage':{'records':len(records),'products':len({r['registration_number'] for r in records}),'state_authority_records':sum(r['evidence_kind']=='state_authority' for r in records),'provider_records':sum(r['evidence_kind']=='provider_availability' for r in records)},
            'note':'State registration and provider availability are separate from federal EPA status and crop-use authorization. Missing evidence means not verified, never not approved. Dates are observations and review deadlines, not approval dates.'}

def load_state_layer(as_of,location=None):
    # Late import avoids a cycle with catalog.publish; the shared reader validates URLs.
    from catalog import read_feed
    payload=read_feed(str(location or DEFAULT))
    return validate(payload,as_of)


def main():
    import argparse
    from catalog import ROOT as APP_ROOT,atomic_write,read_feed,today
    parser=argparse.ArgumentParser(description='Validate and save an authorized state evidence JSON feed; rebuild/import catalog afterward.')
    parser.add_argument('feed',help='Local JSON export or supported HTTPS feed URL')
    parser.add_argument('--output',default=str(DEFAULT))
    args=parser.parse_args();payload=read_feed(args.feed);layer=validate(payload,today())
    atomic_write(args.output,json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(layer['coverage']))
if __name__=='__main__':main()
