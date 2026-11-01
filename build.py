"""Build the report, executed-notebook template and offline static submission."""
from pathlib import Path
import json
import shutil
import zipfile
import sys

import geopandas as gpd
import nbformat as nbf
import pandas as pd
from plotly.offline import get_plotlyjs
from pyproj import Transformer

HERE=Path(__file__).resolve().parent
DIST=HERE/'dist'
RESULTS=HERE/'results'
sys.stdout.reconfigure(encoding='utf-8')

def number(x): return f'{x:,.0f}'
def rho(x): return f'{x:.3f}'

def report(summary):
    s=summary; c=s['correlations']; counts=s['counts']
    top=s['top_population_quality'][0]; gravity=s['top_gravity'][0]
    data=pd.read_csv(RESULTS/'station_results_500m.csv')
    gangdong=data.loc[data.station.eq('강동')].iloc[0]
    jamsil=data.loc[data.station.eq('잠실새내')].iloc[0]
    table='\n'.join(f"| {i+1} | {r['station']} | {number(r['population'])} | {number(r['density'])} | {number(r['gravity'])} | {number(r['price_median'])} | {r['trade_count']} | {r['observed_area_share']:.1%} |" for i,r in enumerate(s['top_population_quality'][:10]))
    sensitivity='\n'.join(f"| {r['radius_m']}m | {r['top_station']} | {number(r['top_population'])} | {r['sample_size']} | {rho(r['spearman_population_price'])} | {rho(r['common_spearman_population_price'])} |" for r in s['sensitivity'])
    cleaning='\n'.join(f"| {r['step']} | {r['removed']:,} | {r['remaining']:,} |" for r in s['cleaning_log'])
    return rf'''# 어느 역세권에 가장 많은 사람이 살까?

서울 역세권 거주인구와 아파트 매매가격의 관계 · 스마트도시데이터분석 과제 3

## 1. 연구 주제와 질문

서울의 역마다 같은 크기의 반경 500m 생활권을 설정하고, 공개 격자인구로 추정한 거주인구와 같은 생활권에서 거래된 아파트의 ㎡당 가격을 비교한다. 분석 단위는 수업 제공 역사마스터에 포함된 서울 경계 안의 **{counts['stations']}개 역**이다. 수업 자료의 고정 스냅샷으로 분석하며, 현재 운영 중인 역 전체 또는 현재 시세를 대표한다고 가정하지 않는다.

1. 반경 500m 안의 공개값 기반 추정 거주인구가 가장 많은 역은 어디인가?
2. 거주인구가 많은 역세권일수록 아파트 ㎡당 매매가격도 높은가?
3. 단순 인구밀도와 역까지의 거리를 반영한 지표는 같은 공간 패턴을 보이는가?
4. 반경이나 자료 선택 조건을 바꾸면 결과가 얼마나 달라지는가?

역세권은 **역 대표좌표 중심의 직선거리 500m 원**으로 정의한다. 이는 정책상 지정된 역세권이나 실제 도보 500m권을 그대로 재현한 것이 아니다. 서울시 사업별 범위도 다르므로 분석 목적의 조작적 정의임을 명시한다.

## 2. 자료와 전처리

| 자료 | 기준 시점 | 사용 항목 | 직접 사용한 파일 |
| --- | --- | --- | --- |
| SGIS 100m 격자 인구 | 2024년 | to_in_001 총인구 | 2024년_인구_다사_100M.csv |
| 수업 제공 격자 도형 | 2025년 | GRID_CD·도형 | seoul_100m_grid_2025.geojson |
| 서울 행정동 경계 | 2025.06.30 | ADM_CD·도형 | bnd_dong_seoul.shp |
| 서울시 역사마스터 | 수업 제공 고정 CSV, 파일 내 기준일 미기재 | 이름·호선·좌표 | 서울시 역사마스터 정보.csv |
| 서울시 아파트 실거래 | 2026.01.01~09.04 | 금액·면적·취소일·권리구분·좌표 | seoul_apt_price_2026_geocoded.csv |

수도권의 노선별 역 기록 {counts['source_station_line_rows']}개 중 대표좌표가 서울 경계 안인 {counts['seoul_station_line_rows']}개를 추출했다. 괄호 속 부역명을 정리하고 `서울→서울역`, `총신대입구→이수`를 통합했다. 같은 역의 중복 좌표를 제거한 후 서로 다른 노선 좌표의 평균으로 역 대표점을 정했다. 서로 약 715m 떨어진 신촌 2호선·경의중앙선은 별개 역으로 유지했다. 최종 단위는 {counts['stations']}개다. 자치구 표시는 대표점이 속한 행정구역이며, 실제 역세권은 구 경계를 넘을 수 있다.

모든 거리·면적은 미터 단위 좌표계 **EPSG:5179**에서 계산했다. 인구는 총인구 코드만 추출하여 격자 도형과 코드로 1:1 연결했다. 도형 {counts['grid_rows']:,}개 중 {counts['missing_grid_population']:,}개에는 인구값이 연결되지 않는다. 이를 0명으로 확정하거나 주변 인구로 외삽하지 않았다. 공개값이 있는 격자가 원 안에서 차지하는 면적 비율을 별도로 계산했다. SGIS는 격자인구에 비밀보호 처리를 적용하므로 공개값 자체도 정확한 개인 수와 같다고 보지 않는다.

거래 전처리는 다음 순서로 진행했다. 원본 {counts['source_price_rows']:,}행에서 {counts['clean_price_rows']:,}행을 사용했다.

| 전처리 | 제외 행 | 남은 행 |
| --- | ---: | ---: |
{cleaning}

가격 이상치를 임의로 절단하지 않았으며, 대표값으로 중위값을 사용했다. 완전히 같은 행 {counts['retained_duplicate_rows']:,}개는 거래 고유번호가 없어 기본 분석에서 유지했다. 같은 날·층·면적·가격의 실제 복수 거래를 잘못 삭제할 수 있기 때문이다. 반복행을 제거한 가격 집계도 민감도 분석으로 비교했다.

### 분석 표본의 선택

- 인구 순위: 원 면적 중 서울 포함률 95% 이상, 인구 공개값 연결 면적비 80% 이상. **{counts['population_quality_stations']}개 역**.
- 주 인구–가격 비교: 위 조건에 유효 아파트 거래 10건 이상을 추가. **{counts['comparable_stations']}개 역**.
- 500m에서 서울 포함률 미달 {counts['boundary_flagged']}개, 인구 연결 면적비 미달 {counts['population_coverage_flagged']}개이며 제외 사유는 중복될 수 있다. 거래 10건 미만인 역은 {counts['missing_or_few_trades']}개다.

인구 순위를 가격 거래 수로 제한하지 않는다. 지도에서는 조건 미달 역을 회색으로 표시하고 개별 추정값·포괄률은 조회할 수 있도록 했다. **조건 적용으로 자료가 잘 연결되는 주거 지역이 상대적으로 많이 남는 선택 편향**이 있으므로, 주 비교 결과를 서울 모든 역에 일반화하지 않는다.

## 3. 지표 정의와 계산식

공간 단위는 역 s 중심의 원을 서울 경계로 잘라낸 영역이다. 격자 내부 인구가 고르게 분포한다고 가정하고, 원과 겹치는 면적 비율로 인구를 배분한다.

### 지표 1: 인구밀도(Density)

\[
w_{{is}}=\frac{{|C_i\cap B_s\cap Seoul|}}{{|C_i|}},\quad
P_s=\sum_{{i\in O}}p_iw_{{is}},\quad
D_s=\frac{{P_s}}{{A_s}}
\]

- C_i: 원래 100m 격자 도형, B_s: 역세권 원, O: 공개 인구값이 연결된 격자의 집합.
- p_i: 격자 공개 총인구, w_is: 원과 겹친 격자 면적비.
- P_s: 공개값 기반 추정 배후 거주인구(명).
- A_s: 서울 경계 안에 있는 역세권 면적(km²). 산·하천·공원도 면적에서 제외하지 않는다.
- D_s: 명/km². 클수록 같은 면적에 거주인구가 많이 분포한다. 결측 인구를 추정해 채운 밀도는 아니다.

모든 원의 면적이 같으면 인구수와 밀도는 같은 순위를 가지므로 이 둘을 지표 2개로 중복 계산하지 않는다.

### 지표 2: 거리 가중 배후인구(Gravity-based)

\[
G_s=\sum_{{i\in O}}p_iw_{{is}}\exp(-\beta d_{{is}}),\quad
\beta=\frac{{\ln2}}{{250\text{{m}}}}
\]

- d_is: 역 대표점에서 원래 격자 중심까지의 직선거리(m).
- β: 분석자가 설정한 거리 감쇠계수. 250m에서 가중치 0.5, 500m에서 0.25이며 세 반경 비교에서 동일하게 고정했다.
- 단위: 거리 가중 인구(명 상당). 가까이 사는 주민의 기여가 더 크며, 같은 총인구라도 역 주변 배치에 따라 달라진다.
- 역에서 접근 가능한 인구를 기회량으로 보는 중력형 모형의 적용이다. 철도 서비스 수준·열차 혼잡·주민의 모든 역에 대한 접근성을 측정하지 않는다.
- 경계 격자는 면적을 나누지만 거리 가중치는 원래 격자 중심으로 근사한다. 더 정밀한 위치자료가 없는 데 따른 오차가 있다.

보조적으로 G_s/P_s를 거리 가중 집중 비율로 확인했다. 이는 동일 반경 안의 역 근접 거주 분포를 비교하는 데 도움을 준다.

### 가격 비교 변수

각 유효 아파트 거래의 `THING_AMT / ARCH_AREA`를 계산하고 역세권별 중위값을 구했다. 단위는 **만원/㎡**다. 면적 차이를 일부 보정한 거래가격이지만, 준공연도·층·학군·단지 특성을 통제한 가격은 아니다. 거래 수, 고유 지번주소 수, 가격 사분위수, 거래된 주택의 준공연도·면적 중위값도 제공한다.

## 4. 공간·비공간 시각화와 주요 결과

웹페이지에는 인구밀도·거리 가중 배후인구·가격·인구–가격 유형 지도, 거주인구 상위 역 막대그래프, 인구–가격 산점도, 두 지표 산점도, 반경별 상관 비교를 포함했다. 역과 반경을 바꾸면 지도와 차트가 함께 갱신된다. 원이 겹치면 주민과 거래가 복수 역에 들어가므로 **역별 인구를 합쳐 서울 인구로 사용하지 않는다**.

### 4.1 어디에 많이 살고, 어디에 적게 사는가?

자료 조건을 충족한 역 중 **{top['station']}역**이 추정 거주인구 **{number(top['population'])}명**, 인구밀도 **{number(top['density'])}명/km²**로 가장 높다. 남구로·까치산·서울대입구·신림이 뒤를 잇는다. 낮은 쪽에는 안국(약 3,579명), 을지로4가(약 5,910명), 충무로(약 6,874명)가 있다. 단, 낮은 거주인구를 낮은 도시 활동량이나 교통 수요로 해석할 수 없다. 주거 중심성, 업무·상업·문화 기능의 중심성은 서로 다른 현상이기 때문이다. 실제 토지이용 구성과 고용·유동인구를 결합하면 이 차이를 추가로 검증할 수 있다.

| 순위 | 역 | 추정 인구(명) | 밀도(명/km²) | 거리 가중 점수 | 가격(만원/㎡) | 거래 수 | 인구 면적비 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

위 순위는 공개값을 면적 배분한 추정치다. 소수점은 계산 결과일 뿐 실제 인원을 그 정밀도로 안다는 뜻이 아니므로 본문과 지도에서는 반올림해 표시한다.

### 4.2 두 지표의 공간 패턴은 같은가?

인구밀도와 거리 가중 점수의 순위상관은 **{rho(c['density_gravity_spearman'])}**로 매우 높다. 같은 격자인구에서 출발하므로 비슷한 패턴이 나타나지만, 1위는 다르다. 거리 가중 점수에서는 **{gravity['station']}역({number(gravity['gravity'])}명 상당)**이 가장 높다. 남구로역의 G/P는 약 44.1%, 강동역은 약 41.7%다. 따라서 총인구 규모는 강동역이 조금 크지만, 가까운 거리의 인구 기여를 더 반영하면 남구로역이 앞선다. 이 차이는 단순 총량과 근접 분포를 나눠 읽어야 한다는 점을 보여준다.

### 4.3 사람이 많이 사는 곳이 비싼가?

주 비교 표본 **{counts['comparable_stations']}개 역**의 인구–가격 상관계수는 **Spearman ρ={rho(c['population_price_spearman'])}, Pearson r={rho(c['population_price_pearson'])}**다. 인구밀도–가격 순위상관은 {rho(c['density_price_spearman'])}, 거리 가중 배후인구–가격 순위상관은 {rho(c['gravity_price_spearman'])}다. 이 표본에서는 거주인구가 많을수록 가격도 높다는 뚜렷한 단순 관계가 관찰되지 않는다.

예를 들어 강동역의 추정 인구는 {number(gangdong.population)}명, 잠실새내역은 {number(jamsil.population)}명으로 비슷하지만, 아파트 ㎡당 가격은 각각 **{number(gangdong.price_median)}만원, {number(jamsil.price_median)}만원**으로 약 **{jamsil.price_median/gangdong.price_median:.1f}배** 차이 난다. 잠실새내의 거래는 {int(jamsil.trade_count)}건이지만 고유 지번주소는 {int(jamsil.building_count)}곳으로 특정 주택 재고의 영향도 고려해야 한다.

비교 표본의 인구·가격 중위값({number(s['thresholds']['population_median'])}명, {number(s['thresholds']['price_median'])}만원/㎡)을 기준으로 네 유형을 구분했다. 강동·남구로·까치산은 고인구·저가격, 잠실새내·행당·한티는 고인구·고가격에 속한다. ‘고·저’는 표본 안의 상대적 구분으로, 저평가·고평가 또는 투자 매력을 의미하지 않는다.

주거형태·아파트 재고·면적 구성·연식·일자리와 교육 접근 등의 차이가 가격 차이의 설명 후보가 된다. 그러나 이 연구는 해당 변수를 통제하지 않았으므로 각 요인의 인과효과를 확인한 결과는 아니다. 인구는 모든 주거형태를 포함하는 반면 가격은 아파트만을 포함한다는 범위 차이도 있다.

## 5. 민감도 확인

| 반경 | 인구 1위 | 추정 인구(명) | 가격 비교 역 수 | 인구–가격 ρ | 공통 74개 역 ρ |
| --- | --- | ---: | ---: | ---: | ---: |
{sensitivity}

반경을 바꾸면 인구 1위가 남구로→강동→길동으로 바뀐다. ‘가장 많은 인구를 가진 역’은 역세권 범위에 의존한다. 반경마다 조건 충족 표본도 달라지므로 세 반경 공통 {s['sensitivity'][0]['common_sample_size']}개 역만 비교한 결과도 제시했다. 양의 관계는 관찰되지 않지만 관계의 크기는 반경에 민감하다.

- 500m의 인구 연결 면적 기준을 80%에서 90%로 강화: {c['strict_90pct_sample_size']}개 역, ρ={rho(c['strict_90pct_spearman'])}.
- 같은 거래 행을 제거한 가격으로 재계산: {c['deduplicated_sample_size']}개 역, ρ={rho(c['deduplicated_spearman'])}.
- 거래 10건 이상인 모든 역에 대해 인구·경계 포괄률 조건을 해제: ρ={rho(c['all_price_stations_spearman'])}. 불완전한 인구가 포함되므로 참고 결과다.

생활권이 겹치는 역의 관측치는 서로 독립적이지 않다. 따라서 상관계수는 관계를 묘사하는 용도로만 사용하고, 독립 표본을 전제로 한 유의확률을 제시하지 않았다.

## 6. 분석만으로 설명할 수 없는 점

1. **시점 차이와 스냅샷:** 2024년 인구와 2026년 일부 기간 거래를 비교한다. 현재 인구·현재 시세·가격 변화를 뜻하지 않는다. 기준일이 없는 역 CSV 역시 완전한 최신 역 목록으로 단정하지 않는다.
2. **공개 인구와 공간 추정:** 비밀보호 처리, 누락 격자, 격자 내부 균등 분포 가정, 중심점 거리 근사가 있다. 지도에서 인구가 적게 보이는 지역에 실제로 사람이 없다고 결론낼 수 없다.
3. **표본 선택:** 면적 포괄률과 거래 수 조건 때문에 관측이 잘 되는 주거 지역 위주로 남을 수 있다. 결과는 이 표본의 관계다.
4. **집값 대표성:** 전체 주민을 대표하는 인구와 아파트 거래만을 대표하는 가격의 범위가 다르다. 특정 단지 또는 소수 지번의 거래가 대표값을 좌우할 수 있다.
5. **역세권의 형태:** 실제 출입구·도로망·신호·경사·하천 횡단·노선 서비스는 반영하지 않았다. 같은 이름의 환승역을 평균 좌표로 묶는 선택도 결과에 영향을 준다.
6. **거래 자료 식별:** 고유 거래번호가 없고 지오코딩에도 오차가 있을 수 있다. 동일행 반복의 처리에 따른 결과를 별도 제시했다.
7. **원인과 정책 판단:** 아파트 특성과 사회경제적 조건을 통제하지 않았다. 인구 증가가 가격을 올리거나 내린다는 결론, 혼잡도 또는 주택 공급 우선순위는 이 결과만으로 정할 수 없다.

## 7. 재현과 검증

`analyze.py`가 입력 준비부터 공간 집계와 통계, CSV 출력을 수행한다. `analysis.ipynb`에는 실행 결과를 포함했다. `data/input/manifest.json`에 원본 SHA-256과 출처를 기록했다. API 키 없이 동봉된 로컬 입력 스냅샷으로 재실행할 수 있다. 웹에는 역별 집계만 제공한다.

역×반경 키 유일성, 지표 비음수, G≤P, 면적비 0~1, 거래 없는 역의 가격 결측, 반경 확대 시 인구의 단조 증가 등을 검증했다. 결과는 `results/validation.json`에 있다.

## 8. 자료 출처

- [수업 저장소](https://github.com/jslee-gses/code): 원본 노트북·입력 자료. 과제 안내는 `lecture05_Urban_Planning_Index/03_accessibility.ipynb` 마지막 셀.
- [국가데이터처 SGIS 소지역 통계 활용 안내](https://sgis.mods.go.kr/view/pss/dataBook04): 총인구 코드와 격자 연결.
- [SGIS 격자 비밀보호 안내](https://sgis.mods.go.kr/view/map/interactiveMap): 공개 격자값과 참값의 차이.
- [서울시 역사마스터 정보](https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do): 이름·호선·좌표.
- [서울시 부동산 실거래가 정보](https://data.seoul.go.kr/dataList/OA-21275/A/1/datasetView.do): 금액·면적·계약일·취소일 등. 좌표는 수업 자료의 Kakao 지오코딩 결과 사용.
- [서울시 역세권사업 비교 안내](https://chinese.gangbuk.seoul.kr/portal/main/contents.do?menuNo=200808): 정책별 범위와 본 연구의 분석용 반경 구분.

## 9. 과제 요구사항 대응

| 과제 항목 | 충족 내용 |
| --- | --- |
| 연구 주제와 질문 | 1절의 네 가지 질문, 역 단위의 명시적 공간 정의 |
| 지표 2개 이상 | 인구밀도·거리 가중 배후인구의 공식, 변수, 단위, 해석 |
| 자료와 전처리 | 2절의 자료표·행 수 변화·표본 선택 기준 |
| 공간 시각화 1개 이상 | 역별 지표 지도·인구–가격 네 유형 지도 |
| 비공간 시각화 1개 이상 | 순위 막대그래프·산점도·반경 민감도 그래프 |
| 주요 결과와 해석 | 높은/낮은 지역, 지표 패턴, 도시 구조와의 해석, 한계 |
| 웹 발행 | `dist/` 정적 웹페이지를 Cloudflare로 발행하는 구성 |
'''


