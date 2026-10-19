"""Stream EPA's APPRIL public XLSX export; never execute workbook SQL or macros.
The source SITES column is a list of EPA-indexed uses, not a per-site approval flag.
"""
import collections, copy, datetime as dt, hashlib, json, pathlib, re, sys, zipfile
from xml.etree import ElementTree as ET
from catalog import SCOPE, INGREDIENTS, norm, regno, valid_date, now

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
SOURCE_URL = 'https://www3.epa.gov/pesticides/appril/apprildatadump_public.xlsx'
REQUIRED = {'REG_NUM','REG_TYPE','PRODUCT_NAME','COMPANY_NAME','STATUS_GROUP','STATUS','STATUS_DESC','STATUS_DT','AIS','SITES','PEST_CAT','MAX_LABEL_DT'}
SITE_PATTERNS = [(s,re.compile(r'(?:^|,\s*)'+re.escape(s).replace(r'\ ',r'\s+')+r'(?=,|$)',re.I)) for s in SCOPE['sites']]
AI_END = re.compile(r'\s+\((\d{6})/([^)]*)\)\s*-\s*\(([\d.]*)%\)\s*(?:,\s*|$)')

def excel_date(value, date1904=False):
    if not str(value).strip(): return None
    try:
        number=float(value)
        if number < 1 or number > 200000: raise ValueError('Excel date out of range')
        return ((dt.datetime(1904,1,1) if date1904 else dt.datetime(1899,12,30))+dt.timedelta(days=number)).date().isoformat()
    except (ValueError, OverflowError):
        return valid_date(value)


def cell_value(cell, strings):
    kind=cell.get('t')
    if kind=='inlineStr': return ''.join(t.text or '' for t in cell.iter(NS+'t'))
    v=cell.find(NS+'v'); value=v.text if v is not None and v.text else ''
    if kind=='s': return strings[int(value)]
    if kind=='e': raise ValueError('Workbook contains an error cell')
    if cell.find(NS+'f') is not None: raise ValueError('Formula cells are not expected in the EPA data export')
    return value


def rows(path):
    """Yield metadata, then (Excel row number, column-keyed dict). Validate full XML."""
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > 3*1024**3: raise ValueError('Workbook expanded size exceeds limit')
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        sheets=wb.find(NS+'sheets')
        target=next((s for s in sheets if s.get('name')=='ACTIVE_REGISTRATIONS5_PUBLIC_V'),None)
        if target is None: raise ValueError('Expected APPRIL registration sheet is missing; review schema')
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rid=target.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        sheet=next(r.get('Target') for r in rels if r.get('Id')==rid)
        sheet=sheet.lstrip('/') if sheet.startswith('/') else 'xl/'+sheet
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for s in ET.fromstring(z.read('xl/sharedStrings.xml')):
                strings.append(''.join(t.text or '' for t in s.iter(NS+'t')))
        core=ET.fromstring(z.read('docProps/core.xml'))
        created=core.find('{http://purl.org/dc/terms/}created')
        created=created.text if created is not None else None
        props=wb.find(NS+'workbookPr')
        date1904=props is not None and props.get('date1904') in ('true','1')
        yield {'sheet':target.get('name'),'workbook_created_at':created,'date1904':date1904}
        with z.open(sheet) as f:
            # Stream using stdlib; clear row nodes to keep memory bounded.
            context=ET.iterparse(f, events=('start','end')); data=None; expected_last=None; last_row=0; count=0
            for event,e in context:
                if event=='start' and e.tag==NS+'sheetData': data=e
                elif event=='end' and e.tag==NS+'dimension':
                    expected_last=int(re.search(r'(\d+)$',e.get('ref')).group(1))
                elif event=='end' and e.tag==NS+'row':
                    rownum=int(e.get('r'))
                    if rownum!=last_row+1: raise ValueError('Missing or nonsequential row in EPA export')
                    values={re.sub(r'\d','',c.get('r')):cell_value(c,strings) for c in e}
                    yield rownum,values
                    last_row=rownum;count+=1
                    if data is not None:data.clear()
            if not count or (expected_last is not None and last_row!=expected_last):
                raise ValueError('Workbook row count does not match its declared extent')


