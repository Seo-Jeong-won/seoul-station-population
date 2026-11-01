"""Station-centred catchments: reproducible statistics, with no API keys.

First run reads the course files and stores minimal, compressed input snapshots.
Later runs use the snapshots, so the project can be moved to another computer.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from shapely import from_wkb, to_wkb

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
INPUT = HERE / 'data' / 'input'
OUTPUT = HERE / 'results'
CRS = 5179
RADII = (300, 500, 800)
HALF_DISTANCE = 250.0
MIN_TRADES = 10
MIN_CITY_SHARE = .95
MIN_OBSERVED_SHARE = .80
DISTRICTS = dict(zip(
    [f'{11010+i*10:05d}' for i in range(25)],
    ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구',
     '노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구',
     '관악구','서초구','강남구','송파구','강동구']))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False,
                               default=lambda x: x.item() if hasattr(x, 'item') else str(x)), encoding='utf-8')


def records(frame):
    return json.loads(frame.to_json(orient='records', force_ascii=False, double_precision=6))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_inputs():
    """Preserve missing population as missing and keep a record of source hashes."""
    INPUT.mkdir(parents=True, exist_ok=True)
    snapshots = ['grid.csv.gz', 'stations.csv.gz', 'prices.csv.gz', 'boundary.geojson', 'manifest.json']
    if all((INPUT / name).exists() for name in snapshots):
        return json.loads((INPUT / 'manifest.json').read_text(encoding='utf-8'))
    workspace = HERE.parent
    course = workspace.parent / 'code'
    if not course.exists():
        course = workspace
    urban = course / 'lecture05_Urban_Planning_Index'
    sources = {
        'population': urban / 'grid/2024년_인구_다사_100M.csv',
        'grid': urban / 'grid/seoul_100m_grid_2025.geojson',
        'prices': course / 'lecture04_spatial_data_analysis/data/seoul_apt_price_2026_geocoded.csv',
        'stations': workspace / 'lecture05_Urban_Planning_Index/data/서울시 역사마스터 정보.csv',
        'boundary': urban / 'shp/bnd_dong_seoul.shp',
    }
    pop = pd.read_csv(sources['population'], encoding='cp949', header=None,
                      names=['year','grid_id','stat_code','population'], dtype={'grid_id':str})
    total = pop.loc[pop.stat_code.eq('to_in_001'), ['grid_id','population']].copy()
    assert total.grid_id.is_unique and total.population.ge(0).all()
    grid = gpd.read_file(sources['grid']).to_crs(CRS).rename(columns={'GRID_CD':'grid_id'})
    grid = grid.merge(total, how='left', on='grid_id', validate='one_to_one')
    table = pd.DataFrame(grid.drop(columns='geometry'))
    table['geometry_wkb'] = to_wkb(grid.geometry.to_numpy(), hex=True)
    table.to_csv(INPUT/'grid.csv.gz', index=False, compression='gzip')
    boundary = gpd.read_file(sources['boundary']).to_crs(CRS)
    boundary['district'] = boundary.ADM_CD.astype(str).str[:5].map(DISTRICTS)
    assert boundary.district.notna().all()
    boundary.to_crs(4326).to_file(INPUT/'boundary.geojson', driver='GeoJSON')
    stations = pd.read_csv(sources['stations'], encoding='cp949')
    stations.to_csv(INPUT/'stations.csv.gz', index=False, compression='gzip')
    prices = pd.read_csv(sources['prices'])
    # There is no unique transaction identifier: identical rows are retained in
    # the main analysis, then removed in a separately reported sensitivity check.
    prices['duplicate_row'] = prices.duplicated()
    keep = ['CGG_NM','STDG_NM','MNO','SNO','BLDG_NM','CTRT_DAY','THING_AMT','ARCH_AREA','FLR',
            'RGHT_SE','RTRCN_DAY','ARCH_YR','BLDG_USG','LAT','LON','duplicate_row']
    prices[keep].to_csv(INPUT/'prices.csv.gz', index=False, compression='gzip')
    manifest = {
        'prepared_at_seoul':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds'),
        'source_files':{k:{'filename':p.name,'sha256':digest(p)} for k,p in sources.items()},
        'source_urls':{
            'course':'https://github.com/jslee-gses/code',
            'population':'https://sgis.mods.go.kr/view/pss/dataBook04',
            'privacy':'https://sgis.mods.go.kr/view/map/interactiveMap',
            'stations':'https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do',
            'prices':'https://data.seoul.go.kr/dataList/OA-21275/A/1/datasetView.do',
            'catchment_reference':'https://chinese.gangbuk.seoul.kr/portal/main/contents.do?menuNo=200808',
        },
        'population_year':2024,'grid_geometry_year':2025,
        'population_code':'to_in_001','source_grid_rows':len(grid),
        'matched_grid_rows':int(grid.population.notna().sum()),
        'unmatched_grid_rows':int(grid.population.isna().sum()),
        'source_station_line_rows':len(stations),'source_price_rows':len(prices),
        'exact_duplicate_price_rows':int(prices.duplicate_row.sum()),
        'price_start':prices.CTRT_DAY.min(),'price_end':prices.CTRT_DAY.max(),
        'station_snapshot_note':'수업 제공 CSV의 고정 스냅샷. 파일 내부에 기준일 정보 없음.',
    }
    # Sidecar files are essential parts of the shapefile source as well.
    manifest['boundary_sidecars'] = {p.name:digest(p) for p in sources['boundary'].parent.glob('bnd_dong_seoul.*')}
    save_json(INPUT/'manifest.json',manifest)
    return manifest


def load_inputs():
    grid = pd.read_csv(INPUT/'grid.csv.gz', dtype={'grid_id':str})
    grid = gpd.GeoDataFrame(grid.drop(columns='geometry_wkb'),
        geometry=from_wkb(grid.geometry_wkb.to_numpy()), crs=CRS)
    boundary = gpd.read_file(INPUT/'boundary.geojson').to_crs(CRS)
    return grid, boundary, pd.read_csv(INPUT/'stations.csv.gz'), pd.read_csv(INPUT/'prices.csv.gz')


def prepare_stations(raw, boundary):
    stations = gpd.GeoDataFrame(raw.copy(),
        geometry=gpd.points_from_xy(raw['경도'],raw['위도']),crs=4326).to_crs(CRS)
    city = boundary.geometry.union_all()
    stations = stations.loc[stations.intersects(city)].copy()
    stations['base_name'] = stations['역사명'].str.replace(r'\([^)]*\)', '', regex=True).str.strip()
    stations['base_name'] = stations.base_name.replace({'서울':'서울역','총신대입구':'이수'})
    # These two stations share a name but are approximately 715 m apart and
    # are not an interchange. All other same-name lines use one mean centre.
    stations['station'] = stations.base_name
    sel = stations.base_name.eq('신촌')
    stations.loc[sel,'station'] = stations.loc[sel,'base_name']+' · '+stations.loc[sel,'호선']
    rows=[]
    for name, group in stations.groupby('station',sort=True):
        coords = group.drop_duplicates(['위도','경도']).geometry
        centre = coords.union_all().centroid
        rows.append({'station':name,'lines':' · '.join(sorted(group['호선'].unique())),
                     'line_rows':len(group),'geometry':centre,
                     'max_line_offset_m':max(centre.distance(x) for x in coords)})
    result = gpd.GeoDataFrame(rows,geometry='geometry',crs=CRS)
    result.insert(0,'station_id',[f'S{i:03d}' for i in range(1,len(result)+1)])
    district_boundaries=boundary[['district','geometry']].dissolve(by='district').reset_index()
    located = gpd.sjoin(result,district_boundaries,how='left',predicate='intersects')
    located = located.drop_duplicates('station_id').drop(columns='index_right')
    if located.district.isna().any():
        nearest = gpd.sjoin_nearest(located.loc[located.district.isna()].drop(columns='district'),
                                    district_boundaries,how='left')
        for i,row in nearest.drop_duplicates('station_id').iterrows():
            located.loc[located.station_id.eq(row.station_id),'district']=row.district
    ll=located.to_crs(4326)
    located['lon']=ll.geometry.x.to_numpy(); located['lat']=ll.geometry.y.to_numpy()
    assert located.station_id.is_unique and located.district.notna().all()
    return located.reset_index(drop=True), len(stations), district_boundaries


def prepare_prices(raw, city):
    prices=raw.copy()
    for col in ['THING_AMT','ARCH_AREA','LAT','LON','ARCH_YR']:
        prices[col]=pd.to_numeric(prices[col],errors='coerce')
    prices['CTRT_DAY']=pd.to_datetime(prices.CTRT_DAY, errors='coerce')
    log=[]
    def retain(mask, reason):
        nonlocal prices
        old=len(prices); prices=prices.loc[mask].copy()
        log.append({'step':reason,'removed':old-len(prices),'remaining':len(prices)})
    retain(prices.RTRCN_DAY.isna(), '취소일이 기재된 거래 제외')
    retain(prices.RGHT_SE.isna(), '분양권·입주권 제외')
    retain(prices.BLDG_USG.eq('아파트'), '아파트 이외 주택유형 제외')
    retain(prices.CTRT_DAY.dt.year.eq(2026), '2026년 계약일 확인')
    retain(prices.THING_AMT.gt(0)&prices.ARCH_AREA.gt(0)&prices[['LAT','LON']].notna().all(axis=1),
           '가격·면적·좌표 유효성 확인')
    prices=gpd.GeoDataFrame(prices,geometry=gpd.points_from_xy(prices.LON,prices.LAT),crs=4326).to_crs(CRS)
    retain(prices.intersects(city), '서울 경계 밖 지오코딩 결과 제외')
    prices['unit_price']=prices.THING_AMT/prices.ARCH_AREA
    prices['building_id']=prices.CGG_NM.astype(str)+'|'+prices.STDG_NM.astype(str)+'|'+prices.MNO.astype(str)+'|'+prices.SNO.astype(str)
    prices=prices.reset_index(drop=True)
    assert prices.unit_price.gt(0).all()
    return prices,log


def correlation(frame, x, y, method='spearman'):
    pair=frame[[x,y]].dropna()
    if len(pair)<3 or pair[x].nunique()<2 or pair[y].nunique()<2:
        return None
    function=spearmanr if method=='spearman' else pearsonr
    return float(function(pair[x],pair[y]).statistic)


def aggregate(grid, stations, prices, city):
    grid_area=grid.geometry.area.to_numpy()
    assert grid_area.min()>0 and grid.grid_id.is_unique
    centres=grid.geometry.centroid
    output=[]; geometry_rows=[]
    for radius in RADII:
        print(f'Aggregating {radius} m / {len(stations)} stations...',flush=True)
        for _,station in stations.iterrows():
            circle=station.geometry.buffer(radius,quad_segs=64)
            region=circle.intersection(city)
            ids=grid.sindex.query(region,predicate='intersects')
            pieces=grid.geometry.iloc[ids].intersection(region)
            areas=pieces.area.to_numpy()
            population=grid.population.iloc[ids].to_numpy()
            known=np.isfinite(population)
            weights=areas[known]/grid_area[ids][known]
            allocated=population[known]*weights
            distances=centres.iloc[ids[known]].distance(station.geometry).to_numpy()
            pop=float(allocated.sum()) if known.any() else np.nan
            gravity=float(np.sum(allocated*np.exp(-np.log(2)/HALF_DISTANCE*distances))) if known.any() else np.nan
            observed_share=min(1.,float(areas[known].sum()/region.area))
            trade_ids=prices.sindex.query(region,predicate='intersects')
            trades=prices.iloc[trade_ids]
            dedup=trades.loc[~trades.duplicate_row]
            built=trades.ARCH_YR.where(trades.ARCH_YR.between(1800,2026))
            row={k:station[k] for k in ['station_id','station','district','lines','lat','lon','line_rows','max_line_offset_m']}
            row.update(radius_m=radius,area_km2=region.area/1e6,
                       city_share=region.area/circle.area,observed_area_share=observed_share,
                       population=pop,density=pop/(region.area/1e6),gravity=gravity,
                       gravity_share=gravity/pop if pop>0 else np.nan,
                       trade_count=len(trades),building_count=int(trades.building_id.nunique()),
                       price_median=float(trades.unit_price.median()) if len(trades) else np.nan,
                       price_q25=float(trades.unit_price.quantile(.25)) if len(trades) else np.nan,
                       price_q75=float(trades.unit_price.quantile(.75)) if len(trades) else np.nan,
                       building_year_median=float(built.median()) if built.notna().any() else np.nan,
                       area_median=float(trades.ARCH_AREA.median()) if len(trades) else np.nan,
                       dedup_trade_count=len(dedup),
                       dedup_price_median=float(dedup.unit_price.median()) if len(dedup) else np.nan)
            row['population_eligible']=bool(row['city_share']>=MIN_CITY_SHARE and observed_share>=MIN_OBSERVED_SHARE and np.isfinite(pop))
            row['comparison_eligible']=bool(row['population_eligible'] and len(trades)>=MIN_TRADES)
            output.append(row)
            geometry_rows.append({'station_id':station.station_id,'radius_m':radius,'geometry':region})
    result=pd.DataFrame(output)
    for radius in RADII:
        sel=result.radius_m.eq(radius)
        comparable=result.loc[sel & result.comparison_eligible]
        pop_mid=comparable.population.median(); price_mid=comparable.price_median.median()
        result.loc[sel,'quadrant']='자료 조건 미충족'
        for idx,row in comparable.iterrows():
            result.loc[idx,'quadrant']=('고인구' if row.population>=pop_mid else '저인구')+'·'+('고가격' if row.price_median>=price_mid else '저가격')
        result.loc[sel,'population_rank']=result.loc[sel,'population'].rank(ascending=False,method='min')
        result.loc[sel,'gravity_rank']=result.loc[sel,'gravity'].rank(ascending=False,method='min')
    geom=gpd.GeoDataFrame(geometry_rows,geometry='geometry',crs=CRS)
    return result,geom


def summarize(result,manifest,grid,stations,prices,cleaning_log,seoul_line_rows):
    main=result.loc[result.radius_m.eq(500)].copy()
    comparable=main.loc[main.comparison_eligible].copy()
    pop_valid=main.loc[main.population_eligible]
    common_ids=set.intersection(*[set(result.loc[result.radius_m.eq(r)&result.comparison_eligible,'station_id']) for r in RADII])
    sensitivity=[]
    for radius in RADII:
        current=result.loc[result.radius_m.eq(radius)]
        valid=current.loc[current.comparison_eligible]
        common=current.loc[current.station_id.isin(common_ids)]
        top=current.loc[current.population_eligible].nlargest(1,'population').iloc[0]
        sensitivity.append({'radius_m':radius,'sample_size':len(valid),'top_station':top.station,
            'top_population':float(top.population),
            'spearman_population_price':correlation(valid,'population','price_median'),
            'pearson_population_price':correlation(valid,'population','price_median','pearson'),
            'spearman_gravity_price':correlation(valid,'gravity','price_median'),
            'common_sample_size':len(common),
            'common_spearman_population_price':correlation(common,'population','price_median')})
    columns=['station','district','population','density','gravity','gravity_share','price_median','trade_count',
             'building_count','observed_area_share','city_share','building_year_median','area_median','quadrant']
    all_with_prices=main.loc[main.trade_count.ge(MIN_TRADES)]
    dedup_comp=comparable.loc[comparable.dedup_trade_count.ge(MIN_TRADES)]
    strict=main.loc[main.city_share.ge(.95)&main.observed_area_share.ge(.9)&main.trade_count.ge(MIN_TRADES)]
    disagreements=pop_valid.copy()
    disagreements['rank_change']=disagreements.population_rank-disagreements.gravity_rank
    by_district=[]
    for district,group in comparable.groupby('district'):
        by_district.append({'district':district,'n':len(group),
            'spearman_population_price':correlation(group,'population','price_median')})
    return {
        'title':'어느 역세권에 가장 많은 사람이 살까?',
        'subtitle':'서울 역세권 거주인구와 아파트 매매가격의 관계',
        'generated_at_seoul':datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds'),
        'config':{'radii_m':list(RADII),'main_radius_m':500,'half_distance_m':HALF_DISTANCE,
                  'min_trades':MIN_TRADES,'min_city_share':MIN_CITY_SHARE,'min_observed_area_share':MIN_OBSERVED_SHARE,
                  'metric_crs':'EPSG:5179','population_year':2024,'price_start':manifest['price_start'],
                  'price_end':manifest['price_end'],'same_name_exception':'신촌은 2호선·경의중앙선으로 분리',
                  'aliases':{'서울':'서울역','총신대입구':'이수'}},
        'counts':{'stations':len(stations),'source_station_line_rows':manifest['source_station_line_rows'],
                  'seoul_station_line_rows':seoul_line_rows,'population_quality_stations':len(pop_valid),
                  'comparable_stations':len(comparable),'missing_or_few_trades':int(main.trade_count.lt(MIN_TRADES).sum()),
                  'boundary_flagged':int(main.city_share.lt(MIN_CITY_SHARE).sum()),
                  'population_coverage_flagged':int(main.observed_area_share.lt(MIN_OBSERVED_SHARE).sum()),
                  'source_price_rows':manifest['source_price_rows'],'clean_price_rows':len(prices),
                  'retained_duplicate_rows':int(prices.duplicate_row.sum()),'grid_rows':len(grid),
                  'missing_grid_population':int(grid.population.isna().sum())},
        'correlations':{'population_price_spearman':correlation(comparable,'population','price_median'),
                        'population_price_pearson':correlation(comparable,'population','price_median','pearson'),
                        'density_price_spearman':correlation(comparable,'density','price_median'),
                        'gravity_price_spearman':correlation(comparable,'gravity','price_median'),
                        'density_gravity_spearman':correlation(pop_valid,'density','gravity'),
                        'all_price_stations_spearman':correlation(all_with_prices,'population','price_median'),
                        'strict_90pct_sample_size':len(strict),
                        'strict_90pct_spearman':correlation(strict,'population','price_median'),
                        'deduplicated_sample_size':len(dedup_comp),
                        'deduplicated_spearman':correlation(dedup_comp,'population','dedup_price_median')},
        'thresholds':{'population_median':float(comparable.population.median()),'price_median':float(comparable.price_median.median())},
        'top_population_all':records(main.nlargest(20,'population')[columns]),
        'top_population_quality':records(pop_valid.nlargest(20,'population')[columns]),
        'lowest_population_quality':records(pop_valid.nsmallest(10,'population')[columns]),
        'lowest_population_all':records(main.nsmallest(10,'population')[columns]),
        'top_gravity':records(pop_valid.nlargest(10,'gravity')[columns]),
        'highest_prices':records(comparable.nlargest(10,'price_median')[columns]),
        'quadrant_counts':comparable.quadrant.value_counts().to_dict(),
        'quadrant_examples':{q:records(g.nlargest(3,'population')[columns]) for q,g in comparable.groupby('quadrant')},
        'rank_changes':records(disagreements.reindex(disagreements.rank_change.abs().sort_values(ascending=False).index).head(10)[columns+['rank_change']]),
        'sensitivity':sensitivity,'district_correlations':by_district,
        'cleaning_log':cleaning_log,'sources':manifest['source_urls'],
    }


def validate(result):
    assert result[['station_id','radius_m']].duplicated().sum()==0
    assert result.groupby('radius_m').size().nunique()==1
    assert result.population.dropna().ge(0).all()
    assert result.gravity.dropna().ge(0).all()
    observed=result.loc[result.population.notna()]
    assert (observed.gravity<=observed.population+1e-6).all()
    assert result.observed_area_share.between(0,1).all()
    assert result.city_share.between(0,1.000001).all()
    assert result.price_median.dropna().gt(0).all()
    assert result.loc[result.trade_count.eq(0),'price_median'].isna().all()
    wide=result.pivot(index='station_id',columns='radius_m',values='population')
    for small,large in [(300,500),(500,800)]:
        pair=wide[[small,large]].dropna()
        assert (pair[large]+1e-6>=pair[small]).all()
    assert np.isfinite(result.loc[result.comparison_eligible,'price_median']).all()


def main():
    OUTPUT.mkdir(exist_ok=True)
    manifest=prepare_inputs()
    grid,boundary,raw_stations,raw_prices=load_inputs()
    city=boundary.geometry.union_all()
    stations,seoul_line_rows,districts=prepare_stations(raw_stations,boundary)
    prices,log=prepare_prices(raw_prices,city)
    result,geometry=aggregate(grid,stations,prices,city)
    validate(result)
    summary=summarize(result,manifest,grid,stations,prices,log,seoul_line_rows)
    result.to_csv(OUTPUT/'station_results.csv',index=False,encoding='utf-8-sig',float_format='%.8f')
    result.loc[result.radius_m.eq(500)].to_csv(OUTPUT/'station_results_500m.csv',index=False,encoding='utf-8-sig',float_format='%.8f')
    save_json(OUTPUT/'summary.json',summary)
    save_json(OUTPUT/'stations.json',records(result))
    # The public web output contains station aggregates only, never addresses,
    # credentials, or transaction-level source data.
    geometry=geometry.merge(result[['station_id','radius_m','station']],on=['station_id','radius_m'],validate='one_to_one')
    geometry.to_crs(4326).to_file(OUTPUT/'catchments.geojson',driver='GeoJSON')
    districts.to_crs(4326).to_file(OUTPUT/'districts.geojson',driver='GeoJSON')
    save_json(OUTPUT/'validation.json',{'passed':True,'checks':[
        '역×반경 키 유일성','반경별 역 수 일치','인구·중력형 점수 비음수','중력형 점수≤배후인구',
        '자료 포괄률 0~1','유효 가격 양수','거래 0건의 가격은 결측','반경 확대 시 배후인구 단조 증가',
        '주 비교 표본 가격의 유효성']})
    print(json.dumps({'counts':summary['counts'],'correlations':summary['correlations'],
                      'top5':summary['top_population_quality'][:5],'sensitivity':summary['sensitivity']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