def make_notebook(summary, text):
    path=HERE/'analysis.ipynb'
    if path.exists() and '--refresh-notebook' not in sys.argv:
        return
    md=nbf.v4.new_markdown_cell; code=nbf.v4.new_code_cell
    cells=[md('# 어느 역세권에 가장 많은 사람이 살까?\n\n서울 역세권 거주인구와 아파트 매매가격의 관계 · 과제 3\n\n**2024년 인구 / 2026.01.01~09.04 아파트 거래 / 기본 반경 500m**\n\n동봉된 `analyze.py`와 `data/input/`을 같은 폴더에 두고 위에서부터 실행하세요. API 키는 사용하지 않습니다.'),
      md('## 1. '+text.split('## 1. ')[1].split('## 2. ')[0]),
      code("from pathlib import Path\nimport json\nimport pandas as pd\nimport geopandas as gpd\nimport plotly.graph_objects as go\nfrom IPython.display import display\nimport analyze as a\n\n# 원본 출처·해시가 보존된 재현용 입력 스냅샷을 준비합니다.\nmanifest = a.prepare_inputs()\ngrid, boundary, raw_stations, raw_prices = a.load_inputs()\ncity = boundary.geometry.union_all()\ndisplay(pd.DataFrame({'자료':['격자 도형','인구 연결 격자','인구 결측 격자','원본 거래'], '행 수':[len(grid),grid.population.notna().sum(),grid.population.isna().sum(),len(raw_prices)]}))"),
      md('## 2. 전처리와 분석 단위\n\n환승역은 별칭 정리 후 중복 좌표를 제거하고 대표점을 평균합니다. 신촌의 두 역은 분리합니다. 취소 거래·권리 거래·좌표 또는 가격 오류를 제외합니다. 동일행 반복은 실제 복수 거래일 수 있어 기본 유지 후 민감도를 확인합니다. 격자 인구의 결측은 0명으로 확정하지 않습니다.'),
      code("stations, seoul_line_rows, districts = a.prepare_stations(raw_stations, boundary)\nprices, cleaning_log = a.prepare_prices(raw_prices, city)\ndisplay(pd.DataFrame(cleaning_log))\nprint(f'분석 단위: {len(stations)}개 역 / 유효 거래: {len(prices):,}행')\ndisplay(stations[['station','lines','district']].head(10))"),
      md('## 3. 지표와 계산 방법\n\n'+text.split('## 3. 지표 정의와 계산식')[1].split('## 4. ')[0]),
      code("# 300m·500m·800m에서 같은 규칙으로 실제 공간 집계를 수행합니다.\nresult, catchments = a.aggregate(grid, stations, prices, city)\na.validate(result)\nsummary = a.summarize(result, manifest, grid, stations, prices, cleaning_log, seoul_line_rows)\nmain = result[result.radius_m.eq(500)].copy()\nvalid = main[main.comparison_eligible].copy()\npopulation_valid = main[main.population_eligible].copy()\nprint('인구 순위 표본:', len(population_valid), '가격 비교 표본:', len(valid))\ndisplay(population_valid.nlargest(15,'population')[['station','population','density','gravity','price_median','trade_count','observed_area_share']].round(2))"),
      md('## 4. 공간 시각화\n\n인구 자료 조건을 충족한 역은 인구밀도로 색칠하고, 조건 미달 역은 회색으로 표시합니다. 배경은 수업 제공 자치구 도형이며 외부 타일·인증키를 쓰지 않습니다. 지도 좌표는 EPSG:5179를 km로 표시한 것입니다.'),
      code("def show_plot(fig):\n    display({'application/vnd.plotly.v1+json': json.loads(fig.to_json())}, raw=True)\n\nfig = go.Figure()\nfor _, district in districts.iterrows():\n    geometries = list(district.geometry.geoms) if district.geometry.geom_type == 'MultiPolygon' else [district.geometry]\n    for polygon in geometries:\n        x, y = polygon.exterior.xy\n        fig.add_trace(go.Scatter(x=[v/1000 for v in x], y=[v/1000 for v in y], mode='lines',fill='toself',fillcolor='#f1f3ed',line=dict(color='#cbd6ca',width=.5),hoverinfo='skip',showlegend=False))\nxy = stations.set_index('station_id').geometry\nfor eligible,color in [(False,'#ccd1cb'),(True,None)]:\n    frame=main[main.population_eligible.eq(eligible)]\n    fig.add_trace(go.Scatter(x=[xy[i].x/1000 for i in frame.station_id],y=[xy[i].y/1000 for i in frame.station_id],text=frame.station,mode='markers',marker=dict(size=7,color=frame.density if eligible else color,colorscale='Teal',showscale=eligible,colorbar=dict(title='名/km²'.replace('名','명'))),hovertemplate='%{text}<extra></extra>',showlegend=False))\nfig.update_layout(title='500m 역세권 인구밀도',height=620,template='plotly_white',xaxis=dict(visible=False),yaxis=dict(visible=False,scaleanchor='x',scaleratio=1))\nshow_plot(fig)"),
      md('## 5. 비공간 시각화: 인구 순위와 인구–가격 관계'),
      code("top=population_valid.nlargest(15,'population').sort_values('population')\nfig=go.Figure(go.Bar(x=top.population,y=top.station,orientation='h',marker_color='#267f72'))\nfig.update_layout(title='500m 추정 거주인구 상위 15개 역',xaxis_title='추정 거주인구 (명)',template='plotly_white',height=550)\nshow_plot(fig)\n\nfig=go.Figure()\ncolors={'고인구·고가격':'#c67845','고인구·저가격':'#177f73','저인구·고가격':'#d5aa7c','저인구·저가격':'#77989d'}\nfor category,group in valid.groupby('quadrant'):\n    fig.add_trace(go.Scatter(x=group.population,y=group.price_median,text=group.station,mode='markers',name=category,marker=dict(color=colors[category],size=9),hovertemplate='%{text}<br>%{x:,.0f}명<br>%{y:,.0f}만원/㎡<extra></extra>'))\nfig.update_layout(title='500m 거주인구와 아파트 가격',xaxis_title='추정 거주인구 (명)',yaxis_title='㎡당 가격 (만원/㎡)',template='plotly_white',height=500)\nshow_plot(fig)\ndisplay(pd.Series(summary['correlations'],name='상관계수 또는 표본 수'))"),
      md('## 6. 두 지표 비교와 반경 민감도'),
      code("fig=go.Figure(go.Scatter(x=population_valid.density,y=population_valid.gravity,text=population_valid.station,mode='markers',marker=dict(color='#267f72'),hovertemplate='%{text}<extra></extra>'))\nfig.update_layout(title='인구밀도와 거리 가중 배후인구',xaxis_title='인구밀도 (명/km²)',yaxis_title='거리 가중 배후인구 (명 상당)',template='plotly_white')\nshow_plot(fig)\ndisplay(pd.DataFrame(summary['sensitivity']).round(4))\nprint('세 반경 공통 표본을 함께 확인해 반경별 표본 구성 차이를 구분합니다.')"),
      md('## 7. 주요 결과와 해석\n\n'+text.split('## 4. 공간·비공간 시각화와 주요 결과')[1].split('## 7. 재현과 검증')[0]),
      md('## 8. 검증·출처\n\n'+text.split('## 7. 재현과 검증')[1])]
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3 (과제 3)','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}})
    nbf.write(nb,path)


