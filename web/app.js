'use strict';
(() => {
  const {summary:S,stations:ALL,map:M}=window.ANALYSIS_DATA;
  const $=id=>document.getElementById(id);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=(n,d=0)=>Number.isFinite(n)?n.toLocaleString('ko-KR',{maximumFractionDigits:d,minimumFractionDigits:d}):'자료 없음';
  const rho=n=>Number.isFinite(n)?n.toFixed(3).replace('-','−'):'계산 불가';
  const pct=n=>fmt(n*100,1)+'%';
  const stationLabel=name=>name.endsWith('역')?name:name+'역';
  const colors={'고인구·고가격':'#c67845','고인구·저가격':'#177f73','저인구·고가격':'#d5aa7c','저인구·저가격':'#77989d'};
  const names={density:'인구밀도',population:'추정 거주인구',gravity:'거리 가중 배후인구',price_median:'아파트 ㎡당 가격',quadrant:'인구 × 가격 유형'};
  const units={density:'명/km²',population:'명',gravity:'명 상당',price_median:'만원/㎡'};
  const state={radius:500,metric:'density',station:'강동'};
  const mobile=()=>window.innerWidth<721;
  const font={family:"'Malgun Gothic','Apple SD Gothic Neo',sans-serif",color:'#385057',size:11};
  const config={responsive:true,displaylogo:false,scrollZoom:false,modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d'],toImageButtonOptions:{format:'png',scale:2}};
  const base=()=>({font,paper_bgcolor:'#fff',plot_bgcolor:'#fff',margin:{l:65,r:24,t:25,b:65},hoverlabel:{font:{family:font.family,size:12},bgcolor:'#fff',bordercolor:'#b5c9bd'},xaxis:{gridcolor:'#edf0e8',zeroline:false,linecolor:'#dbe2d7',automargin:true},yaxis:{gridcolor:'#edf0e8',zeroline:false,automargin:true}});
  const rows=()=>ALL.filter(x=>x.radius_m===state.radius);
  const populationRows=()=>rows().filter(x=>x.population_eligible);
  const comparisonRows=()=>rows().filter(x=>x.comparison_eligible);
  const selected=()=>rows().find(x=>x.station===state.station);
  const selectStation=name=>{if(!rows().some(x=>x.station===name))return;state.station=name;$('station-search').value=name;render();};
  function addClick(id){$(id).on('plotly_click',event=>{const id=event.points[0]?.customdata?.[0];const row=rows().find(x=>x.station_id===id);if(row)selectStation(row.station);});}
  function hover(r){return [r.station_id,r.station,fmt(r.population)+'명',fmt(r.density)+'명/km²',fmt(r.price_median)+'만원/㎡',fmt(r.trade_count)+'건',pct(r.observed_area_share)];}
  const hovertemplate='<b>%{customdata[1]}</b><br>추정 거주인구 %{customdata[2]}<br>인구밀도 %{customdata[3]}<br>아파트 가격 %{customdata[4]}<br>거래 %{customdata[5]} · 인구 연결 면적 %{customdata[6]}<extra></extra>';
  function renderMap(){
    const current=rows(), selectedRow=selected(), metric=state.metric;
    $('map-title').textContent=names[metric]+' 지도 · '+state.radius+'m';
    const traces=M.districts.map(d=>({type:'scatter',mode:'lines',x:d.x,y:d.y,fill:'toself',fillcolor:'#f2f3ed',line:{color:'#d1dbcf',width:.8},hoverinfo:'skip',showlegend:false}));
    traces.push({type:'scatter',mode:'text',x:M.districts.map(x=>x.cx),y:M.districts.map(x=>x.cy),text:M.districts.map(x=>x.name),textfont:{size:9,color:'#899b8b'},hoverinfo:'skip',showlegend:false});
    const eligible=r=>['quadrant','price_median'].includes(metric)?r.comparison_eligible:r.population_eligible;
    const invalid=current.filter(r=>!eligible(r));
    traces.push({type:'scatter',mode:'markers',x:invalid.map(r=>r.x),y:invalid.map(r=>r.y),customdata:invalid.map(hover),hovertemplate,marker:{size:6,color:'#c7cec9',line:{width:.4,color:'#fff'}},showlegend:false});
    if(metric==='quadrant'){
      for(const [category,color] of Object.entries(colors)){
        const data=current.filter(r=>r.comparison_eligible&&r.quadrant===category);
        traces.push({type:'scatter',mode:'markers',name:category,x:data.map(r=>r.x),y:data.map(r=>r.y),customdata:data.map(hover),hovertemplate,marker:{size:8,color,line:{color:'#fff',width:.6}}});
      }
    }else{
      const valid=current.filter(eligible), price=metric==='price_median';
      traces.push({type:'scatter',mode:'markers',x:valid.map(r=>r.x),y:valid.map(r=>r.y),customdata:valid.map(hover),hovertemplate,showlegend:false,marker:{size:8,color:valid.map(r=>r[metric]),colorscale:price?[[0,'#f3e3d3'],[.45,'#d6a06d'],[1,'#924823']]:[[0,'#d1e4d3'],[.5,'#59a391'],[1,'#08675f']],showscale:true,colorbar:{title:{text:units[metric],side:'top',font:{size:9}},thickness:9,len:.58,tickfont:{size:9},x:1.01},line:{color:'#fff',width:.5}}});
    }
    const shape=M.catchments[state.radius+'|'+selectedRow.station_id];
    if(shape)traces.push({type:'scatter',mode:'lines',x:shape.x,y:shape.y,fill:'toself',fillcolor:'rgba(220,139,76,.17)',line:{color:'#cf793e',width:2},hoverinfo:'skip',showlegend:false});
    traces.push({type:'scatter',mode:'markers+text',x:[selectedRow.x],y:[selectedRow.y],text:[selectedRow.station],textposition:'top center',textfont:{size:12,color:'#1b423d'},customdata:[hover(selectedRow)],hovertemplate,marker:{size:12,color:'#edb47c',line:{color:'#173c35',width:2}},showlegend:false});
    const layout={...base(),margin:{l:12,r:metric==='quadrant'?12:65,t:10,b:metric==='quadrant'?45:15},dragmode:'pan',uirevision:'seoul-map',xaxis:{visible:false,range:M.bounds.x,constrain:'domain'},yaxis:{visible:false,scaleanchor:'x',scaleratio:1,range:M.bounds.y,constrain:'domain'},legend:{orientation:'h',x:.5,xanchor:'center',y:-.01,font:{size:9},itemwidth:30},showlegend:metric==='quadrant'};
    Plotly.react('map-chart',traces,layout,{...config,scrollZoom:true});
    $('map-note').textContent='서울 자치구 경계 + 역 위치. 주황색 원은 선택한 역의 '+state.radius+'m 분석 범위입니다. 회색 점은 자료 조건 미충족.';
  }
  function renderDetail(){
    const r=selected();
    const issues=[];
    if(r.city_share<.95)issues.push('서울 포함 면적 95% 미만');
    if(r.observed_area_share<.8)issues.push('인구 연결 면적 80% 미만');
    if(r.trade_count<10)issues.push('아파트 거래 10건 미만');
    $('station-detail').innerHTML=`<div class="station-label">SELECTED STATION · ${state.radius}m</div><h3>${esc(stationLabel(r.station))}</h3><p class="station-lines">${esc(r.district)} · ${esc(r.lines)}<br>자치구는 역 대표점 위치 기준입니다.</p><div class="station-kpi"><span>공개값 기반 추정 거주인구</span><strong>${fmt(r.population)}<small>명</small></strong></div><div class="station-kpi"><span>인구밀도</span><strong>${fmt(r.density)}<small>명/km²</small></strong></div><div class="station-kpi"><span>거리 가중 배후인구</span><strong>${fmt(r.gravity)}<small>명 상당</small></strong></div><div class="station-kpi"><span>아파트 ㎡당 거래가격 중위값</span><strong>${fmt(r.price_median)}<small>만원/㎡</small></strong></div><div class="station-kpi inline"><span>거래 / 지번주소 수</span><strong>${fmt(r.trade_count)}건 / ${fmt(r.building_count)}곳</strong></div><div class="station-kpi inline"><span>인구값 연결 면적비</span><strong>${pct(r.observed_area_share)}</strong></div><div class="station-kpi inline"><span>서울 경계 포함률</span><strong>${pct(r.city_share)}</strong></div><div class="quality-note ${issues.length?'':'good'}">${issues.length?'주 가격 비교에서 제외: '+issues.join(' · '):'인구·면적·거래 수 조건 충족. 주 가격 비교에 포함됩니다.'}</div>`;
  }
  function renderScatter(){
    const current=comparisonRows(), r=selected();
    const s=S.sensitivity.find(x=>x.radius_m===state.radius);
    $('sample-label').textContent=state.radius+'m 가격 비교 표본';
    $('sample-count').innerHTML=fmt(s.sample_size)+'<small>개 역</small>';
    $('rho').textContent=rho(s.spearman_population_price);$('pearson').textContent=rho(s.pearson_population_price);
    const traces=[];
    for(const [category,color] of Object.entries(colors)){
      const data=current.filter(x=>x.quadrant===category);
      traces.push({type:'scatter',mode:'markers',name:category,x:data.map(x=>x.population),y:data.map(x=>x.price_median),customdata:data.map(hover),hovertemplate,marker:{color,size:9,opacity:.82,line:{color:'#fff',width:.7}}});
    }
    const pops=current.map(x=>x.population).sort((a,b)=>a-b), ps=current.map(x=>x.price_median).sort((a,b)=>a-b);
    const med=a=>a.length%2?a[(a.length-1)/2]:(a[a.length/2-1]+a[a.length/2])/2;
    const annotations=[];
    if(r.comparison_eligible){
      traces.push({type:'scatter',mode:'markers',x:[r.population],y:[r.price_median],customdata:[hover(r)],hovertemplate,showlegend:false,marker:{size:17,color:'rgba(0,0,0,0)',line:{color:'#173c35',width:2}}});
      annotations.push({x:r.population,y:r.price_median,text:esc(r.station),showarrow:true,arrowhead:0,ax:25,ay:-28,font:{size:11,color:'#173c35'},bgcolor:'rgba(255,255,255,.9)',borderpad:3});
    }
    const layout={...base(),margin:{l:mobile()?58:75,r:25,t:30,b:mobile()?100:75},xaxis:{...base().xaxis,title:{text:'추정 거주인구 (명)',standoff:18},tickformat:',.0f'},yaxis:{...base().yaxis,title:{text:'아파트 ㎡당 가격 (만원/㎡)',standoff:13},tickformat:',.0f'},legend:{orientation:'h',y:mobile()?-.29:-.2,x:.5,xanchor:'center',font:{size:9}},annotations,shapes:[{type:'line',xref:'x',yref:'paper',x0:med(pops),x1:med(pops),y0:0,y1:1,line:{color:'#c1ccc0',width:1,dash:'dot'}},{type:'line',xref:'paper',yref:'y',x0:0,x1:1,y0:med(ps),y1:med(ps),line:{color:'#c1ccc0',width:1,dash:'dot'}}]};
    Plotly.react('scatter-chart',traces,layout,config);
    $('scatter-title').textContent=state.radius+'m 거주인구와 아파트 ㎡당 가격';
  }
  function renderRankings(){
    const data=populationRows().sort((a,b)=>b.population-a.population).slice(0,15).reverse();
    $('ranking-title').textContent=state.radius+'m 추정 거주인구 상위 15개 역';
    Plotly.react('ranking-chart',[{type:'bar',orientation:'h',x:data.map(r=>r.population),y:data.map(r=>r.station),customdata:data.map(hover),hovertemplate,marker:{color:data.map(r=>r.station===state.station?'#cb804b':'#3e8c7c')},text:data.map(r=>fmt(r.population)),textposition:'outside',textfont:{size:10},cliponaxis:false}],{...base(),margin:{l:mobile()?92:105,r:58,t:18,b:55},xaxis:{...base().xaxis,title:{text:'추정 거주인구 (명)',standoff:14},tickformat:',.0f'},yaxis:{...base().yaxis,gridcolor:'transparent',tickfont:{size:10}},showlegend:false},config);
    const valid=populationRows();
    Plotly.react('indicator-chart',[{type:'scatter',mode:'markers',x:valid.map(r=>r.density),y:valid.map(r=>r.gravity),customdata:valid.map(hover),hovertemplate,marker:{size:7,color:valid.map(r=>r.station===state.station?'#cc804b':'#3b8c7b'),opacity:.8,line:{color:'#fff',width:.5}}}],{...base(),margin:{l:mobile()?63:70,r:25,t:25,b:65},xaxis:{...base().xaxis,title:{text:'인구밀도 (명/km²)',standoff:16},tickformat:',.0f'},yaxis:{...base().yaxis,title:{text:'거리 가중 배후인구 (명 상당)',standoff:13},tickformat:',.0f'},showlegend:false},config);
  }
  function renderStatic(){
    const c=S.correlations,top=S.top_population_quality[0],gravity=S.top_gravity[0];
    document.querySelector('.lead-number').innerHTML=esc(top.station)+'역 <strong>'+fmt(top.population)+'<span>명</span></strong>';
    document.querySelector('.lead-bottom b').textContent=rho(c.population_price_spearman);
    document.querySelector('.lead-result small').textContent=`자료 조건을 충족한 ${S.counts.comparable_stations}개 역. 인구가 많을수록 가격이 높다는 뚜렷한 관계는 나타나지 않았습니다.`;
    const main=ALL.filter(r=>r.radius_m===500),gangdong=main.find(r=>r.station==='강동'),jamsil=main.find(r=>r.station==='잠실새내');
    $('findings-content').innerHTML=`<div class="finding-text"><p>인구 자료 조건을 충족한 ${S.counts.population_quality_stations}개 역 중 <b>${esc(top.station)}역</b>의 공개값 기반 추정 거주인구가 ${fmt(top.population)}명으로 가장 많았습니다. 낮은 쪽에는 <b>안국역 ${fmt(S.lowest_population_quality.find(r=>r.station==='안국')?.population)}명</b>, 을지로4가역이 있습니다. 이 값은 주거 집중을 나타내며, 업무·상업·관광 기능을 포함한 도시 중심성은 별도 자료가 필요합니다.</p><p>역과의 거리를 반영하면 <b>${esc(gravity.station)}역</b>이 ${fmt(gravity.gravity)}명 상당으로 1위가 됩니다. 남구로역의 G/P는 44.1%, 강동역은 41.7%로, 전자는 같은 총인구 대비 역 가까이 배치된 인구의 가중 기여가 더 큽니다. 두 지표의 순위상관은 <b>${rho(c.density_gravity_spearman)}</b>로, 전체 공간 패턴은 매우 비슷합니다.</p></div><div class="finding-text"><p>강동역과 잠실새내역은 각각 ${fmt(gangdong.population)}명, ${fmt(jamsil.population)}명으로 배후인구가 비슷하지만, 아파트 ㎡당 가격은 <b>${fmt(gangdong.price_median)}만원과 ${fmt(jamsil.price_median)}만원</b>으로 약 ${fmt(jamsil.price_median/gangdong.price_median,1)}배 차이납니다. 강동·남구로·까치산은 ‘고인구·저가격’, 잠실새내·행당·한티는 ‘고인구·고가격’ 유형에 속합니다.</p><p class="takeaway"><b>많이 산다는 사실만으로 가격 수준을 설명하기는 어렵습니다.</b> 주 비교 표본 ${S.counts.comparable_stations}개 역의 인구–가격 순위상관은 ${rho(c.population_price_spearman)}입니다. 주거 형태와 아파트 재고 구성, 주택의 연식·면적, 일자리·교육 접근 등의 차이가 설명 후보이며, 이 분석만으로 각 원인의 효과를 확인하지는 못합니다.</p></div>`;
    const examples=['강동','남구로','잠실새내'];
    $('case-cards').innerHTML=examples.map(name=>{const r=main.find(x=>x.station===name);return `<button class="case-card" type="button" data-station="${esc(name)}"><span>${esc(r.quadrant)}</span><h3>${esc(name)}역</h3><p>추정 거주인구 <strong>${fmt(r.population)}명</strong></p><p>㎡당 가격 <strong>${fmt(r.price_median)}만원</strong></p><p>거래 ${fmt(r.trade_count)}건 · 준공연도 중위값 ${fmt(r.building_year_median)}년</p><small>500m 지도에서 이 역 보기 ↗</small></button>`;}).join('');
    $('case-cards').addEventListener('click',e=>{const el=e.target.closest('[data-station]');if(el){state.radius=500;$('radius').value='500';selectStation(el.dataset.station);$('explore').scrollIntoView({behavior:'smooth'});}});
    const sensitivity=S.sensitivity;
    Plotly.react('sensitivity-chart',[{type:'scatter',mode:'lines+markers',name:'반경별 조건 충족 표본',x:sensitivity.map(x=>x.radius_m),y:sensitivity.map(x=>x.spearman_population_price),line:{color:'#187c70',width:2},marker:{size:9},hovertemplate:'%{x}m<br>Spearman ρ %{y:.3f}<extra>반경별 표본</extra>'},{type:'scatter',mode:'lines+markers',name:'세 반경 공통 74개 역',x:sensitivity.map(x=>x.radius_m),y:sensitivity.map(x=>x.common_spearman_population_price),line:{color:'#c5824c',width:2,dash:'dot'},marker:{size:8},hovertemplate:'%{x}m<br>Spearman ρ %{y:.3f}<extra>공통 표본</extra>'}],{...base(),margin:{l:65,r:30,t:25,b:80},xaxis:{...base().xaxis,title:{text:'분석 반경 (m)'},tickvals:[300,500,800]},yaxis:{...base().yaxis,title:{text:'인구–가격 Spearman ρ'},range:[-.4,.1],zeroline:true,zerolinecolor:'#a4b9aa'},legend:{orientation:'h',y:-.35,x:.5,xanchor:'center',font:{size:10}}},config);
    $('sensitivity-table').innerHTML=`<table><thead><tr><th>반경</th><th>인구 1위</th><th>추정 거주인구</th><th>가격 비교 역 수</th><th>순위상관 ρ</th><th>공통 표본 ρ</th></tr></thead><tbody>${sensitivity.map(x=>`<tr><td>${x.radius_m}m</td><td>${esc(x.top_station)}역</td><td>${fmt(x.top_population)}명</td><td>${x.sample_size}개</td><td>${rho(x.spearman_population_price)}</td><td>${rho(x.common_spearman_population_price)}</td></tr>`).join('')}</tbody></table>`;
    $('sensitivity-note').textContent=`300m에서는 남구로, 500m에서는 강동, 800m에서는 길동이 인구 1위입니다. ‘어디에 가장 많이 사는가’는 범위 설정에 따라 달라집니다. 반경마다 주 비교 표본도 달라지므로, 세 반경 모두 조건을 충족한 ${sensitivity[0].common_sample_size}개 역만 비교한 결과도 함께 제시했습니다. 세 반경에서 양의 관계는 나타나지 않았지만, 관계의 크기는 반경에 민감합니다.`;
    $('robustness').innerHTML=`<div><b>인구 연결 면적 기준을 90%로 강화</b><strong>ρ ${rho(c.strict_90pct_spearman)}</strong><span>${c.strict_90pct_sample_size}개 역 · 500m</span></div><div><b>동일 거래 행을 제거한 비교</b><strong>ρ ${rho(c.deduplicated_spearman)}</strong><span>${c.deduplicated_sample_size}개 역 · 가격 중위값 재계산</span></div><div><b>거래 10건 이상 모든 역 비교</b><strong>ρ ${rho(c.all_price_stations_spearman)}</strong><span>인구·경계 포괄률 제한 해제 · 해석 주의</span></div>`;
    $('cleaning-details').innerHTML=`<p>원자료 ${fmt(S.counts.source_price_rows)}행에서 다음 순서로 처리해 ${fmt(S.counts.clean_price_rows)}행을 사용했습니다. 개별 거래의 가격을 임의로 절단하거나 극단값을 일괄 삭제하지 않았으며, 중위값과 거래 수·지번주소 수를 함께 제시했습니다.</p><div class="table-wrap"><table><thead><tr><th>처리</th><th>제외 행</th><th>남은 행</th></tr></thead><tbody>${S.cleaning_log.map(x=>`<tr><td>${esc(x.step)}</td><td>${fmt(x.removed)}</td><td>${fmt(x.remaining)}</td></tr>`).join('')}</tbody></table></div><p>인구는 to_in_001(총인구)만 추출하고 격자 코드로 1:1 연결했습니다. ${fmt(S.counts.grid_rows)}개 도형 중 ${fmt(S.counts.missing_grid_population)}개는 공개 인구값이 연결되지 않아 결측을 유지했습니다. 좌표계는 EPSG:5179로 통일하고 교차 면적으로 인구를 배분했습니다. 결측 면적에 인구를 외삽하지 않았습니다.</p><p>수도권 원본 ${S.counts.source_station_line_rows}개 노선별 기록 중 역 좌표가 서울 경계 안인 ${S.counts.seoul_station_line_rows}개를 추출했습니다. 괄호 속 부역명을 정리하고 ‘서울→서울역’, ‘총신대입구→이수’를 통합했습니다. 같은 역의 서로 다른 좌표는 중복 좌표를 먼저 제거한 뒤 평균했습니다. 신촌 2호선과 경의중앙선은 별개 역으로 유지했습니다. 이렇게 ${S.counts.stations}개 분석 단위를 만들었습니다.</p><p>500m에서 서울 포함률이 95%보다 낮은 역은 ${S.counts.boundary_flagged}개, 인구 연결 면적비가 80%보다 낮은 역은 ${S.counts.population_coverage_flagged}개입니다(사유 중복 가능). 인구 순위용 ${S.counts.population_quality_stations}개 역, 가격 비교용 ${S.counts.comparable_stations}개 역을 구분했습니다.</p><p>완전히 같은 거래 행 ${fmt(S.counts.retained_duplicate_rows)}개는 고유 거래번호가 없어 기본 분석에서 유지했습니다. 반복행을 제거하고 가격을 다시 집계한 민감도 결과도 제공합니다. 건축연도·면적의 중위값은 거래된 아파트의 구성일 뿐, 역세권 주택 전체의 특성은 아닙니다.</p>`;
    $('source-table').innerHTML=`<table><thead><tr><th>자료</th><th>시점 / 범위</th><th>사용 항목</th><th>출처</th></tr></thead><tbody><tr><td>100m 격자 인구</td><td>2024년</td><td>총인구 to_in_001</td><td><a href="${S.sources.population}" target="_blank" rel="noopener">국가데이터처 SGIS</a></td></tr><tr><td>격자·행정동 경계</td><td>2025년 · 수업 제공 도형</td><td>격자 코드, 도형, 서울 경계</td><td><a href="${S.sources.course}" target="_blank" rel="noopener">수업 저장소</a></td></tr><tr><td>역사마스터</td><td>수업 제공 CSV 스냅샷 · 기준일 미기재</td><td>역 이름, 호선, 좌표</td><td><a href="${S.sources.stations}" target="_blank" rel="noopener">서울 열린데이터광장</a></td></tr><tr><td>아파트 실거래가</td><td>2026.01.01~09.04 · 수업 제공 지오코딩</td><td>금액, 면적, 계약일, 취소일, 좌표</td><td><a href="${S.sources.prices}" target="_blank" rel="noopener">서울 열린데이터광장</a></td></tr><tr><td>격자값 해석 안내</td><td>비밀보호 처리 유의</td><td>공개값과 참값의 차이</td><td><a href="${S.sources.privacy}" target="_blank" rel="noopener">SGIS 비밀보호 안내</a></td></tr></tbody></table>`;
    const opts=ALL.filter(x=>x.radius_m===500).map(x=>`<option value="${esc(x.station)}"></option>`).join('');$('station-options').innerHTML=opts;$('station-search').value=state.station;
  }
  function render(){renderMap();renderDetail();renderScatter();renderRankings();}
  $('radius').addEventListener('change',e=>{state.radius=Number(e.target.value);render();});
  $('map-metric').addEventListener('change',e=>{state.metric=e.target.value;renderMap();});
  $('station-search').addEventListener('change',e=>{const name=e.target.value.trim().replace(/역$/,'');const exact=rows().find(x=>x.station===e.target.value.trim())||rows().find(x=>x.station===name);if(exact)selectStation(exact.station);else{e.target.setCustomValidity('목록에 있는 역 이름을 선택해 주세요.');e.target.reportValidity();}});
  $('station-search').addEventListener('input',e=>e.target.setCustomValidity(''));
  $('reset').addEventListener('click',()=>{Object.assign(state,{radius:500,metric:'density',station:'강동'});$('radius').value='500';$('map-metric').value='density';$('station-search').value='강동';Plotly.relayout('map-chart',{'xaxis.range':M.bounds.x,'yaxis.range':M.bounds.y});render();});
  renderStatic();render();['map-chart','scatter-chart','ranking-chart','indicator-chart'].forEach(addClick);
  window.addEventListener('resize',()=>{for(const id of ['map-chart','scatter-chart','ranking-chart','indicator-chart','sensitivity-chart'])Plotly.Plots.resize($(id));});
})();
