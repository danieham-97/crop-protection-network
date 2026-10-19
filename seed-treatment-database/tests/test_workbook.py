import copy, json, pathlib, sys, tempfile, unittest, zipfile
from unittest.mock import patch
from types import SimpleNamespace
from xml.sax.saxutils import escape
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from appril_workbook import read_workbook, parse_ingredients, selected_sites, excel_date, REQUIRED
from refresh_epa import run, publish_workbook

HEADERS=sorted(REQUIRED|{'ABNS','PESTICIDE_TYPE'})

def column(i):
    s=''
    while i:i,r=divmod(i-1,26);s=chr(65+r)+s
    return s

def fixture(path,records,headers=HEADERS,created='2026-09-21T11:58:19Z',declared_rows=None):
    rows=[dict(zip(headers,headers))]+records
    content=[]
    for rowno,r in enumerate(rows,1):
        cells=''.join(f'<c r="{column(i)}{rowno}" t="inlineStr"><is><t>{escape(str(r.get(h,"")))}</t></is></c>' for i,h in enumerate(headers,1))
        content.append(f'<row r="{rowno}">{cells}</row>')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><workbookPr date1904="false"/><sheets><sheet name="ACTIVE_REGISTRATIONS5_PUBLIC_V" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('docProps/core.xml',f'<properties xmlns:d="http://purl.org/dc/terms/"><d:created>{created}</d:created></properties>')
        z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:R{declared_rows or len(rows)}"/><sheetData>'+''.join(content)+'</sheetData></worksheet>')

def record(**kw):
    return {'REG_NUM':'100-1','REG_TYPE':'Sec3','PRODUCT_NAME':'Test fixture — not a product','COMPANY_NAME':'Fixture','STATUS_GROUP':'Active','STATUS':'Registered','STATUS_DESC':'Active - Registered','STATUS_DT':'45000','AIS':'Metalaxyl (113501/57837-19-1) - (25%), ','SITES':'Wheat (Seed Treatment), ','PEST_CAT':'Fungicide','MAX_LABEL_DT':'45517','PESTICIDE_TYPE':'Conventional Chemical',**kw}

class WorkbookTests(unittest.TestCase):
    def parse(self,records,**kwargs):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'epa.xlsx';fixture(p,records,**kwargs);return read_workbook(p,'2026-10-16')
    def test_active_exact_site_census_and_deltamethrin(self):
        p,a=self.parse([record(),record(REG_NUM='100-2',STATUS_GROUP='Inactive'),record(REG_NUM='100-3',SITES='Wheat (Grain Storage), '),record(REG_NUM='100-4',AIS='Chemical synonym (097805/52918-63-5) - (4.75%), ')])
        self.assertEqual([r['id'] for r in p],['100-1']);self.assertEqual(a['row_count'],4);self.assertEqual(a['active_matching_site_rows'],2);self.assertEqual(len(a['excluded_records']),1)
    def test_edible_soybeans_comma_and_no_group_expansion(self):
        self.assertEqual(selected_sites('Soybeans, Edible (Seed and Pod Vegetable) (Seed Treatment), '),['Soybeans, Edible (Seed and Pod Vegetable) (seed treatment)'])
        self.assertEqual(selected_sites('Corn (Sweet) (Seed Treatment), Small Grains (Hay) (Seed Treatment), '),[])
        self.assertEqual(selected_sites('  WHEAT   (SEED TREATMENT), '),['Wheat (seed treatment)'])
    def test_distributor_base_link_preserves_own_sites_and_identity(self):
        p,a=self.parse([record(SITES='Apples'),record(REG_NUM='100-1-99',REG_TYPE='DP',AIS='',SITES='Soybeans (Seed Treatment), ')])
        self.assertEqual(len(p),1);r=p[0];self.assertEqual(r['id'],'100-1-99');self.assertEqual(r['base_registration'],'100-1');self.assertEqual(r['sites'],['Soybeans (seed treatment)']);self.assertEqual(r['ingredient_quality'],'base-linked');self.assertEqual(r['base_source_row'],2)
    def test_unavailable_formulation_retained_with_visible_uncertainty(self):
        p,a=self.parse([record(REG_NUM='100-8-99',REG_TYPE='DP',AIS='')]);self.assertEqual(len(p),1);self.assertEqual(p[0]['ingredient_quality'],'missing');self.assertIn('exclusion cannot be independently confirmed',p[0]['notes']);self.assertEqual(a['missing_formulation_products'],1)
    def test_base_deltamethrin_excludes_distributor(self):
        p,a=self.parse([record(),record(REG_NUM='100-9',SITES='Apples',AIS='Deltamethrin (097805/52918-63-5) - (1%), '),record(REG_NUM='100-9-99',REG_TYPE='DP',AIS='')]);self.assertEqual(len(p),1);self.assertEqual(a['excluded_records'][0]['registration_number'],'100-9-99')
    def test_missing_percentage_not_zero_or_dropped(self):
        p,a=self.parse([record(AIS='Clothianidin (044309/210880-92-5) - (%), ')]);self.assertIsNone(p[0]['ingredients'][0]['percent']);self.assertEqual(p[0]['ingredient_quality'],'partial');self.assertEqual(a['missing_percent_products'],1)
    def test_numeric_dates_and_source_provenance(self):
        p,a=self.parse([record()]);self.assertEqual(p[0]['status_date'],'2023-03-15');self.assertEqual(p[0]['latest_label_date'],'2024-08-13');self.assertIsNone(p[0]['source_updated']);self.assertIsNone(p[0]['retrieved_at']);self.assertEqual(p[0]['source_snapshot_date'],'2026-09-21');self.assertEqual(excel_date('1',True),'1904-01-02')
    def test_schema_and_incomplete_extent_fail_closed(self):
        for kw in ({'headers':[h for h in HEADERS if h!='STATUS_DT']},{'declared_rows':8}):
            with self.assertRaises(ValueError):self.parse([record()],**kw)
    def test_bad_ingredient_and_duplicate_registration_abort(self):
        for records in ([record(AIS='Unparsed chemical')],[record(),record()]):
            with self.assertRaises(ValueError):self.parse(records)
    def test_creation_date_guard(self):
        with self.assertRaises(ValueError):self.parse([record()],created='2027-01-01T00:00:00Z')
    def test_failed_download_retains_previous_publication(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)/'catalog.json';out.write_text('last valid catalog')
            args=SimpleNamespace(workbook=None,db=str(pathlib.Path(d)/'db.sqlite'),output=str(out))
            with patch('refresh_epa.download_workbook',side_effect=OSError('fixture download failure')):
                self.assertEqual(run(args),1)
            self.assertEqual(out.read_text(),'last valid catalog');self.assertEqual(json.loads(out.with_name('sync-status.json').read_text())['state'],'failed')
    def test_older_workbook_cannot_replace_newer(self):
        p,a=self.parse([record()])
        with tempfile.TemporaryDirectory() as d:
            args=SimpleNamespace(db=str(pathlib.Path(d)/'db'),output=str(pathlib.Path(d)/'catalog.json'))
            publish_workbook(p,a,args);before=pathlib.Path(args.output).read_bytes();a['workbook_created_at']='2026-08-01T00:00:00Z'
            with self.assertRaises(ValueError):publish_workbook(p,a,args)
            self.assertEqual(before,pathlib.Path(args.output).read_bytes())

if __name__=='__main__':unittest.main()
