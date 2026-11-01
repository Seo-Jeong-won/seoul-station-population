/* Contract tests for our own app state and generated figure specifications.
   This is not a browser-rendering test. */
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=__dirname;
const elements=new Map(),figures=new Map(),checks=[];
class Element {
  constructor(id){this.id=id;this.innerHTML='';this.textContent='';this.value='';this.listeners={};this.plotEvents={};this.validity='';}
  addEventListener(type,fn){this.listeners[type]=fn;}
  on(type,fn){this.plotEvents[type]=fn;}
  setCustomValidity(value){this.validity=value;}
  reportValidity(){return !this.validity;}
  scrollIntoView(){}
}
const element=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
const window={innerWidth:1280,listeners:{},addEventListener(type,fn){this.listeners[type]=fn;}};
const context=vm.createContext({window,document:{getElementById:element,querySelector:element},Plotly:{react(id,traces,layout){figures.set(id,{traces,layout});},relayout(){},Plots:{resize(){}}},console});
vm.runInContext(fs.readFileSync(path.join(root,'dist/assets/data.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/assets/app.js'),'utf8'),context);
function check(name,fn){fn();checks.push(name);}
function change(id,value){const e=element(id);e.value=value;e.listeners.change({target:e});}
check('default 500m sample and selected station',()=>{assert.match(element('sample-count').innerHTML,/141/);assert.match(element('station-detail').innerHTML,/강동역/);assert.match(element('station-detail').innerHTML,/35,944/);});
check('five populated chart specifications',()=>{assert.equal(figures.size,5);for(const f of figures.values())assert.ok(f.traces.length);});
check('scatter includes exactly 141 cohort points plus selection',()=>{assert.equal(figures.get('scatter-chart').traces.reduce((n,t)=>n+t.x.length,0),142);});
check('300m updates cohort and values',()=>{change('radius','300');assert.match(element('sample-count').innerHTML,/124/);assert.match(element('map-title').textContent,/300m/);});
check('800m updates cohort and values',()=>{change('radius','800');assert.match(element('sample-count').innerHTML,/111/);assert.match(element('scatter-title').textContent,/800m/);});
check('all map modes produce usable figure specifications',()=>{for(const mode of ['population','gravity','price_median','quadrant','density']){change('map-metric',mode);assert.ok(figures.get('map-chart').traces.length>25);if(mode==='quadrant')assert.equal(figures.get('map-chart').layout.showlegend,true);}});
check('station alias label does not add a second station suffix',()=>{change('station-search','서울역');assert.match(element('station-detail').innerHTML,/서울역<\/h3>/);assert.doesNotMatch(element('station-detail').innerHTML,/서울역역/);});
check('separate Sinchon station lookup',()=>{change('station-search','신촌 · 2호선');assert.match(element('station-detail').innerHTML,/신촌 · 2호선역/);});
check('missing population station remains selectable without a false zero',()=>{change('station-search','김포공항');assert.match(element('station-detail').innerHTML,/김포공항역/);assert.match(element('station-detail').innerHTML,/주 가격 비교에서 제외/);});
check('invalid search does not change the selected station',()=>{change('station-search','존재하지않는역');assert.ok(element('station-search').validity);assert.match(element('station-detail').innerHTML,/김포공항역/);});
check('case button resets radius and synchronizes selection',()=>{element('case-cards').listeners.click({target:{closest(){return {dataset:{station:'잠실새내'}};}}});assert.match(element('station-detail').innerHTML,/잠실새내역/);assert.match(element('map-title').textContent,/500m/);});
check('chart click synchronizes selected station',()=>{const id=window.ANALYSIS_DATA.stations.find(x=>x.station==='남구로').station_id;element('scatter-chart').plotEvents.plotly_click({points:[{customdata:[id]}]});assert.match(element('station-detail').innerHTML,/남구로역/);});
check('reset restores the 500m Gangdong default',()=>{element('reset').listeners.click();assert.match(element('sample-count').innerHTML,/141/);assert.match(element('station-detail').innerHTML,/강동역/);assert.match(element('map-title').textContent,/인구밀도/);});
check('map selection has real projected geometry and finite coordinates',()=>{const selected=figures.get('map-chart').traces.at(-1);assert.ok(Number.isFinite(selected.x[0])&&Number.isFinite(selected.y[0]));const shape=figures.get('map-chart').traces.at(-2);assert.ok(shape.x.length>=16);});
check('resize event processes all chart containers',()=>{window.innerWidth=390;window.listeners.resize();});
check('all three radii and station ids are complete',()=>{const rows=window.ANALYSIS_DATA.stations;assert.equal(rows.length,924);for(const r of [300,500,800])assert.equal(rows.filter(x=>x.radius_m===r).length,308);});
check('generated bundle does not contain non-JSON numeric literals',()=>{assert.doesNotMatch(fs.readFileSync(path.join(root,'dist/assets/data.js'),'utf8'),/:\s*(NaN|Infinity)\b/);});
fs.writeFileSync(path.join(root,'results/web_contract_validation.json'),JSON.stringify({passed:true,checks,browser_rendering_verified:false,rendering_limit:'Native app access approval timed out; browser access host unavailable.'},null,2));
console.log(`Passed ${checks.length} app-state and figure-specification checks. Browser rendering is not covered.`);
