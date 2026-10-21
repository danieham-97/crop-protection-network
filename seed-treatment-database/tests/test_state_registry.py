import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from state_registry import validate,STATES
from catalog import connect,publish

DAY='2026-10-19'
def fixture():
    return {'schema_version':1,'compiled_on':DAY,'records':[{'registration_number':'100-1','jurisdiction':'IA','status':'yes','evidence_kind':'provider_availability','source':'Test provider','source_product_name':'Fixture only','source_status':'Yes','source_url':'https://example.org/record','source_updated_on':None,'observed_on':DAY,'review_due':'2026-11-18','expires_on':None,'retrieval_basis':'authorized_feed','notes':'Test fixture, not a real product or registration.'}]}
class StateEvidenceTests(unittest.TestCase):
    def test_full_identity_and_provider_evidence_preserved(self):
        f=fixture();f['records'][0]['registration_number']='000100-00001-000099'
        r=validate(f,DAY)['records'][0]
        self.assertEqual(r['registration_number'],'100-1-99')
        self.assertEqual(r['evidence_kind'],'provider_availability')
        self.assertEqual(r['status'],'yes');self.assertIsNone(r['source_updated_on'])
        self.assertEqual(validate(f,DAY)['coverage']['state_authority_records'],0)
    def test_expiration_and_review_deadline(self):
        f=fixture();f['records'][0]['expires_on']='2026-10-20'
        self.assertEqual(validate(f,'2026-10-21')['records'][0]['review_state'],'expired')
        f['records'][0]['expires_on']=None
        self.assertEqual(validate(f,'2026-11-19')['records'][0]['review_state'],'review-due')
    def test_unknown_is_not_no_and_missing_states_not_filled(self):
        f=fixture();f['records'][0]['status']='unknown'
        r=validate(f,DAY);self.assertEqual(len(r['records']),1);self.assertEqual(r['records'][0]['status'],'unknown')
        self.assertEqual(len(STATES),52)
    def test_effective_date_preserved_and_not_yet_effective(self):
        f=fixture();f['records'][0].update(effective_on='2026-10-21',evidence_kind='state_authority',status='restricted',notes='Fixture restriction: specified crop only.')
        r=validate(f,DAY)['records'][0]
        self.assertEqual(r['effective_on'],'2026-10-21')
        self.assertEqual(r['review_state'],'not-yet-effective')
        self.assertEqual(validate(f,'2026-10-21')['records'][0]['review_state'],'within-review-window')
        f['records'][0]['expires_on']='2026-10-20'
        with self.assertRaises(ValueError):validate(f,DAY)
    def test_invalid_effective_date_fails(self):
        f=fixture();f['records'][0]['effective_on']='2026-02-30'
        with self.assertRaises(ValueError):validate(f,DAY)
    def test_bad_state_status_dates_and_source_fail(self):
        for key,value in [('jurisdiction','ZZ'),('status','approved everywhere'),('observed_on','2027-01-01'),('review_due','2026-01-01'),('source_url','javascript:bad'),('source_updated_on','2027-01-01')]:
            with self.subTest(key=key):
                f=fixture();f['records'][0][key]=value
                with self.assertRaises(ValueError):validate(f,DAY)
    def test_duplicate_source_and_false_authority_fail(self):
        f=fixture();f['records']*=2
        with self.assertRaises(ValueError):validate(f,DAY)
        f=fixture();f['records'][0].update(evidence_kind='state_authority',retrieval_basis='indexed_excerpt')
        with self.assertRaises(ValueError):validate(f,DAY)
    def test_failed_state_feed_does_not_publish_a_revision(self):
        with tempfile.TemporaryDirectory() as d:
            db=connect(pathlib.Path(d)/'db')
            with patch('state_registry.load_state_layer',side_effect=ValueError('Invalid feed')):
                with self.assertRaises(ValueError):publish(db,[{'id':'100-1'}],[],DAY,{})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],0);db.close()
    def test_older_compilation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db=connect(pathlib.Path(d)/'db');layer=validate(fixture(),DAY)
            with patch('state_registry.load_state_layer',return_value=layer):publish(db,[{'id':'100-1'}],[],DAY,{})
            older=copy.deepcopy(layer);older['compiled_on']='2026-10-18'
            with patch('state_registry.load_state_layer',return_value=older):
                with self.assertRaises(ValueError):publish(db,[{'id':'100-1'}],[],DAY,{})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1);db.close()
if __name__=='__main__':unittest.main()
