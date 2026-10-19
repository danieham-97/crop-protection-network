"""Check the actual committed catalog independently of source availability."""
import collections
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from catalog import SCOPE, regno, valid_date

ROOT=pathlib.Path(__file__).resolve().parents[1]

class PublishedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'static/catalog.json').read_text())
        cls.products=cls.catalog['products']
        cls.audit=json.loads((ROOT/'static/epa-import-audit.json').read_text())

    def test_census_and_site_counts_reconcile(self):
        ids=[p['id'] for p in self.products]
        self.assertTrue(ids);self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(self.audit['published_products'],len(ids))
        self.assertEqual(self.audit['active_matching_site_rows'],len(ids)+len(self.audit['excluded_records']))
        counts=collections.Counter(s for p in self.products for s in p['sites'])
        self.assertEqual(self.audit['counts_by_site'],{s:counts[s] for s in SCOPE['sites']})

    def test_scope_status_dates_and_identity(self):
        end=valid_date(self.catalog['meta']['status_date_end'])
        for p in self.products:
            self.assertEqual(p['id'],regno(p['registration_number']))
            self.assertEqual(p['status'],'Active Products')
            self.assertTrue(p['sites']);self.assertTrue(set(p['sites'])<=set(SCOPE['sites']))
            self.assertLessEqual(valid_date(p['status_date']),end)
            self.assertIsInstance(p['source_row'],int)

    def test_exclusions_and_missing_data_disclosed(self):
        excluded={p['registration_number'] for p in self.audit['excluded_records']}
        for p in self.products:
            self.assertNotIn(p['id'],excluded)
            for ai in p['ingredients']:
                self.assertNotIn('deltamethrin',ai['name'].lower())
                self.assertNotIn(ai.get('pc_code'),SCOPE['excluded_pc_codes'])
                self.assertNotIn(ai.get('cas'),SCOPE['excluded_cas'])
            if not p['ingredients']:
                self.assertEqual(p['ingredient_quality'],'missing')
                self.assertIn('cannot be independently confirmed',p['notes'])
            if p['ingredient_quality']=='base-linked':
                self.assertEqual(p['base_registration'],'-'.join(p['id'].split('-')[:2]))
                self.assertIsInstance(p['base_source_row'],int)

    def test_provenance_agrees_between_files(self):
        self.assertEqual(self.catalog['meta']['audit'],self.audit)
        self.assertEqual(self.catalog['meta']['source_snapshot_date'],self.audit['workbook_created_at'][:10])
        self.assertEqual(len(self.audit['sha256']),64)
        self.assertEqual(self.catalog['scope']['sites'],SCOPE['sites'])

if __name__=='__main__':unittest.main()