def parse_ingredients(text):
    if not text.strip(): return [],False
    result=[]; position=0
    for m in AI_END.finditer(text):
        name=text[position:m.start()].strip(' ,\r\n')
        if not name: raise ValueError('Missing active ingredient name')
        percent=float(m.group(3)) if m.group(3) else None
        if percent is not None and not 0 < percent <=100: raise ValueError('Invalid active ingredient concentration')
        result.append({'name':name,'percent':percent,'pc_code':m.group(1),'cas':m.group(2) or None})
        position=m.end()
    if text[position:].strip(' ,\r\n') or not result: raise ValueError('Unparsed text in EPA AIS column')
    if sum(a['percent'] or 0 for a in result)>100.01: raise ValueError('Total active ingredient concentration exceeds 100%')
    return result,True


def selected_sites(text):
    if 'seed treatment' not in norm(text): return []
    return [s for s,p in SITE_PATTERNS if p.search(text.strip())]


def read_workbook(path, date_end, progress=False):
    valid_date(date_end);path=pathlib.Path(path)
    with path.open('rb') as source: digest=hashlib.file_digest(source,'sha256').hexdigest()
    stream=rows(path);meta=next(stream);created=meta['workbook_created_at']
    if created and created[:10]>date_end: raise ValueError('Workbook creation date is after the selected cutoff')
    heads=None; candidates=[];bases={};products=[];excluded=[];seen=set();groups=collections.Counter();types=collections.Counter();site_counts=collections.Counter();matched_all=0; active_matches=0; count=0
    for rownum,values in stream:
        if heads is None:
            heads=values
            if not REQUIRED.issubset(heads.values()):raise ValueError('APPRIL columns missing: '+', '.join(sorted(REQUIRED-set(heads.values()))))
            if len(set(heads.values()))!=len(heads):raise ValueError('Duplicate APPRIL column headers')
            continue
        count+=1
        raw={heads[k]:v for k,v in values.items() if k in heads}
        if raw.get('STATUS_GROUP') not in ('Active','Inactive'):raise ValueError('Unexpected EPA status group; review schema')
        groups[raw['STATUS_GROUP']]+=1
        if raw.get('REG_TYPE')=='Sec3':
            bases[regno(raw['REG_NUM'])]={k:raw.get(k,'') for k in ['REG_NUM','PRODUCT_NAME','STATUS_GROUP','STATUS','AIS','PEST_CAT','PESTICIDE_TYPE']}
            bases[regno(raw['REG_NUM'])]['source_row']=rownum
        if progress and count%50000==0:print(f'Read {count:,} EPA rows…',file=sys.stderr,flush=True)
        sites=selected_sites(raw.get('SITES',''))
        if not sites:continue
        matched_all+=1
        if raw.get('STATUS_GROUP')!='Active':continue
        active_matches+=1
        candidates.append((rownum,raw,sites))
    for rownum,raw,sites in candidates:
        rid=regno(raw['REG_NUM'])
        if rid in seen:raise ValueError('Duplicate active registration in EPA workbook: '+rid)
        seen.add(rid)
        status_date=excel_date(raw.get('STATUS_DT',''),meta['date1904'])
        if status_date is None: raise ValueError('Missing EPA status date: '+rid)
        if status_date>date_end:
            excluded.append({'registration_number':rid,'reason':'Status date after cutoff','source_row':rownum});continue
        basis='EPA product row';base=None
        ai_text=raw.get('AIS','')
        if not ai_text and raw['REG_TYPE']=='DP':
            base=bases.get('-'.join(rid.split('-')[:2]))
            if base and base['AIS']:
                ai_text=base['AIS'];basis='Related EPA base registration'
            else:basis='Not supplied'
        ais,complete=parse_ingredients(ai_text)
        if not complete:basis='Not supplied'
        if any('deltamethrin' in norm(a['name']) or a['cas'] in SCOPE['excluded_cas'] or a['pc_code'] in SCOPE['excluded_pc_codes'] for a in ais):
            excluded.append({'registration_number':rid,'name':raw['PRODUCT_NAME'],'reason':'Deltamethrin excluded','source_row':rownum});continue
        if not raw.get('PRODUCT_NAME','').strip():raise ValueError('Missing product name: '+rid)
        categories=[x.strip() for x in (raw.get('PEST_CAT') or (base or {}).get('PEST_CAT','')).split(',') if x.strip()]
        purposes=list(categories)
        if not purposes:purposes=sorted({INGREDIENTS.get(norm(a['name']),{}).get('purpose','Unclassified') for a in ais})
        p={'id':rid,'registration_number':rid,'name':raw['PRODUCT_NAME'],'registrant':raw.get('COMPANY_NAME') or 'Not supplied',
           'aliases':[], 'alternate_names_raw':raw.get('ABNS',''),
           'record_type':raw['REG_TYPE'],'sites':sites,'ingredients':ais,'purposes':purposes,
           'pest_categories':categories,'pesticide_type':raw.get('PESTICIDE_TYPE') or (base or {}).get('PESTICIDE_TYPE',''),
           'use_type':raw.get('USE_TYPE') or 'Not supplied', 'purpose_basis':basis, 'ingredient_basis':basis,
           'base_registration':base['REG_NUM'] if base else None, 'base_product_name':base['PRODUCT_NAME'] if base else None,
           'base_source_row':base['source_row'] if base else None, 'base_status_group':base['STATUS_GROUP'] if base else None,
           'base_product_ingredients':copy.deepcopy(ais) if base else None,'status':'Active Products','epa_status':raw.get('STATUS'),'epa_status_description':raw.get('STATUS_DESC'),
           'status_date':status_date,'epa_verified':True,'ingredient_quality':'missing' if not ais else ('base-linked' if basis=='Related EPA base registration' else ('partial' if any(a['percent'] is None for a in ais) else 'verified')),
           'notes':'Active status and seed-treatment sites are reported by the supplied EPA export. Consult the current label for permitted uses.',
           'source':'EPA APPRIL workbook','source_url':SOURCE_URL,'source_updated':None,
           'latest_label_date':excel_date(raw.get('MAX_LABEL_DT',''),meta['date1904']),
           'source_snapshot_date':created[:10] if created else None,'retrieved_at':None,'imported_at':now(),
           'source_row':rownum,'source_sites_note':'Exact matches in the EPA export SITES column. The export does not provide individual site approval dates or status flags.',
           'greenbook':None,'cdms':None}
        if basis=='Not supplied':p['notes']+=' Active ingredients are missing; the deltamethrin exclusion cannot be independently confirmed for this record.'
        if base and ais:
            p['notes']+=' Ingredient values come from related base registration '+base['REG_NUM']+' because the distributor AIS field is blank. Verify the distributor label; its use claims can be narrower.'
            if base['STATUS_GROUP']!='Active':p['notes']+=' Review required: the base registration is not Active in this export.'
        if any(a['percent'] is None for a in ais):p['notes']+=' EPA did not supply all ingredient percentages.'
        products.append(p);site_counts.update(sites);types[p['record_type']]+=1
        if progress and len(products)%250==0:print(f'Collected {len(products)} matching active registrations…',file=sys.stderr,flush=True)
    if not products:raise ValueError('No in-scope active products; prior catalog retained')
    products.sort(key=lambda p:(norm(p['name']),p['id']))
    audit={**meta,'source_file':path.name,'sha256':digest,'source_url':SOURCE_URL,'row_count':count,'status_group_counts':dict(groups),
           'all_status_matching_site_rows':matched_all,'active_matching_site_rows':active_matches,
           'published_products':len(products),'excluded_records':excluded,'record_type_counts':dict(types),
           'counts_by_site':{s:site_counts[s] for s in SCOPE['sites']},'status_date_start':None,'status_date_end':date_end,
           'min_published_status_date':min(p['status_date'] for p in products),'max_published_status_date':max(p['status_date'] for p in products),
           'base_linked_formulations':sum(p['ingredient_basis']=='Related EPA base registration' for p in products),
           'base_status_conflicts':sum(bool(p['base_registration']) and p['base_status_group']!='Active' for p in products),
           'missing_formulation_products':sum(not p['ingredients'] for p in products),
           'missing_percent_products':sum(any(a['percent'] is None for a in p['ingredients']) for p in products),
           'distinct_ingredients':len({a['pc_code'] for p in products for a in p['ingredients']}),
           'complete_for_uploaded_workbook':True,'currency_note':'Workbook creation metadata is shown as provenance; it does not prove that the file is the latest EPA release or that every source field was current on that date.'}
    return products,audit
