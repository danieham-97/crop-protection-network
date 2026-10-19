"""Embed the imported catalog as a self-contained, explicitly dated offline snapshot."""
import argparse,copy,json,pathlib
root=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--catalog',default=str(root/'static/catalog.json'))
p.add_argument('--output',default=str(root/'CPN_Seed_Treatment_Preview.html'))
a=p.parse_args();data=json.loads(pathlib.Path(a.catalog).read_text())
if not data.get('products'):raise ValueError('No imported EPA records to build')
data['mode']='snapshot';data['meta']['automation']='Standalone snapshot; updates require CPN hosting'
source=(root/'static/index.html').read_text()
source=source.replace('const PREVIEW = null;', 'const PREVIEW = '+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+';')
out=pathlib.Path(a.output);out.write_text(source);print(out)
