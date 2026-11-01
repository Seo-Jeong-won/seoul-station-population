# 검증 기록

## 확인한 사항

- `analysis.ipynb`의 코드 셀 6개를 같은 Python 환경에서 순서대로 실행. 오류 0개, Plotly 시각화 출력 4개 포함.
- 역×반경 유일성, 반경별 역 수 일치, 인구·가중 점수의 비음수, G≤P, 면적비 범위, 거래 없는 가격의 결측, 반경 확대 시 인구의 단조 증가 확인.
- 강동·남구로·까치산·잠실새내·안국·김포공항의 500m 거래 집계를 별도 Euclidean KD-tree로 대조. 거래 수와 가격 중위값 일치.
- 투영 좌표계에서 만든 500m 원의 면적과 πr²의 오차가 0.02% 미만임을 확인.
- 앱 초기값, 300m·800m 변경, 지도 지표 5종, 역 검색, 신촌 분리, 서울역 표기, 미달 표본 선택, 차트/사례 버튼 선택, 초기화 등 17개 앱 상태·차트 명세 검사 통과.
- 로컬 서버 HTTP 200 및 자산·다운로드 링크 11개 응답 확인.
- 공개 파일에서 원본 입력 스냅샷·개별 거래 주소·인증키 제외 확인.
- 보고서 LaTeX 공식의 역슬래시와 노트북 출력 보존 확인.

## 검증 한계

브라우저 접근 호스트가 제공되지 않았고, Windows Chrome 앱 접근 승인이 시간 초과되어 실제 화면 렌더링을 직접 확인하지 못했습니다. 앱 상태 및 차트 명세 검사는 실물 화면·모바일 레이아웃 검증을 대신하지 않습니다. 화면 검증을 통과했다고 표시하지 않습니다.

검증 결과 JSON은 `results/validation.json`, `results/artifact_validation.json`, `results/web_contract_validation.json`에 있습니다.

## 재실행

```powershell
python analyze.py
python build.py
python execute_notebook.py
python build.py
node verify_web.js
# 별도 터미널에서 먼저 python -m http.server 8003 --directory dist 실행
python verify_artifacts.py
```