def map_data():
    districts=gpd.read_file(RESULTS/'districts.geojson').to_crs(5179)
    shapes=[]
    bounds=districts.total_bounds/1000
    for _,r in districts.iterrows():
        geom=r.geometry.simplify(40,preserve_topology=True)
        parts=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
        x=[];y=[]
        for part in parts:
            if x: x.append(None);y.append(None)
            px,py=part.exterior.xy
            x += [round(v/1000,4) for v in px]; y += [round(v/1000,4) for v in py]
        c=geom.representative_point()
        shapes.append({'name':r.district,'x':x,'y':y,'cx':c.x/1000,'cy':c.y/1000})
    catchments=gpd.read_file(RESULTS/'catchments.geojson').to_crs(5179)
    paths={}
    for _,r in catchments.iterrows():
        geom=r.geometry.simplify(8,preserve_topology=True)
        parts=list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom]
        x=[];y=[]
        for p in parts:
            if p.geom_type!='Polygon':continue
            if x:x.append(None);y.append(None)
            px,py=p.exterior.xy
            x += [round(v/1000,4) for v in px];y += [round(v/1000,4) for v in py]
        paths[f'{r.radius_m}|{r.station_id}']={'x':x,'y':y}
    return {'districts':shapes,'catchments':paths,'bounds':{'x':[float(bounds[0]-1),float(bounds[2]+1)],'y':[float(bounds[1]-1),float(bounds[3]+1)]}}


