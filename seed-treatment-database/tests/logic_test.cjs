const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'..','CPN_Seed_Treatment_Preview.html'),'utf8');
// Keep edge-case scenarios stable as the published EPA catalog changes weekly.
const data=JSON.parse(require('zlib').gunzipSync(fs.readFileSync(require('path').join(__dirname,'fixtures','catalog-2026-10-19.json.gz'))));
data.mode='snapshot';
const source=html.match(/<script>([\s\S]*)<\/script>/)[1].replace(/^const PREVIEW = .*$/m,()=> 'const PREVIEW = '+JSON.stringify(data)+';');
new Function(source);
const elements={};
function el(id){return elements[id]??=( {value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,checked:false,dataset:{},style:{setProperty(){}},open:false,addEventListener(){},setAttribute(){},removeAttribute(){},contains(){return false},getBoundingClientRect(){return {height:0,top:0,bottom:0}},focus(){},click(){},showModal(){this.open=true},close(){this.open=false},classList:{toggle(){return true}}});}
let siteInputs=[];
const tabs=['products','matrix','resources'].map(id=>({...el('tab-'+id),dataset:{tab:id}}));
const panels=['products','matrix','resources'].map(id=>({...el(id),id}));
const document={querySelector:s=>el(s),querySelectorAll:s=>['[data-tab]','[role=tab]'].includes(s)?tabs:s==='[role=tabpanel]'?panels:s==='#site-options input:checked'?siteInputs.filter(x=>x.checked):s==='#site-options input'?siteInputs:[],addEventListener(){},createElement:()=>el('anchor'),activeElement:null,documentElement:el('html')};
class FixedDate extends Date{constructor(...args){super(...(args.length?args:['2026-10-19T12:00:00Z']));}static now(){return new Date('2026-10-19T12:00:00Z').getTime();}}
const context=vm.createContext({document,window:{print(){},addEventListener(){}},console,URL,Blob,Intl,Date:FixedDate,AbortController,setTimeout:()=>1,clearTimeout(){},setInterval(){},requestAnimationFrame:fn=>fn(),getComputedStyle:()=>({position:'static'}),matchMedia:()=>({matches:false,addEventListener(){}}),localStorage:{getItem(){return null},setItem(){}},fetch:async()=>{throw Error('Offline fixture')}});
vm.runInContext(source,context);
const run=s=>vm.runInContext(s,context);
assert(data.products.length>1);assert.equal(run('catalog.products.length'),data.products.length);assert.equal(run('filtered.length'),data.products.length);
assert.equal(el('#start').disabled,false);
assert.equal((el('#results').innerHTML.match(/class="product /g)||[]).length,Math.min(25,data.products.length));
assert(el('#page-label').textContent.includes('Page 1 of '+Math.ceil(data.products.length/25)));
if(data.products.length>25){run('page=2;render(false)');assert(el('#page-label').textContent.includes('26–'));}
const sample=data.products.find(p=>p.ingredients.length)||data.products[0];
el('#query').value=sample.id;run('render()');assert(run('filtered.some(p=>p.id==='+JSON.stringify(sample.id)+')'));assert.equal(run('page'),1);
run('reset()');siteInputs=[{checked:true,value:'Barley (seed treatment)'}];run('render()');assert.equal(run('filtered.length'),data.products.filter(p=>p.sites.includes('Barley (seed treatment)')).length);
siteInputs=[];run('reset()');el('#query').value='mefenoxam';run('render()');assert.equal(run('filtered.length'),data.products.filter(p=>p.ingredients.some(a=>a.pc_code==='113502')||[p.name,p.registrant,p.alternate_names_raw||''].join(' ').toLowerCase().includes('mefenoxam')).length);
run('reset()');el('#technology').value='Plant-Incorp. Protectant';run('render()');assert.equal(run('filtered.length'),data.products.filter(p=>p.pesticide_type==='Plant-Incorp. Protectant').length);
run('reset()');el('#purpose').value='Herbicide';run('render()');assert.equal(run('filtered.length'),data.products.filter(p=>p.purposes.includes('Herbicide')).length);
for(const [filter,test] of [['verified',p=>p.ingredient_quality==='verified'],['base-linked',p=>p.ingredient_quality==='base-linked'],['needs-review',p=>p.ingredient_quality!=='verified']]){run('reset()');el('#quality').value=filter;run('render()');assert.equal(run('filtered.length'),data.products.filter(test).length);}
run('reset()');el('#start').value='2026-01-01';run('render()');assert.equal(run('filtered.length'),data.products.filter(p=>p.status_date>='2026-01-01').length);
el('#start').value='2099-01-01';el('#end').value='2026-01-01';run('render()');assert.equal(run('filtered.length'),0);assert.equal(el('#count').textContent,'Check your dates');
run('reset()');const pair=data.products.slice(0,2);run('selected=new Set('+JSON.stringify(pair.map(p=>p.id))+');compare()');for(const p of pair)assert(el('#matrix-body').innerHTML.includes(p.id));assert.equal(run('view'),'matrix');assert(!el('#dialog').open);
run('details('+JSON.stringify(sample.id)+')');assert(el('#dialog-body').innerHTML.includes(sample.id));assert(el('#dialog-body').innerHTML.includes('Workbook created'));
const missing=data.products.find(p=>p.ingredient_quality==='missing');if(missing){run('details('+JSON.stringify(missing.id)+')');assert(el('#dialog-body').innerHTML.includes('exclusion cannot be independently confirmed'));}
run('renderData()');assert(el('#data-grid').innerHTML.includes('Embedded snapshot; online checks enabled'));assert(el('#catalog-summary').innerHTML.includes(data.products.length.toLocaleString()));
for(const [id,value,test] of [['frac','4',p=>p.ingredients.some(a=>data.ingredient_reference[a.name.trim().replace(/\s+/g,' ').toLowerCase()]?.frac_code==='4')],['irac','4A',p=>p.ingredients.some(a=>data.ingredient_reference[a.name.trim().replace(/\s+/g,' ').toLowerCase()]?.irac_code==='4A')],['signal','NONE',p=>p.safety?.signal_word==='NONE'],['signal','NOT_SUPPLIED',p=>!p.safety?.signal_word],['rup','yes',p=>p.safety?.restricted_use===true]]){run('reset()');el('#'+id).value=value;run('render()');assert.equal(run('filtered.length'),data.products.filter(test).length);}
run('reset();tabs("guide")');assert(el('#guide-content').innerHTML.includes('Best management practices'));assert(el('#guide-content').innerHTML.includes('FRAC Code List 2026'));
const missingSignal=data.products.find(p=>p.safety?.signal_word_state==='missing'),explicitNone=data.products.find(p=>p.safety?.signal_word==='NONE');
if(missingSignal){run('details('+JSON.stringify(missingSignal.id)+')');assert(el('#dialog-body').innerHTML.includes('EPA signal: Not supplied'));}
if(explicitNone){run('details('+JSON.stringify(explicitNone.id)+')');assert(el('#dialog-body').innerHTML.includes('EPA signal: None reported by EPA'));}
run('reset();selected=new Set('+JSON.stringify(pair.map(p=>p.id))+');compare()');assert(el('#matrix-body').innerHTML.includes('FRAC fungicide groups'));assert(el('#matrix-body').innerHTML.includes('EPA restricted-use flag'));
assert(html.includes('href="data:application/pdf;base64,'));

// The four-column cap applies to both entry points; removal and filtering preserve order.
run('clearComparison();tabs("matrix")');assert(el('#matrix-body').innerHTML.includes('Build your side-by-side'));assert(el('#matrix-export').disabled);
for(const id of ['100-1648','7969-441','352-937','100-1508'])assert(run('setComparisonSelection('+JSON.stringify(id)+',true)'));
assert.equal(run('selected.size'),4);assert(el('#matrix-add').disabled);assert(!run('setComparisonSelection('+JSON.stringify(sample.id)+',true)'));assert.equal(run('selected.size'),4);
assert.equal(run('comparisonProducts().map(p=>p.id).join(",")'),'100-1648,7969-441,352-937,100-1508');
assert(run('setComparisonSelection("100-1648",true)'));assert.equal(run('selected.size'),4);
assert(!/efficacy/i.test(el('#matrix-body').innerHTML));assert(el('#matrix-body').innerHTML.includes('First EPA registration date'));
assert(el('#matrix-body').innerHTML.includes('product-wide'));assert(el('#matrix-body').innerHTML.includes('No reviewed label extract loaded'));
assert(el('#matrix-body').innerHTML.includes('0.25 fl oz'));assert(el('#matrix-body').innerHTML.includes('FRAC fungicide groups'));
run('setComparisonSelection("7969-441",false)');assert.equal(run('selected.size'),3);assert(!el('#matrix-add').disabled);
el('#matrix-search').value='Ilevo';run('renderMatrixPicker()');assert(el('#matrix-picker').innerHTML.includes('7969-441'));
el('#matrix-search').value='no-such-product-xyz';run('renderMatrixPicker()');assert(el('#matrix-add').disabled);
el('#matrix-search').value='';run('renderMatrixPicker()');
assert.equal(run('labelSpec(catalog.products.find(p=>p.id==="100-1648")).ready'),true);
assert.equal(run('labelSpec({...catalog.products.find(p=>p.id==="100-1648"),registration_number:"100-1648-999"}).ready'),false);
assert.equal(run('labelSpec({...catalog.products.find(p=>p.id==="100-1648"),latest_label_date:"2026-10-01"}).ready'),false);
assert.equal(run('labelSpec({...catalog.products.find(p=>p.id==="100-1648"),ingredients:[{pc_code:"090110",percent:40}]}).ready'),false);
run('globalThis.originalSpecs=JSON.stringify(catalog.label_specs);catalog.label_specs.records[0].review_due="2020-01-01"');
assert.equal(run('labelSpec(catalog.products.find(p=>p.id==="100-1648")).ready'),false);run('catalog.label_specs=JSON.parse(originalSpecs)');
const matrixExport=run('matrixCsv()');assert(matrixExport.includes('First EPA registration date'));assert(matrixExport.includes('0.25 fl oz'));assert(matrixExport.includes('https://www3.epa.gov/'));assert(!/efficacy/i.test(matrixExport));
run('globalThis.beforeMatrixName=catalog.products.find(p=>p.id==="100-1648").name;catalog.products.find(p=>p.id==="100-1648").name="<img src=x onerror=alert(1)>";renderMatrix()');
assert(!el('#matrix-body').innerHTML.includes('<img src=x'));run('catalog.products.find(p=>p.id==="100-1648").name=beforeMatrixName;clearComparison();tabs("products")');
console.log('PASS: matrix selection cap/order, empty state, search, source rows, label-version/composition guards, no efficacy content, CSV and escaping.');

// State feature data and controls are absent from the published tool.
assert(!('state_registration' in data));
assert(!html.includes('id="state"'));assert(!html.includes('id="state-status"'));assert(!html.includes('id="matrix-state"'));
assert(!html.includes('statePanel'));assert(!html.includes('registration-guide'));

// Label downloads must preserve identity and cover every result, including lookups.
const labelProduct=data.products.find(p=>p.safety?.label_url),distributor=data.products.find(p=>p.record_type==='DP');
const access=p=>run('labelAccess('+JSON.stringify(p)+')');
assert.equal(access(labelProduct).pdf,labelProduct.safety.label_url);
assert.equal(access(distributor).pdf,null);assert(access(distributor).note.includes(distributor.registration_number));
assert.equal(access({...distributor,safety:labelProduct.safety}).pdf,null,'Never relabel a base PDF as a distributor label');
assert.equal(access({...labelProduct,registration_number:'999999-99999'}).pdf,null);
assert.equal(access({...labelProduct,safety:{...labelProduct.safety,label_url:'javascript:alert(1)'}}).pdf,null);
assert.equal(access({...labelProduct,safety:{...labelProduct.safety,label_url:labelProduct.safety.label_url.replace('www3.epa.gov','example.com')}}).pdf,null);
assert.equal(access({...labelProduct,safety:{...labelProduct.safety,label_date:'2000-01-01'}}).pdf,null);
assert(access({...labelProduct,safety:{}}).lookup.endsWith(labelProduct.registration_number));
assert.equal(run('catalog.products.filter(p=>labelAccess(p).pdf).length'),628);
run('reset()');assert.equal(run('labelLinksCsv().split("\\r\\n").length'),data.products.length+1);
el('#query').value=labelProduct.id;run('render()');
assert(el('#results').innerHTML.includes('Open / download label (PDF)'));assert(el('#results').innerHTML.includes('data-label-link='));
assert.equal(run('labelLinksCsv().split("\\r\\n").length'),2);
run('details('+JSON.stringify(distributor.id)+')');assert(el('#dialog-body').innerHTML.includes('No direct distributor PDF'));
el('#query').value='no-product-matches-xyz';run('render()');assert(el('#export-labels').disabled);
run('reset()');el('#start').value='2099-01-01';run('render()');assert(el('#export-labels').disabled);run('reset()');
assert(run('labelLinksCsv([{...catalog.products[0],name:"=1+1"}])').includes("'=1+1"));
console.log('PASS: label PDF identity, distributor fallback, source/date guards, all-page label exports, empty results and CSV safety.');

assert.equal(run("esc('<script>')"),'&lt;script&gt;');assert.equal(run("safeUrl('javascript:alert(1)')"),'#');assert(run("csvCell('=1+1')").startsWith('"\''));
run("catalog.products[0].name='<img src=x onerror=alert(1)>';render()");assert(!el('#results').innerHTML.includes('<img src=x'));
assert.equal(run('catalog.meta.audit.excluded_records.length'),data.meta.audit.excluded_records.length);
console.log('PASS: '+data.products.length+'-record catalog, search, exact-site filters, synonyms, quality, dates, pagination, comparison, source disclosure, escaping and CSV cell safety. Mocked DOM; not browser rendering.');
(async()=>{run('reset();globalThis.exportedBlob=null;URL.createObjectURL=b=>{globalThis.exportedBlob=b;return "blob:fixture"};exportCsv()');const csv=await run('exportedBlob.text()');assert(csv.includes('Workbook created'));assert(csv.includes('Technology type'));assert(csv.includes('FRAC fungicide group'));assert(csv.includes('Signal word data state'));assert(csv.includes('Warning basis'));assert(!csv.includes('State evidence sources and dates'));assert(!csv.includes('Federal registration evidence'));assert(!csv.includes('State restriction details'));assert(csv.includes('Data-use notice'));assert.equal(csv.split('\r\n').length-1,data.products.reduce((n,p)=>n+Math.max(1,p.ingredients.length),0));console.log('PASS: CSV exports all filtered records across pages, with provenance.');})().catch(e=>{console.error(e);process.exitCode=1});

// Exercise real online refresh paths without accessing EPA or GitHub.
function refreshHarness(embedded=false){
 const nodes={},node=s=>nodes[s]??={value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,dataset:{},style:{setProperty(){}},open:false,addEventListener(){},setAttribute(){},removeAttribute(){},contains(){return false},getBoundingClientRect(){return{height:0}},focus(){},click(){},classList:{toggle(){return true}}};
 const doc={querySelector:node,querySelectorAll:()=>[],addEventListener(){},createElement:()=>node('anchor'),documentElement:node('html')};
 let replies={},intervals=[];const requests=[];
 const ctx=vm.createContext({document:doc,window:{addEventListener(){}},console,URL,Blob,Intl,Date:FixedDate,AbortController,setTimeout:()=>1,clearTimeout(){},setInterval(fn,ms){intervals.push({fn,ms});},requestAnimationFrame:fn=>fn(),getComputedStyle:()=>({position:'static'}),matchMedia:()=>({matches:false,addEventListener(){}}),localStorage:{getItem(){return null},setItem(){}},fetch:async url=>{requests.push(url);const value=replies[url.split('/').pop()];if(value instanceof Error||!value)throw value||Error('Offline fixture');if(value.httpError)return{ok:false};return{ok:true,json:async()=>JSON.parse(JSON.stringify(value))};}});
 let script=fs.readFileSync(require('path').join(__dirname,'..','static','index.html'),'utf8').match(/<script>([\s\S]*)<\/script>/)[1].replace(/^loadCatalog\(\);$/m,'');
 if(embedded)script=script.replace(/^const PREVIEW = .*$/m,()=> 'const PREVIEW = '+JSON.stringify(data)+';');
 vm.runInContext(script,ctx);
 return{run:s=>vm.runInContext(s,ctx),el:node,reply:next=>{replies=next;},requests,intervals};
}
(async()=>{
 const current=JSON.parse(JSON.stringify(data));current.mode='live';current.meta.source_checked='2026-10-01T12:00:00Z';current.meta.source_snapshot_date='2020-01-01';
 const status=(checked='2026-10-19T11:00:00Z',state='success',message='Sources checked; unchanged fixture.')=>({state,message,sources:{EPA:{state:state==='success'?'checked':'update failed; last published data retained',checked_at:checked}}});
 const host=refreshHarness();host.reply({'catalog.json':current,'sync-status.json':status()});await host.run('loadCatalog()');
 assert.equal(host.intervals.length,1);assert.equal(host.intervals[0].ms,300000);
 assert.equal(host.run('updateWarning()'),null,'Old workbook creation metadata must not imply an overdue retrieval');
 assert.equal(host.run('lastEpaCheck()'),'2026-10-19T11:00:00Z');
 assert(host.el('#data-grid').innerHTML.includes('<dt>Latest official retrieval</dt><dd>Oct 19, 2026</dd>'),'Latest check comes from status even when catalog is unchanged');
 host.el('#query').value=sample.id;host.run('selected=new Set(['+JSON.stringify(sample.id)+']);page=2;view="resources"');
 host.reply({'catalog.json':current,'sync-status.json':status('2026-10-19T11:00:00Z','failed','Source check failed fixture.')});await host.run('pollPublishedCatalog()');
 assert(host.el('#notice').innerHTML.includes('EPA update failed.'));assert(host.el('#data-grid').innerHTML.includes('Source check failed fixture.'),'Status-only refresh updates the source panel');
 assert.equal(host.el('#query').value,sample.id);assert.equal(host.run('page'),2);assert(host.run('selected.has('+JSON.stringify(sample.id)+')'));
 host.reply({'catalog.json':current,'sync-status.json':status()});await host.run('pollPublishedCatalog()');assert.equal(host.run('updateWarning()'),null,'A successful check clears the failure warning');
 host.reply({'catalog.json':current,'sync-status.json':{state:'success'}});await host.run('pollPublishedCatalog()');assert(host.el('#notice').innerHTML.includes('Published updates unavailable.'));assert(host.el('#notice').innerHTML.includes('update status'));
 host.reply({'catalog.json':{httpError:true},'sync-status.json':status()});await host.run('pollPublishedCatalog()');assert(host.el('#notice').innerHTML.includes('latest catalog'));assert.equal(host.run('catalog.products.length'),current.products.length);
 const malformed=JSON.parse(JSON.stringify(current));delete malformed.products[0].ingredients;host.reply({'catalog.json':malformed,'sync-status.json':status()});await host.run('pollPublishedCatalog()');assert(host.el('#notice').innerHTML.includes('latest catalog'));assert.equal(host.run('catalog.products[0].ingredients.length'),current.products[0].ingredients.length,'Malformed candidates cannot replace the displayed catalog');
 host.reply({'catalog.json':current,'sync-status.json':status('2026-10-17T11:00:00Z')});await host.run('pollPublishedCatalog()');assert(host.el('#notice').innerHTML.includes('EPA update check overdue.'));assert(host.el('#notice').innerHTML.includes('workbook creation date'));
 host.reply({'catalog.json':current,'sync-status.json':status('2026-10-17T12:00:00Z')});await host.run('pollPublishedCatalog()');assert.equal(host.run('updateWarning()'),null,'Exactly 48 hours is not over 48 hours');
 host.reply({'catalog.json':current,'sync-status.json':status()});await host.run('pollPublishedCatalog()');assert.equal(host.run('updateWarning()'),null);
 const newer=JSON.parse(JSON.stringify(current));newer.meta.last_successful_sync='2026-10-19T11:30:00Z';newer.products[0].name='Updated fixture product';
 host.el('#start').value='2020-01-01';host.el('#end').value='2026-10-01';host.reply({'catalog.json':newer,'sync-status.json':status()});await host.run('pollPublishedCatalog()');
 assert.equal(host.run('catalog.products[0].name'),'Updated fixture product');assert.equal(host.el('#query').value,sample.id);assert.equal(host.el('#start').value,'2020-01-01');assert.equal(host.el('#end').value,'2026-10-01');assert(host.run('selected.has('+JSON.stringify(sample.id)+')'));
 const download=refreshHarness(true);await download.run('loadCatalog()');assert(download.run('usingEmbeddedSnapshot'));assert(download.el('#notice').innerHTML.includes('Offline snapshot displayed.'));assert(!download.el('#notice').innerHTML.includes('EPA update failed.'));
 assert(download.requests.every(url=>url.startsWith('https://raw.githubusercontent.com/danieham-97/crop-protection-network/master/seed-treatment-database/static/')),'Downloads use the exact public repository catalog');
 download.reply({'catalog.json':newer,'sync-status.json':status()});await download.run('pollPublishedCatalog()');assert(!download.run('usingEmbeddedSnapshot'));assert.equal(download.run('catalog.products[0].name'),'Updated fixture product');assert.equal(download.run('updateWarning()'),null);
 download.reply({});await download.run('pollPublishedCatalog()');assert(!download.run('usingEmbeddedSnapshot'),'A lost connection retains newer loaded data instead of reverting');assert.equal(download.run('catalog.products[0].name'),'Updated fixture product');assert(download.el('#notice').innerHTML.includes('Published updates unavailable.'));
 download.reply({'catalog.json':newer,'sync-status.json':status()});await download.run('pollPublishedCatalog()');assert.equal(download.run('updateWarning()'),null);
 console.log('PASS: online downloads, offline fallback/recovery, status-only refresh, 48-hour warnings, failed polling retention and filter/selection preservation.');
})().catch(e=>{console.error(e);process.exitCode=1});

