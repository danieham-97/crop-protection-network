"""Reviewed label extracts. EPA imports retain references, never infer label content."""
import json, pathlib
from catalog import regno, source_url, valid_date


def load_label_specs(path=None):
    path=path or pathlib.Path(__file__).resolve().parent/'data/label-specs.json'
    data=json.loads(pathlib.Path(path).read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('records'),list):
        raise ValueError('Invalid label-specification reference')
    seen=set()
    for r in data['records']:
        rid=regno(r['registration_number'])
        if rid in seen:raise ValueError('Duplicate label specification')
        seen.add(rid)
        source_url(r['source_url'],{'www3.epa.gov'})
        for field in ('label_date','reviewed_on','review_due'):valid_date(r[field])
        if not r['label_date']<=r['reviewed_on']<=r['review_due']:
            raise ValueError('Invalid label review dates')
        if not r.get('composition') or not r.get('crop') or not r.get('pages'):
            raise ValueError('Label identity and scope required')
        for a in r['composition']:
            if len(a['pc_code'])!=6 or not a['pc_code'].isdigit() or not 0<a['percent']<=100:
                raise ValueError('Invalid label ingredient fingerprint')
        for field in ('targets','rate','application','rei','ppe','restrictions'):
            if not isinstance(r.get(field),str) or not r[field].strip():
                raise ValueError('Label extract field missing: '+field)
    return data
