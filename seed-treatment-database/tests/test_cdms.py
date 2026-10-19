import copy, pathlib, sys, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from catalog import enrich, filter_products
from test_catalog import feed, DAY

def cdms():
 return {'schema_version':1,'source':'CDMS','retrieved_on':DAY,'products':[{
  'registration_number':'100-123','name':'Fixture','source_url':'https://www.cdms.net/LabelsSDS/home/prodidx?key=1',
  'ingredient_basis':'label','ingredients':[{'name':'Metalaxyl','percent':25}],
  'documents':[{'type':'specimen_label','url':'https://www.cdms.net/ldat/example.pdf','revision':'fixture','date':'2026-10-01'}]}]}

class CDMSTests(unittest.TestCase):
 def test_exact_join_and_document_metadata(self):
  p,_=filter_products(feed(),DAY);result,status=enrich(p,cdms(),DAY,'CDMS')
  self.assertEqual(status['matched'],1);self.assertEqual(result[0]['cdms']['documents'][0]['revision'],'fixture')
  self.assertTrue(result[0]['epa_verified']);self.assertEqual(result[0]['ingredients'][0]['percent'],25)
 def test_distributor_is_not_joined_to_base(self):
  p,_=filter_products(feed(),DAY);g=cdms();g['products'][0]['registration_number']='100-123-111'
  result,status=enrich(p,g,DAY,'CDMS');self.assertEqual(status['matched'],0);self.assertNotIn('cdms',result[0])
 def test_sds_composition_not_used_as_formulation(self):
  p,_=filter_products(feed(),DAY);g=cdms();g['products'][0]['ingredient_basis']='sds';g['products'][0]['ingredients']=[{'name':'Water','percent':80}]
  result,status=enrich(p,g,DAY,'CDMS')
  self.assertEqual(result[0]['ingredients'][0]['name'],'Metalaxyl')
  self.assertTrue(any('SDS composition' in x for x in result[0]['cdms']['warnings']))
 def test_invalid_document_url_blocks_import(self):
  p,_=filter_products(feed(),DAY);g=cdms();g['products'][0]['documents'][0]['url']='javascript:alert(1)'
  with self.assertRaises(ValueError):enrich(p,g,DAY,'CDMS')
 def test_label_conflict_preserves_epa_and_warns(self):
  p,_=filter_products(feed(),DAY);g=cdms();g['products'][0]['ingredients'][0]['percent']=40
  result,status=enrich(p,g,DAY,'CDMS');self.assertEqual(result[0]['ingredients'][0]['percent'],25)
  self.assertTrue(any('percentages differ' in x for x in result[0]['cdms']['warnings']))

if __name__=='__main__':unittest.main()
