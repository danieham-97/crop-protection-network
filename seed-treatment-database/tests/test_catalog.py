import copy, datetime as dt, json, pathlib, sqlite3, sys, tempfile, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from catalog import SCOPE, filter_products, snapshot_validate, enrich, connect, publish, regno, sync
from sources import parse_greenbook, parse_ppis
from types import SimpleNamespace

DAY='2026-10-16'
def feed():
 return {'schema_version':1,'source':'EPA APPRIL','source_url':'https://ordspub.epa.gov/ords/pesticides/f?p=APPRIL_PUBLIC:2','complete':True,'retrieved_on':DAY,
 'query':{'status_group':'Active Products','status_date_start':None,'status_date_end':DAY,'sites':SCOPE['sites']},
 'products':[{'registration_number':'100-123','name':'Validation fixture — not a commercial product','registrant':'Test','status_group':'Active Products','status_date':'2026-01-01',
 'sites':[{'name':SCOPE['sites'][11],'status':'Approved'}], 'ingredients_complete':True,'ingredients':[{'name':'Metalaxyl','percent':25}]}]}

class CatalogTests(unittest.TestCase):
 def test_exact_14_sites_and_blank_start(self):
  self.assertEqual(len(SCOPE['sites']),14); self.assertIsNone(SCOPE['status_date_start'])
  f=feed();f['query']['sites']=f['query']['sites'][:-1]
  with self.assertRaises(ValueError):filter_products(f,DAY)
 def test_case_whitespace_only_site_match(self):
  f=feed();f['products'][0]['sites'][0]['name']=' SOYBEANS   (seed treatment) '
  good,bad=filter_products(f,DAY);self.assertEqual(len(good),1)
  f['products'][0]['sites'][0]['name']='Soybeans'
  self.assertEqual(len(filter_products(f,DAY)[0]),0)
 def test_storage_only_excluded(self):
  f=feed();f['products'][0]['sites']=[{'name':'Corn (grain storage)','status':'Approved'}]
  self.assertEqual(len(filter_products(f,DAY)[0]),0)
 def test_canceled_site_not_published(self):
  f=feed();f['products'][0]['sites'][0]['status']='Cancelled'
  self.assertEqual(len(filter_products(f,DAY)[0]),0)
 def test_deltamethrin_name_synonym_and_cas(self):
  for ai in [{'name':'Deltamethrin','percent':2},{'name':'Chemical synonym','synonyms':['DELTAMETHRIN'],'percent':2},{'name':'Chemical synonym','cas':'52918-63-5','percent':2}]:
   f=feed();f['products'][0]['ingredients']=[ai]
   self.assertEqual(len(filter_products(f,DAY)[0]),0)
 def test_status_dates_not_source_dates(self):
  f=feed();f['products'][0]['status_date']=None;f['products'][0]['source_updated']='2026-10-01'
  self.assertEqual(len(filter_products(f,DAY)[0]),0)
  f['products'][0]['status_date']='2026-10-17';self.assertEqual(len(filter_products(f,DAY)[0]),0)
 def test_partial_feed_blocked(self):
  f=feed();f['complete']=False
  with self.assertRaises(ValueError):filter_products(f,DAY)
 def test_partial_formulation_quarantined(self):
  f=feed();f['products'][0]['ingredients_complete']=False
  good,bad=filter_products(f,DAY);self.assertFalse(good);self.assertTrue(bad)
 def test_duplicate_registration_aborts(self):
  f=feed();f['products'].append(copy.deepcopy(f['products'][0]))
  with self.assertRaises(ValueError):filter_products(f,DAY)
 def test_stale_or_future_snapshot_aborts(self):
  f=feed();f['retrieved_on']='2026-10-15'
  with self.assertRaises(ValueError):filter_products(f,DAY)
 def test_distributor_number_preserved(self):
  self.assertEqual(regno('071532-00022-007969'),'71532-22-7969')
 def test_percent_validation(self):
  for value in [-1,101,float('nan'),float('inf'),True]:
   f=feed();f['products'][0]['ingredients'][0]['percent']=value
   with self.assertRaises(ValueError):filter_products(f,DAY)
 def test_full_number_join_and_conflict(self):
  p,_=filter_products(feed(),DAY)
  gb={'schema_version':1,'source':'Greenbook','retrieved_on':DAY,'products':[{'registration_number':'100-123-999','name':'Another product','source_url':'https://www.greenbook.net/products/1/example','ingredients':[]}]}
  result,status=enrich(p,gb,DAY);self.assertIsNone(result[0]['greenbook'])
  gb['products'][0]['registration_number']='100-123';gb['products'][0]['ingredients']=[{'name':'Metalaxyl','percent':40}]
  result,status=enrich(p,gb,DAY);self.assertEqual(result[0]['ingredients'][0]['percent'],25)
  self.assertTrue(result[0]['greenbook']['warnings'])
 def test_atomic_history_deletions_and_loss_guard(self):
  with tempfile.TemporaryDirectory() as d:
   db=connect(pathlib.Path(d)/'db.sqlite');p,_=filter_products(feed(),DAY)
   many=[]
   for i in range(5):
    x=copy.deepcopy(p[0]);x['id']=x['registration_number']='100-'+str(100+i);many.append(x)
   publish(db,many,[],DAY,{},False)
   with self.assertRaises(ValueError):publish(db,many[:2],[],DAY,{},False)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1)
   publish(db,many[:4],[],DAY,{},False)
   self.assertEqual(db.execute("SELECT COUNT(*) FROM changes WHERE action='removed'").fetchone()[0],1)
   db.close()
 def test_failure_preserves_existing_output(self):
  with tempfile.TemporaryDirectory() as d:
   out=pathlib.Path(d)/'catalog.json';out.write_text('last good catalog')
   code=sync(SimpleNamespace(epa=None,greenbook=None,db=str(pathlib.Path(d)/'db'),output=str(out),allow_large_change=False))
   self.assertEqual(code,1);self.assertEqual(out.read_text(),'last good catalog')
   self.assertEqual(json.loads((pathlib.Path(d)/'sync-status.json').read_text())['state'],'failed')
 def test_no_javascript_source_link(self):
  f=feed();f['source_url']='javascript:alert(1)'
  with self.assertRaises(ValueError):filter_products(f,DAY)

