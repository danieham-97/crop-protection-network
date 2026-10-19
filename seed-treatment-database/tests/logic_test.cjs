const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'..','CPN_Seed_Treatment_Preview.html'),'utf8');
const source=html.match(/<script>([\s\S]*)<\/script>/)[1];
new Function(source);
const elements={};
function el(id){return elements[id]??=( {value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,checked:false,dataset:{},style:{},open:false,addEventListener(){},setAttribute(){},focus(){},click(){},showModal(){this.open=true},close(){this.open=false},classList:{toggle(){return true}}});}
let siteInputs=[];
const tabs=['products','ingredients','data'].map(id=>({...el('tab-'+id),dataset:{tab:id}}));
const panels=['products','ingredients','data'].map(id=>({...el(id),id}));
const document={querySelector:s=>el(s),querySelectorAll:s=>s==='[data-tab]'?tabs:s==='[role=tabpanel]'?panels:s==='#site-options input:checked'?siteInputs.filter(x=>x.checked):s==='#site-options input'?siteInputs:[],addEventListener(){},createElement:()=>el('anchor'),activeElement:null};
const context=vm.createContext({document,window:{print(){}},console,URL,Blob,Intl,Date,setTimeout:()=>1,clearTimeout(){},setInterval(){},localStorage:{getItem(){return null},setItem(){}},fetch:async()=>{throw Error('Unexpected network in preview')}});
vm.runInContext(source,context);
const run=s=>vm.runInContext(s,context);
const data=JSON.parse(fs.readFileSync(require('path').join(__dirname,'..','static','catalog.json'),'utf8'));
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
run('reset()');const pair=data.products.slice(0,2);run('selected=new Set('+JSON.stringify(pair.map(p=>p.id))+');compare()');for(const p of pair)assert(el('#dialog-body').innerHTML.includes(p.id));assert(!el('#dialog-body').innerHTML.includes('Source examples only'));
run('details('+JSON.stringify(sample.id)+')');assert(el('#dialog-body').innerHTML.includes(sample.id));assert(el('#dialog-body').innerHTML.includes('Workbook created'));
const missing=data.products.find(p=>p.ingredient_quality==='missing');if(missing){run('details('+JSON.stringify(missing.id)+')');assert(el('#dialog-body').innerHTML.includes('exclusion cannot be independently confirmed'));}
run('renderData()');assert(el('#data-grid').innerHTML.includes('Not running in this file'));assert(el('#notice').innerHTML.includes(data.products.length.toLocaleString()));
assert.equal(run("esc('<script>')"),'&lt;script&gt;');assert.equal(run("safeUrl('javascript:alert(1)')"),'#');assert(run("csvCell('=1+1')").startsWith('"\''));
run("catalog.products[0].name='<img src=x onerror=alert(1)>';render()");assert(!el('#results').innerHTML.includes('<img src=x'));
assert.equal(run('catalog.meta.audit.excluded_records.length'),data.meta.audit.excluded_records.length);
console.log('PASS: '+data.products.length+'-record catalog, search, exact-site filters, synonyms, quality, dates, pagination, comparison, source disclosure, escaping and CSV cell safety. Mocked DOM; not browser rendering.');
(async()=>{run('reset();globalThis.exportedBlob=null;URL.createObjectURL=b=>{globalThis.exportedBlob=b;return "blob:fixture"};exportCsv()');const csv=await run('exportedBlob.text()');assert(csv.includes('Workbook created'));assert(csv.includes('Technology type'));assert.equal(csv.split('\r\n').length-1,data.products.reduce((n,p)=>n+Math.max(1,p.ingredients.length),0));console.log('PASS: CSV exports all filtered records across pages, with provenance.');})().catch(e=>{console.error(e);process.exitCode=1});
