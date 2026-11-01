from pathlib import Path
from html.parser import HTMLParser
import json
import zipfile
import urllib.request
import numpy as np
import pandas as pd
import nbformat
from scipy.spatial import cKDTree
import analyze as a

HERE=Path(__file__).resolve().parent
DIST=HERE/'dist'
checks=[]

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ['src','href'] and value and not value.startswith(('#','http','mailto:')):
                self.links.append(value)

parser=Links();parser.feed((DIST/'index.html').read_text(encoding='utf-8'))
for link in parser.links:
    assert (DIST/link).is_file(),link
    with urllib.request.urlopen('http://127.0.0.1:8003/'+link,timeout=15) as r:
        assert r.status==200,link
checks.append(f'All {len(parser.links)} local asset/download links exist and return HTTP 200')
notebook=nbformat.read(HERE/'analysis.ipynb',as_version=4)
nbformat.validate(notebook)
codes=[c for c in notebook.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in codes)
assert not any(o.output_type=='error' for c in codes for o in c.outputs)
assert sum(o.output_type=='display_data' and 'application/vnd.plotly.v1+json' in o.get('data',{}) for c in codes for o in c.outputs)>=4
checks.append(f'All {len(codes)} notebook code cells executed without errors; 4 interactive plot outputs')
report=(HERE/'REPORT.md').read_text(encoding='utf-8')
assert not any(ord(c)<32 and c not in '\n\r\t' for c in report)
assert r'\beta' in report and r'\frac' in report
checks.append('Report equations preserve LaTeX backslashes and contain no unexpected control characters')
for file in DIST.rglob('*'):
    if file.is_file():assert file.suffix not in ['.env','.enc','.toml']
with zipfile.ZipFile(DIST/'downloads/analysis-code.zip') as z:
    assert not any(name.startswith(('data/input/','.env','.cache/')) for name in z.namelist())
checks.append('Public output contains aggregates/code only; source input snapshots are excluded')
grid,boundary,raw_stations,raw_prices=a.load_inputs()
stations,_,_=a.prepare_stations(raw_stations,boundary)
prices,_=a.prepare_prices(raw_prices,boundary.geometry.union_all())
results=pd.read_csv(HERE/'results/station_results_500m.csv')
tree=cKDTree(np.column_stack([prices.geometry.x,prices.geometry.y]))
for name in ['강동','남구로','까치산','잠실새내','안국','김포공항']:
    station=stations.loc[stations.station.eq(name)].iloc[0]
    direct_ids=tree.query_ball_point([station.geometry.x,station.geometry.y],500)
    row=results.loc[results.station.eq(name)].iloc[0]
    assert len(direct_ids)==row.trade_count,(name,len(direct_ids),row.trade_count)
    if direct_ids:
        median=np.median(prices.iloc[direct_ids].unit_price)
        assert np.isclose(median,row.price_median,atol=1e-6),(name,median,row.price_median)
checks.append('Independent Euclidean KD-tree catchment counts and medians match polygon aggregation at 6 stations')
area=stations.geometry.iloc[0].buffer(500,quad_segs=64).area
assert abs(area/(np.pi*500**2)-1)<.0002
checks.append('Projected 500m polygon area differs from the analytic circle by less than 0.02%')
(HERE/'results/artifact_validation.json').write_text(json.dumps({'passed':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print('\n'.join(checks))
