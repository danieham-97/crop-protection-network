"""Source collectors. Output is review material, never an auto-approved APPRIL feed.
PPIS fixed widths follow EPA's 2021 data dictionary. Greenbook extraction is an
optional public-page adapter; verify permission and parser behavior with the provider
before enabling at scale. It respects robots.txt and never bypasses authentication.
"""
import argparse, collections, datetime as dt, html.parser, io, json, pathlib, re, time, urllib.parse, urllib.robotparser, zipfile
from catalog import ROOT, SCOPE, atomic_write, download, norm, regno, today

EPA_BASE = 'https://www3.epa.gov/pesticides/PPISdata/'
EPA_FILES = {'product':'product.zip','prodsite':'prodsite.zip','sitename':'sitename.zip','formula':'formula.zip','chemname':'chemname.zip'}
GB_INDEX = 'https://www.greenbook.net/product-types/seed-treatment'


def zipped_lines(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = [x for x in archive.infolist() if x.filename.lower().endswith('.txt')]
        if len(entries) != 1 or entries[0].file_size > 300*1024*1024:
            raise ValueError('Unexpected EPA archive structure or size')
        with archive.open(entries[0]) as f:
            for line in io.TextIOWrapper(f, encoding='cp1252'):
                if line.strip(): yield line.rstrip('\r\n')


def parse_ppis(files):
    """Produce candidates, NOT legal use approval. PPIS sites can include cancelled uses."""
    requested = {norm(x): x for x in SCOPE['sites']}
    code_sites = {}
    for line in files['sitename']:
        if len(line)<10: raise ValueError('Invalid SITENAME row')
        name=line[9:109].strip()
        if norm(name) in requested: code_sites[line[:9]]=requested[norm(name)]
    found=set(code_sites.values())
    unmatched=sorted(set(SCOPE['sites'])-found)
    uses=collections.defaultdict(set)
    for line in files['prodsite']:
        if line[11:20] in code_sites: uses[line[:11]].add(code_sites[line[11:20]])
    names=collections.defaultdict(list)
    for line in files['chemname']:
        if len(line)<27: raise ValueError('Invalid CHEMNAME row')
        names[line[:6]].append((line[296:297].upper()=='Y',line[26:296].strip()))
    formula=collections.defaultdict(list)
    for line in files['formula']:
        if line[:11] not in uses: continue
        choices=names.get(line[11:17],[])
        n=next((s for preferred,s in choices if preferred),choices[0][1] if choices else None)
        v=line[17:24].strip()
        # Numeric 7,4: EPA ASCII uses an implied decimal for integer fields.
        pct=float(v) if '.' in v else int(v)/10000 if v else None
        formula[line[:11]].append({'name':n or 'Unknown PC '+line[11:17], 'pc_code':line[11:17], 'percent':pct,'synonyms':[x[1] for x in choices]})
    products=[]
    for line in files['product']:
        if len(line)<102: raise ValueError('Invalid PRODUCT row')
        key=line[:11]
        if key not in uses or line[22:30]!='00000000': continue
        ais=formula.get(key,[])
        if any('deltamethrin' in norm(s) for a in ais for s in [a['name']]+a['synonyms']): continue
        registration=str(int(key[:6]))+'-'+str(int(key[6:]))
        products.append({'registration_number':registration,'name':line[32:102].strip(),
          'approval_date':line[14:22], 'status_date':None, 'ppis_cancel_date':line[22:30],
          'sites':[{'name':s,'status':'Unverified'} for s in sorted(uses[key])],
          'ingredients':ais, 'ingredients_complete':bool(ais) and all(not x['name'].startswith('Unknown PC ') for x in ais),
          'review_required':['APPRIL status date','Current approved site status','Distributor products and package relationships']})
    if not products: raise ValueError('No matching PPIS candidates; check vocabulary and source format')
    return {'schema_version':1,'source':'EPA PPIS candidate import','retrieved_on':today(),
      'source_url':'https://www.epa.gov/ingredients-used-pesticide-products/ppis-download-product-information-data',
      'complete':False,'unmatched_requested_sites':unmatched,'products':products,
      'note':'PPIS is weekly. APPRIL status dates and current approved site status must be reconciled before publication. This collector covers base Section 3 products only; distributor and marketed-package records require additional mapping.'}


class VisibleHTML(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.links=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag=='a':
            attr=dict(attrs)
            if attr.get('href'): self.links.append(attr['href'])
        if tag in ('h1','h2','h3','li','p','div','dt','dd','br','section'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('h1','h2','h3','li','p','div','dt','dd'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)
    def text(self):
        return '\n'.join(re.sub(r'\s+',' ',x).strip() for x in ''.join(self.parts).splitlines() if x.strip())


def section(text, start, end):
    if start not in text: return ''
    tail=text.split(start,1)[1]
    return tail.split(end,1)[0] if end in tail else tail


def parse_greenbook(page, url):
    h=VisibleHTML(); h.feed(page); text=h.text()
    r=re.search(r'EPA Reg\s*#\s*(\d+-\d+(?:-\d+)?)',text)
    if not r: raise ValueError('Greenbook registration field missing; source layout may have changed')
    title=re.search(r'<h1\b[^>]*>(.*?)</h1>',page,re.S|re.I)
    if not title: raise ValueError('Greenbook product title missing')
    t=VisibleHTML(); t.feed(title.group(1)); name=t.text()
    ingredients=[]
    block=section(text,'Active Ingredients','Signal word')
    if not block: block=section(text,'Active Ingredients','Type')
    for line in block.splitlines():
        m=re.match(r'(.+?)\s*(?:CAS\s+[\d-]+\s*)?([\d.]+)\s*%\s*$',line)
        if m:
            ingredient=re.sub(r'CAS\s+[\d-]+','',m[1]).strip()
            ingredients.append({'name':ingredient,'percent':float(m[2])})
    updated=re.search(r'Last updated\s+([A-Za-z]+ \d{1,2}, \d{4})',text)
    date=dt.datetime.strptime(updated[1],'%b %d, %Y').date().isoformat() if updated else None
    status=re.search(r'\bStatus\s*\n([^\n]+)',text)
    return {'registration_number':regno(r[1]),'name':name,'ingredients':ingredients,
      'ingredients_complete':False,'source_url':url,'source_updated':date,
      'status':status[1].strip() if status else None,
      'note':'Public-page extraction; completeness requires label reconciliation.'}


def fetch_greenbook(url, cache):
    p=urllib.parse.urlparse(url)
    if p.scheme!='https' or p.hostname!='www.greenbook.net': raise ValueError('Unexpected Greenbook host')
    if 'robots' not in cache:
        rp=urllib.robotparser.RobotFileParser()
        rp.parse(download('https://www.greenbook.net/robots.txt').decode().splitlines())
        cache['robots']=rp
    if not cache['robots'].can_fetch('CPN-Seed-Treatment-Catalog',url):
        raise ValueError('Greenbook robots.txt does not permit this collection')
    time.sleep(1)
    return download(url).decode('utf-8')


def greenbook_collect(urls, discover=False, fetch=fetch_greenbook):
    cache={}; visited=set(); product_urls=set(urls)
    if discover:
        queue=[GB_INDEX]
        while queue:
            page=queue.pop(0)
            if page in visited: continue
            if len(visited)>=50: raise ValueError('Discovery exceeded 50 pages; check pagination')
            visited.add(page); h=VisibleHTML(); h.feed(fetch(page,cache))
            for href in h.links:
                link=urllib.parse.urljoin(page,href); p=urllib.parse.urlparse(link)
                if p.scheme!='https' or p.hostname!='www.greenbook.net': continue
                if re.fullmatch(r'/products/\d+/[^/]+',p.path): product_urls.add(link.split('#')[0])
                if p.path=='/product-types/seed-treatment' and p.query and link not in visited: queue.append(link)
    if not product_urls: raise ValueError('No Greenbook product URLs discovered')
    products=[]
    for url in sorted(product_urls): products.append(parse_greenbook(fetch(url,cache),url))
    return {'schema_version':1,'source':'Greenbook','retrieved_on':today(),'complete':False,'products':products,
      'note':'Discovery is best effort. Not proof of comprehensive Greenbook or EPA coverage.'}


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('ppis'); e.add_argument('--output',default=str(ROOT/'private/ppis-candidates.json')); e.add_argument('--input-dir',help='Previously downloaded EPA ZIPs')
    g=sub.add_parser('greenbook'); g.add_argument('--url',action='append',default=[]); g.add_argument('--discover',action='store_true'); g.add_argument('--output',default=str(ROOT/'private/greenbook.json'))
    args=p.parse_args()
    if args.command=='ppis':
        tables={k:list(zipped_lines((pathlib.Path(args.input_dir)/v).read_bytes() if args.input_dir else download(EPA_BASE+v))) for k,v in EPA_FILES.items()}
        result=parse_ppis(tables)
    else: result=greenbook_collect(args.url,args.discover)
    atomic_write(args.output,json.dumps(result,indent=2)); print(json.dumps({'records':len(result['products']),'output':args.output,'complete':False}))

if __name__=='__main__': main()