def main():
    summary=json.loads((RESULTS/'summary.json').read_text(encoding='utf-8'))
    text=report(summary)
    (HERE/'REPORT.md').write_text(text,encoding='utf-8')
    make_notebook(summary,text)
    assets=DIST/'assets'; downloads=DIST/'downloads'
    assets.mkdir(parents=True,exist_ok=True);downloads.mkdir(exist_ok=True)
    shutil.copy2(HERE/'web/index.html',DIST/'index.html')
    for name in ['styles.css','app.js']:shutil.copy2(HERE/'web'/name,assets/name)
    (assets/'plotly.min.js').write_text(get_plotlyjs(),encoding='utf-8')
    stations=json.loads((RESULTS/'stations.json').read_text(encoding='utf-8'))
    transform=Transformer.from_crs(4326,5179,always_xy=True)
    for row in stations:
        x,y=transform.transform(row['lon'],row['lat']);row['x']=x/1000;row['y']=y/1000
    data={'summary':summary,'stations':stations,'map':map_data()}
    (assets/'data.js').write_text('window.ANALYSIS_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';',encoding='utf-8')
    for source in [RESULTS/'station_results.csv',RESULTS/'station_results_500m.csv',HERE/'analysis.ipynb',HERE/'REPORT.md']:
        shutil.copy2(source,downloads/source.name)
    with zipfile.ZipFile(downloads/'analysis-code.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in ['analyze.py','build.py','execute_notebook.py','verify_web.js','verify_artifacts.py','PLAN.md','README.md','requirements.txt','REPORT.md','analysis.ipynb','QA_NOTES.md']:
            z.write(HERE/name,name)
        z.write(HERE/'data/input/manifest.json','SOURCE_MANIFEST.json')
        z.writestr('INPUTS_REQUIRED.txt','공개 코드 묶음에는 거래별·격자별 원본 입력을 포함하지 않습니다. 재실행에는 로컬 프로젝트의 data/input 스냅샷 또는 수업 저장소의 해당 원본 자료가 필요합니다. 역별 집계 CSV는 웹페이지에서 별도 다운로드할 수 있습니다.')
        for name in ['index.html','styles.css','app.js']:
            z.write(HERE/'web'/name,'web/'+name)
    # Full, portable source stays local; public deployment only has aggregates.
    with zipfile.ZipFile(HERE/'assignment3-source.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in ['analyze.py','build.py','execute_notebook.py','verify_web.js','verify_artifacts.py','PLAN.md','README.md','requirements.txt','REPORT.md','analysis.ipynb','wrangler.jsonc','QA_NOTES.md']:
            z.write(HERE/name,name)
        for directory in ['data/input','web']:
            for p in (HERE/directory).rglob('*'):
                if p.is_file():z.write(p,p.relative_to(HERE))
        for name in ['validation.json','artifact_validation.json','web_contract_validation.json']:
            if (RESULTS/name).exists():z.write(RESULTS/name,'results/'+name)
    print(f'Built {DIST}')
    print(f'Notebook exists: {(HERE/"analysis.ipynb").exists()}')
    print(f'Data bundle: {(assets/"data.js").stat().st_size:,} bytes')
    print(f'Local reproducible source: {(HERE/"assignment3-source.zip").stat().st_size:,} bytes')


if __name__=='__main__':main()
