import csv
import io
import tempfile
from pathlib import Path

from aiohttp.test_utils import AioHTTPTestCase

from cpn.config import Settings
from cpn.normalize import normalize
from cpn.web import STORE, create_app
from test_core import TODAY, row


class WebTests(AioHTTPTestCase):
    async def get_application(self):
        self.temp=tempfile.TemporaryDirectory()
        app=create_app(Settings(data_dir=Path(self.temp.name),demo=False),background=False)
        products=[normalize(row(i),TODAY) for i in range(1205)]
        app[STORE].publish(products, source='Fixture', demo=False)
        return app

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.temp.cleanup()

    async def test_pagination_and_no_total_cap(self):
        r=await self.client.get('/api/products?page=51&page_size=24')
        data=await r.json()
        self.assertEqual(data['total'],1205)
        self.assertEqual(len(data['items']),5)
        self.assertEqual((await self.client.get('/api/products?page=0')).status,400)

    async def test_csv_exports_every_matching_record(self):
        response=await self.client.get('/api/export.csv?crop=Corn')
        rows=list(csv.reader(io.StringIO(await response.text())))
        self.assertEqual(len(rows),1206)
        self.assertIn('12345-1204',rows[-1])

    async def test_compare_two_three_and_reject_invalid(self):
        for ids,expected in [(['12345-1'],400),(['12345-1','12345-2'],200),(['12345-1','12345-2','12345-3'],200),(['12345-1']*2,400),(['12345-1','unknown'],404),(['12345-1','12345-2','12345-3','12345-4'],400)]:
            r=await self.client.get('/api/compare',params=[('id',x) for x in ids])
            self.assertEqual(r.status,expected)

    async def test_conditional_cache_security_and_unknown(self):
        r=await self.client.get('/api/products');await r.read()
        self.assertIn("script-src 'self'",r.headers['Content-Security-Policy'])
        second=await self.client.get('/api/products',headers={'If-None-Match':r.headers['ETag']})
        self.assertEqual(second.status,304)
        self.assertEqual((await self.client.get('/api/products/missing')).status,404)
        self.assertEqual((await self.client.post('/api/products')).status,405)

    async def test_status_and_health(self):
        s=await (await self.client.get('/api/status')).json()
        self.assertEqual(len(s['allowed_sites']),14)
        self.assertTrue(s['stale'])
        health=await (await self.client.get('/healthz')).json()
        self.assertTrue(health['ready'])
