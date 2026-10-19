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

    def test_product_hazard_counts_and_no_distributor_label_guess(self):
        counts=collections.Counter(p['safety']['signal_word'] or 'NOT_SUPPLIED' for p in self.products)
        self.assertEqual(dict(counts),self.audit['signal_word_counts'])
        self.assertEqual(sum(p['safety']['restricted_use'] is True for p in self.products),self.audit['restricted_use_products'])
        for p in self.products:
            s=p['safety']
            self.assertIn(s['signal_word_state'],('reported','reported-none','missing','unrecognized'))
            if s['signal_word']=='NONE':self.assertEqual(s['signal_word_state'],'reported-none')
            if p['record_type']=='DP':self.assertIsNone(s['label_url'])
            if s['label_url']:
                filename=s['label_url'].rsplit('/',1)[1]
                self.assertEqual('-'.join(str(int(x)) for x in filename.split('-')[:2]),p['id'])
                self.assertLessEqual(valid_date(s['label_date']),self.catalog['meta']['status_date_end'])

    def test_matrix_source_fields_and_label_specs(self):
        from comparison_evidence import load_label_specs
        self.assertEqual(self.catalog['label_specs'],load_label_specs())
        self.assertEqual(sum(bool(p['first_registration_date']) for p in self.products),self.audit['first_registration_dates'])
        self.assertEqual(sum(bool(p['target_pests_raw']) for p in self.products),self.audit['product_pest_indexes'])
        for r in self.catalog['label_specs']['records']:
            # Weekly EPA data may retire a product or supersede a reviewed label.
            # The UI must mark the extract stale; that is not an invalid import.
            self.assertEqual(r['registration_number'],regno(r['registration_number']))
            self.assertTrue(r['composition']);self.assertTrue(r['source_url'].startswith('https://www3.epa.gov/'))

    def test_classification_sources_and_published_guide(self):
        refs=json.loads((ROOT/'data/ingredients.json').read_text())
        self.assertEqual(self.catalog['ingredient_reference'],refs)
        self.assertEqual(self.catalog['education'],json.loads((ROOT/'data/education.json').read_text()))
        for key,r in refs.items():
            self.assertEqual(key,' '.join(key.lower().split()))
            scheme='FRAC' if r.get('frac_code') else 'IRAC'
            self.assertEqual(r['group'],scheme+' '+r[scheme.lower()+'_code'])
            self.assertIn('www.frac.info' if scheme=='FRAC' else 'irac-online.org',r['source_url'])
            valid_date(r['reviewed_on'])
        # Distinct schemes and historically changed classifications must stay explicit.
        self.assertEqual(refs['metalaxyl-m']['frac_code'],'4')
        self.assertIn('Mefenoxam',refs['metalaxyl-m']['synonyms'])
        self.assertEqual(refs['extract of reynoutria sachalinensis']['frac_code'],'P05')
        self.assertEqual(refs['picarbutrazox']['frac_code'],'U17')
        self.assertEqual(refs['thiamethoxam']['irac_code'],'4A')

if __name__=='__main__':unittest.main()

