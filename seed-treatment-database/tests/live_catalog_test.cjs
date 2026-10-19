// Exercise the real generated snapshot, independently of frozen regression data.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..'),data=JSON.parse(fs.readFileSync(path.join(root,'static/catalog.json'),'utf8'));
const html=fs.readFileSync(path.join(root,'CPN_Seed_Treatment_Preview.html'),'utf8'),source=html.match(/<script>([\s\S]*)<\/script>/)[1];
const elements={};const el=s=>elements[s]??={value:'',innerHTML:'',textContent:'',hidden:false,disabled:false,dataset:{},style:{setProperty(){}},addEventListener(){},setAttribute(){},removeAttribute(){},contains(){return false},getBoundingClientRect(){return{height:0}},focus(){},click(){},classList:{toggle(){}}};
const doc={querySelector:el,querySelectorAll:()=>[],addEventListener(){},createElement:()=>el('anchor'),documentElement:el('html')};
const ctx=vm.createContext({document:doc,window:{addEventListener(){}},console,Date,Intl,URL,Blob,setTimeout:()=>1,clearTimeout(){},setInterval(){},requestAnimationFrame:fn=>fn(),matchMedia:()=>({matches:false,addEventListener(){}}),getComputedStyle:()=>({position:'static'}),localStorage:{getItem(){return null},setItem(){}},fetch(){throw Error('Offline snapshot requested network');}});
vm.runInContext(source,ctx);const run=s=>vm.runInContext(s,ctx);
assert.equal(run('catalog.products.length'),data.products.length);assert.equal(run('filtered.length'),data.products.length);
assert.equal((el('#results').innerHTML.match(/class="product /g)||[]).length,Math.min(25,data.products.length));
const sample=data.products.find(p=>p.ingredients.length)||data.products[0];el('#query').value=sample.id;run('render()');assert(run('filtered.some(p=>p.id==='+JSON.stringify(sample.id)+')'));
run('reset();selected=new Set('+JSON.stringify(data.products.slice(0,4).map(p=>p.id))+');renderMatrix()');
assert.equal((el('#matrix-body').innerHTML.match(/scope="col"/g)||[]).length,Math.min(4,data.products.length)+1);
for(const p of data.products.slice(0,4))assert(run('matrixCsv()').includes(p.registration_number));
run('renderData()');assert(el('#data-grid').innerHTML.includes('Automatic source checks'));
assert.equal(run('catalog.meta.audit.sha256'),data.meta.audit.sha256);
console.log('PASS: current published snapshot loads, searches and compares '+data.products.length+' products with matching source hash.');
