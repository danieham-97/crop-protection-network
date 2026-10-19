"""Safety-critical scheduled publication checks; never contact source websites."""
import copy,gzip,json,pathlib,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from catalog import ROOT,connect,seed_published_baseline,enrich,today
from refresh_epa import publish_workbook
from scheduled_update import changes_between,needs_publication,run
from test_workbook import fixture,record
from appril_workbook import read_workbook


class ScheduledTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
        self.out=self.root/'catalog.json'
        self.catalog=json.loads(gzip.decompress((ROOT/'tests/fixtures/catalog-2026-10-19.json.gz').read_bytes()))
        self.catalog['mode']='live';self.out.write_text(json.dumps(self.catalog))
        self.args=SimpleNamespace(output=str(self.out),greenbook=None,cdms=None)

    def tearDown(self):self.temp.cleanup()

    def fake_refresh(self,job):
        pathlib.Path(job.output).write_text(json.dumps(self.candidate))
        return 0

    def test_dates_alone_are_not_product_changes(self):
        new=copy.deepcopy(self.catalog)
        for p in new['products']:
            p['imported_at']='2099-01-01';p['source_row']=1
            if p.get('cdms'):p['cdms']['retrieved_at']='2099-01-01'
        self.assertEqual(changes_between(self.catalog,new),[])
        self.assertFalse(needs_publication(self.catalog,new))

    def test_exact_identity_and_changed_fields_are_reported(self):
        new=copy.deepcopy(self.catalog);deleted=new['products'].pop()
        new['products'][0]['safety']['signal_word']='CHANGED FIXTURE'
        extra=copy.deepcopy(new['products'][0]);extra['id']=extra['registration_number']='999999-99999';new['products'].append(extra)
        changes={x['registration_number']:x for x in changes_between(self.catalog,new)}
        self.assertEqual(changes[deleted['id']]['action'],'removed')
        self.assertEqual(changes[extra['id']]['action'],'added')
        self.assertIn('safety',changes[new['products'][0]['id']]['fields'])

    def test_unchanged_check_keeps_catalog_bytes_and_updates_status(self):
        self.candidate=copy.deepcopy(self.catalog);before=self.out.read_bytes()
        with patch('scheduled_update.refresh',side_effect=self.fake_refresh):self.assertEqual(run(self.args),0)
        self.assertEqual(before,self.out.read_bytes())
        status=json.loads(self.out.with_name('sync-status.json').read_text())
        self.assertEqual(status['outcome'],'unchanged')
        self.assertIsNone(status['sources']['CDMS']['checked_at'])

    def test_provider_revision_triggers_publication_without_epa_change(self):
        self.candidate=copy.deepcopy(self.catalog)
        p=next(p for p in self.candidate['products'] if p.get('cdms'))
        p['cdms']['source_updated']='2026-10-19'
        with patch('scheduled_update.refresh',side_effect=self.fake_refresh):self.assertEqual(run(self.args),0)
        history=json.loads(self.out.with_name('update-history.json').read_text())
        self.assertIn('cdms',history['updates'][0]['records'][0]['fields'])

    def test_failed_refresh_retains_catalog_and_original_success_date(self):
        self.out.with_name('sync-status.json').write_text(json.dumps({'last_successful_sync':'2026-10-01'}))
        before=self.out.read_bytes()
        with patch('scheduled_update.refresh',return_value=1):self.assertEqual(run(self.args),1)
        self.assertEqual(before,self.out.read_bytes())
        status=json.loads(self.out.with_name('sync-status.json').read_text())
        self.assertEqual(status['state'],'failed');self.assertEqual(status['last_successful_sync'],'2026-10-01')

    def test_fresh_runner_baseline_blocks_excessive_removals(self):
        path=self.root/'epa.xlsx';fixture(path,[record()]);products,audit=read_workbook(path,'2026-10-19')
        args=SimpleNamespace(db=str(self.root/'fresh.sqlite'),output=str(self.out))
        before=self.out.read_bytes()
        with self.assertRaisesRegex(ValueError,'30%'):publish_workbook(products,audit,args)
        self.assertEqual(before,self.out.read_bytes())

    def test_fresh_runner_baseline_blocks_older_workbook(self):
        path=self.root/'epa.xlsx';fixture(path,[record()],created='2020-01-01T00:00:00Z');products,audit=read_workbook(path,'2026-10-19')
        args=SimpleNamespace(db=str(self.root/'fresh.sqlite'),output=str(self.out))
        with self.assertRaisesRegex(ValueError,'Older'):publish_workbook(products,audit,args)

    def test_catalog_reference_updates_trigger_republish(self):
        new=copy.deepcopy(self.catalog);new['education']['reviewed_on']='2026-10-20'
        self.assertTrue(needs_publication(self.catalog,new))

    def test_invalid_feed_url_is_not_published_or_leaked(self):
        self.args.cdms='https://user:secret@example.com/private'
        before=self.out.read_bytes()
        with patch('scheduled_update.refresh') as refresh:
            self.assertEqual(run(self.args),1);refresh.assert_not_called()
        self.assertEqual(before,self.out.read_bytes())
        self.assertNotIn('secret',self.out.with_name('sync-status.json').read_text())

    def test_invalid_baseline_does_not_disable_guard(self):
        self.out.write_text('{"products":[]}');db=connect(self.root/'new.sqlite')
        try:
            with self.assertRaises(ValueError):seed_published_baseline(db,self.out)
        finally:db.close()

    def test_scheduled_partial_provider_feed_blocks_release(self):
        args=SimpleNamespace(db=str(self.root/'db'),output=str(self.out),cdms='https://example.com/feed',require_complete_feeds=True)
        before=self.out.read_bytes()
        with patch('refresh_epa.read_feed',return_value={'source':'CDMS','products':[]}):
            with self.assertRaisesRegex(ValueError,'complete'):publish_workbook(copy.deepcopy(self.catalog['products']),self.catalog['meta']['audit'],args)
        self.assertEqual(self.out.read_bytes(),before)

    def test_older_provider_revision_is_rejected(self):
        p=copy.deepcopy(next(p for p in self.catalog['products'] if p.get('cdms')))
        p['cdms']['source_updated']='2026-10-01'
        feed={'schema_version':1,'source':'CDMS','retrieved_on':today(),'products':[{'registration_number':p['id'],'name':p['name'],'source_url':p['cdms']['source_url'],'source_updated':'2026-09-01'}]}
        with self.assertRaisesRegex(ValueError,'older'):enrich([p],feed,today(),'CDMS')


if __name__=='__main__':unittest.main()
