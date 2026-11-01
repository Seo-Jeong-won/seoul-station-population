# 어느 역세권에 가장 많은 사람이 살까?

스마트도시데이터분석 과제 3. 서울 역 중심 반경 500m의 2024년 공개 격자 거주인구를 면적 가중으로 추정하고, 2026년 아파트 ㎡당 거래가격 중위값과 비교합니다. 인구밀도와 거리 가중 배후인구가 두 분석 지표입니다.

## 파일과 실행

- `PLAN.md`: 과제 항목에 대응하는 분석 설계.
- `analysis.ipynb`: 실행 결과를 포함한 제출용 분석 노트북.
- `analyze.py`: 자료 준비, 전처리, 공간 집계, 통계, 검증.
- `build.py`: 보고서·노트북·웹페이지·제출 파일 생성.
- `REPORT.md`: 실제 계산 결과를 근거로 작성한 해석.
- `data/input/`: 수업 원본에서 추출한 재현용 입력 스냅샷과 SHA-256 출처 기록. 인증키 불필요.
- `results/`: 역별 결과, 상관계수, 반경 민감도, 검증 결과.
- `dist/`: Cloudflare에 배포할 완성된 정적 웹페이지.

```powershell
python -m pip install -r requirements.txt
python analyze.py
python build.py
python -m http.server 8003 --directory dist
```

브라우저에서 `http://localhost:8003`을 엽니다. 지도와 차트는 동봉한 Plotly.js 및 데이터만 사용하므로 외부 지도 API 키나 타일 서비스가 필요 없습니다.

## 범위와 해석

가격은 2026년 1월 1일~9월 4일의 수업 제공 스냅샷이며 현재 시세나 연간 전체 거래가 아닙니다. 인구는 2024년 자료입니다. 공개 인구가 연결되지 않은 격자는 무인 지역으로 확정하지 않습니다. 반경은 실제 도보거리나 정책상 지정 구역과 다른 분석용 직선거리입니다. 겹치는 역세권의 주민·거래는 각 역에 중복 포함될 수 있습니다.

주 비교는 서울 포함 면적비 95%·인구 공개값 연결 면적비 80%·거래 10건 조건을 적용합니다. 자료 조건이 좋은 주거 지역이 더 많이 포함될 수 있어 결과를 서울 모든 역에 일반화하지 않습니다. 유의확률 및 인과효과를 주장하지 않습니다.

## 출처

- 수업 자료: https://github.com/jslee-gses/code
- SGIS 소지역 통계: https://sgis.mods.go.kr/view/pss/dataBook04
- SGIS 격자 비밀보호 안내: https://sgis.mods.go.kr/view/map/interactiveMap
- 서울시 역사마스터 정보: https://data.seoul.go.kr/dataList/OA-21232/S/1/datasetView.do
- 서울시 부동산 실거래가 정보: https://data.seoul.go.kr/dataList/OA-21275/A/1/datasetView.do

웹에는 역별 집계만 공개하고 개별 거래 주소·원본 입력·인증키는 포함하지 않습니다. 실행용 입력 스냅샷은 로컬 프로젝트에 있습니다.

공개 GitHub 저장소에는 원본 입력 스냅샷과 로컬 백업 ZIP을 제외하고, 분석 코드·실행 결과 노트북·역별 집계·정적 웹페이지를 제공합니다. 웹페이지는 추가 데이터 수집 없이 `dist/`에서 확인할 수 있습니다. 인구·거래 집계를 처음부터 재계산하려면 로컬 프로젝트의 `data/input/` 또는 위 수업 원본 자료가 필요합니다. 원본 파일의 출처와 SHA-256은 `data/input/manifest.json`에 있습니다.
