import copy,json,pathlib,sqlite3,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import record_store
from appril_workbook import read_workbook
from test_workbook import fixture,record
from catalog import atomic_write
from scheduled_update import run
from types import SimpleNamespace

class RecordStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.db=self.root/'private/catalog.sqlite';self.xlsx=self.root/'source.xlsx'
        self.rows=[record(REG_NUM='100-'+str(i)) for i in range(1,6)]
        self.first=self.parse(self.rows)
    def tearDown(self):self.tmp.cleanup()
    def parse(self,rows,tracked=()):
        fixture(self.xlsx,rows);products,audit=read_workbook(self.xlsx,'2026-10-19',tracked=tracked)
        return {'products':products,'meta':{'audit':audit,'source_snapshot_date':'2026-09-21','imported_at':'2026-10-19','status_date_end':'2026-10-19'},'mode':'live'}
    def sql(self,query):
        with sqlite3.connect(self.db) as db:return db.execute(query).fetchall()
    def save(self,data,checked='2026-10-19'):
        return record_store.upsert_catalog(self.db,data,self.first,checked)
    def test_delta_upserts_unchanged_identity_and_repeat(self):
        self.assertEqual(self.save(self.first)['initialized'],5)
        original=self.sql('SELECT registration_number,updated_at FROM products')
        rows=copy.deepcopy(self.rows);rows[0]['STATUS']='Conditional';rows.append(record(REG_NUM='100-6'))
        second=self.parse(rows);counts=self.save(second,'2026-10-26')
        self.assertEqual((counts['added'],counts['changed'],counts['unchanged']),(1,1,4))
        self.assertEqual(self.sql("SELECT latest_epa_status FROM products WHERE registration_number='100-1'")[0][0],'Conditional')
        self.assertEqual(self.sql("SELECT updated_at FROM products WHERE registration_number='100-2'")[0][0],dict(original)['100-2'])
        self.assertEqual(self.save(second,'2026-11-02')['unchanged'],6)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM product_changes')[0][0],2)
    def test_inactive_status_and_reactivation_preserve_identity(self):
        self.save(self.first);rows=copy.deepcopy(self.rows)
        rows[0].update(STATUS_GROUP='Inactive',STATUS='Cancelled',STATUS_DESC='Cancelled fixture')
        counts=self.save(self.parse(rows,tracked=['100-1']),'2026-10-26')
        self.assertEqual(counts['removed'],1)
        self.assertEqual(self.sql("SELECT in_scope,latest_status_group,latest_epa_status FROM products WHERE registration_number='100-1'")[0],(0,'Inactive','Cancelled'))
        self.assertEqual(self.save(self.first,'2026-11-02')['reactivated'],1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM products')[0][0],5)
    def test_missing_is_not_inferred_cancellation(self):
        self.save(self.first);self.save(self.parse(self.rows[1:],tracked=['100-1']))
        self.assertEqual(self.sql("SELECT in_scope,latest_epa_status FROM products WHERE registration_number='100-1'")[0],(0,None))
        self.assertEqual(len(record_store.tracked_registrations(self.db)),5)
    def test_unrelated_invalid_identity_does_not_break_status_tracking(self):
        rows=self.rows+[record(REG_NUM='INVALID',REG_TYPE='DP',STATUS_GROUP='Inactive',SITES='Apples')]
        self.assertEqual(len(self.parse(rows,tracked=['100-1'])['products']),5)
        # A matching active row still fails the original strict validation.
        rows[-1].update(STATUS_GROUP='Active',SITES=self.rows[0]['SITES'])
        with self.assertRaisesRegex(ValueError,'registration number'):
            self.parse(rows,tracked=['100-1'])
    def test_rollback_on_sql_failure(self):
        self.save(self.first);before=self.sql('SELECT * FROM products')
        newer=self.parse(self.rows+[record(REG_NUM='100-6')])
        original=record_store.write_record
        def fail_after_write(*args):original(*args);raise RuntimeError('fixture storage failure')
        with patch('record_store.write_record',side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):self.save(newer)
        self.assertEqual(self.sql('SELECT * FROM products'),before)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM worker_runs')[0][0],1)
    def test_older_and_large_loss_blocked(self):
        self.save(self.first)
        older=copy.deepcopy(self.first);older['meta']['source_snapshot_date']='2020-01-01'
        with self.assertRaisesRegex(ValueError,'Older'):self.save(older)
        with self.assertRaisesRegex(ValueError,'30%'):self.save(self.parse(self.rows[:2]))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM worker_runs')[0][0],1)
    def test_new_database_backfill_is_idempotent(self):
        self.save(self.first);counts=self.save(self.first,'2026-10-26')
        self.assertEqual(counts['initialized'],0);self.assertEqual(counts['unchanged'],5)
        self.assertFalse(self.sql('SELECT * FROM product_changes'))
    def test_full_distributor_number_and_missing_site_observations(self):
        data=self.parse(self.rows+[record(REG_NUM='100-1-99',REG_TYPE='DP')]);self.save(data)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM products')[0][0],6)
        rows=copy.deepcopy(self.rows);rows[0]['SITES']='Apples'
        newer=self.parse(rows,tracked=['100-1','100-1-99'])
        # Preserve the distributor in the candidate to keep this scenario below the loss threshold.
        newer['products'].append(next(p for p in data['products'] if p['id']=='100-1-99'))
        self.save(newer)
        self.assertEqual(self.sql("SELECT latest_epa_status,in_scope FROM products WHERE registration_number='100-1'")[0],('Registered',0))
    def test_worker_repeated_download_and_failure_retention(self):
        out=self.root/'public/catalog.json';atomic_write(out,json.dumps(self.first))
        args=SimpleNamespace(output=str(out),db=str(self.db),greenbook=None,cdms=None)
        self.save(self.first)
        next_rows=copy.deepcopy(self.rows);next_rows[0]['STATUS']='Conditional'
        def fake_download(destination):fixture(destination,next_rows)
        with patch('refresh_epa.download_workbook',side_effect=fake_download):
            self.assertEqual(run(args),0);self.assertEqual(run(args),0)
        before=self.sql('SELECT * FROM products');published=out.read_bytes()
        with patch('refresh_epa.download_workbook',side_effect=ValueError('fixture network failure')):
            self.assertEqual(run(args),1)
        self.assertEqual(before,self.sql('SELECT * FROM products'));self.assertEqual(published,out.read_bytes())

if __name__=='__main__':unittest.main()