class SourceTests(unittest.TestCase):
 def test_greenbook_missing_fields_fail_without_publication(self):
  with self.assertRaises(ValueError):parse_greenbook('<h1>Example</h1>','https://www.greenbook.net/products/1/example')
 def test_greenbook_parser_fixture(self):
  html='<h1>Example</h1><h2>Active Ingredients</h2><ul><li>Metalaxyl CAS 57837-19-1 29.99%</li></ul><div>Signal word</div><div>Caution</div><div>EPA Reg #</div><div>100-123</div><div>Last updated</div><div>Dec 31, 2025</div><div>Status</div><div>Active Registration</div>'
  p=parse_greenbook(html,'https://www.greenbook.net/products/1/example')
  self.assertEqual(p['registration_number'],'100-123');self.assertEqual(p['ingredients'][0]['name'],'Metalaxyl');self.assertAlmostEqual(p['ingredients'][0]['percent'],29.99);self.assertFalse(p['ingredients_complete'])
 def test_ppis_candidates_never_masquerade_as_appril(self):
  reg='00010000123';sc='123456789';pc='000001'
  product=reg+'01'+'3'+'20200101'+'00000000'+'  '+'Fixture'.ljust(70)+'F'+'00'+'F'
  data={'sitename':[sc+SCOPE['sites'][11].ljust(100)],'prodsite':[reg+sc],'chemname':[pc+'ISO'.ljust(20)+'Metalaxyl'.ljust(270)+'Y'],'formula':[reg+pc+'299900 '],'product':[product]}
  result=parse_ppis(data);self.assertFalse(result['complete']);self.assertIsNone(result['products'][0]['status_date']);self.assertEqual(result['products'][0]['sites'][0]['status'],'Unverified');self.assertAlmostEqual(result['products'][0]['ingredients'][0]['percent'],29.99)

if __name__=='__main__':unittest.main()
