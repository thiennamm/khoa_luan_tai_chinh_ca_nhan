// Behavioral tests: no parser copy, no real requests or financial data.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const quick = fs.readFileSync(path.join(__dirname, '../static/js/quick-entry.js'), 'utf8');
const ml = fs.readFileSync(path.join(__dirname, '../static/js/transaction-form.js'), 'utf8');
const money = fs.readFileSync(path.join(__dirname, '../static/js/money.js'), 'utf8');
class Element {
  constructor(value='') {this.value=value;this.handlers={};this.hidden=false;this.disabled=false;this.children=[];this.options=[];this.dataset={};this.textContent='';}
  addEventListener(type,fn) {(this.handlers[type]??=[]).push(fn);}
  async fire(type,event={}) {for(const fn of this.handlers[type]??[]) await fn(event);}
  dispatchEvent(event) {this.fire(event.type);}
  setAttribute(name,value) {this[name]=value;}
  querySelector() {return {value:'qa-csrf'};}
  append(...items) {this.children.push(...items);this.options.push(...items);}
  replaceChildren() {this.children=[];this.options=[];this.value='';}
  get selectedOptions() {return this.options.filter(o=>o.value===this.value);}
}
const response = (data,ok=true) => ({ok,redirected:false,json:async()=>data});
const parsed = () => ({status:'ok',fields:{amount:'45000',date:'2026-10-25',kind:'expense',description:'Ăn trưa'},
  date_defaulted:true,warnings:['Kiểm tra; chưa lưu.']});
function setup(fetcher=async()=>response(parsed()),withML=false) {
  const ids=['quick-entry','transaction-form','quick-text','quick-fill','quick-status','quick-preview','quick-fields',
    'quick-warnings','quick-summary','quick-needed','quick-attention','quick-default-date','quick-details','quick-detail-result',
    'quick-confirmation','quick-replace','quick-cancel','id_kind','id_amount','id_date','id_category','id_description',
    'category-kinds','classification-suggestion','suggestion-mode','suggest-category','suggestion-result','suggestion-actions',
    'suggestion-category','apply-suggestion','suggestion-id'];
  const n=Object.fromEntries(ids.map(id=>[id,new Element()]));
  n.id_date.value='2026-10-25';n['quick-text'].value='Chi: Ăn trưa 45k';
  n['quick-entry'].dataset.url='/quick/';n['classification-suggestion'].dataset={url:'/suggest/',actionUrl:'/action/'};
  n['category-kinds'].textContent='{"1":"expense","2":"income"}';
  n.id_category.options=[new Element(''),new Element('1'),new Element('2')];n['suggestion-mode'].value='vi';
  const requests=[];
  const sandbox={document:{getElementById:id=>n[id],createElement:()=>new Element(),querySelector:()=>({value:'qa-csrf'})},
    URLSearchParams,Event:class{constructor(type){this.type=type;}},fetch:async(url,options)=>{
      requests.push({url,options});return fetcher(url,options);
    }};
  vm.createContext(sandbox);
  vm.runInContext(money,sandbox);
  if(withML)vm.runInContext(ml,sandbox);
  vm.runInContext(quick,sandbox);
  return {n,requests};
}
test('explicit click prefills blank form, previews text, POST CSRF only, never saves/requests ML',async()=>{
  const {n,requests}=setup();
  assert.equal(requests.length,0);
  await n['quick-fill'].fire('click');
  assert.equal(n.id_amount.value,'45.000');assert.equal(n.id_date.value,'2026-10-25');
  assert.equal(n.id_description.value,'Ăn trưa');assert.equal(n.id_category.value,'');
  assert.equal(n['quick-preview'].hidden,false);assert.equal(n['quick-confirmation'].hidden,true);
  assert.equal(requests.length,1);assert.equal(requests[0].url,'/quick/');
  assert.equal(requests[0].options.method,'POST');assert.equal(requests[0].options.headers['X-CSRFToken'],'qa-csrf');
  assert.match(n['quick-status'].textContent,/chưa lưu/);
});
test('existing values require explicit replacement; cancel and later editing preserve data',async()=>{
  const {n}=setup();n.id_amount.value='99000';n.id_description.value='Thủ công';n.id_category.value='1';
  await n['quick-fill'].fire('click');assert.equal(n.id_amount.value,'99000');assert.equal(n['quick-confirmation'].hidden,false);
  await n['quick-cancel'].fire('click');await n['quick-replace'].fire('click');assert.equal(n.id_amount.value,'99000');
  await n['quick-fill'].fire('click');n.id_amount.value='123000';await n.id_amount.fire('input');
  await n['quick-replace'].fire('click');assert.equal(n.id_amount.value,'123000');
  await n['quick-fill'].fire('click');await n['quick-replace'].fire('click');assert.equal(n.id_amount.value,'45.000');assert.equal(n.id_category.value,'');
});
test('parser errors, offline, expired session keep all manual values',async()=>{
  for(const fetcher of [async()=>response({status:'invalid',errors:['Có nhiều số tiền']},false),
    async()=>{throw Error('offline');},async()=>({redirected:true})]){
    const {n}=setup(fetcher);n.id_amount.value='99000';n.id_description.value='Cũ';
    await n['quick-fill'].fire('click');assert.equal(n.id_amount.value,'99000');assert.equal(n.id_description.value,'Cũ');
    assert.equal(n['quick-status'].role,'alert');assert.equal(n['quick-fill'].disabled,false);
  }
});
test('late response after input change is ignored; input while fetching requires replacement',async()=>{
  let finish;const {n}=setup(()=>new Promise(resolve=>{finish=resolve;}));
  const old=n['quick-fill'].fire('click');n['quick-text'].value='Mới';await n['quick-text'].fire('input');finish(response(parsed()));await old;
  assert.equal(n.id_amount.value,'');
  const current=n['quick-fill'].fire('click');n.id_amount.value='12000';await n.id_amount.fire('input');finish(response(parsed()));await current;
  assert.equal(n.id_amount.value,'12000');assert.equal(n['quick-confirmation'].hidden,false);
});
test('preview uses text nodes, unknown kind remains empty and category is not guessed',async()=>{
  const data=parsed();data.fields.kind='';data.fields.description='<img src=x onerror=alert(1)>';
  const {n}=setup(async()=>response(data));await n['quick-fill'].fire('click');
  assert.equal(n.id_kind.value,'');assert.equal(n.id_category.value,'');
  assert.equal(n['quick-fields'].children[3].children[1].textContent,data.fields.description);
  assert.equal(n['quick-fields'].children[1].children[0].textContent,'Ngày (mặc định hôm nay)');
});
test('quick replacement reuses ML invalidation and revokes old receipt; Apply cannot reuse it',async()=>{
  const {n,requests}=setup(async(url,options)=>{
    if(url==='/quick/')return response(parsed());
    if(url==='/action/')return response({status:'revoked'});
    return response({status:'suggestion',suggestion_id:'old-receipt',label:'Restaurants',label_display:'Ăn uống',message:'Xem lại',categories:[{id:1,name:'Ăn'}]});
  },true);
  n.id_kind.value='expense';n.id_description.value='Cũ';await n.id_kind.fire('change');
  await n['suggest-category'].fire('click');assert.equal(n['suggestion-id'].value,'old-receipt');
  await n['quick-fill'].fire('click');await n['quick-replace'].fire('click');
  assert.equal(n['suggestion-id'].value,'');assert.equal(n['suggestion-actions'].hidden,true);
  assert.ok(requests.some(r=>r.url==='/action/'&&r.options.body.get('action')==='revoke'));
  await n['apply-suggestion'].fire('click');assert.equal(n.id_category.value,'');
});
test('compact summary shows formatted integer, date and missing kind with visible required fields',async()=>{
  const data=parsed();data.fields.amount='30000';data.fields.kind='';data.warnings=[
    'Chưa xác định loại thu/chi. Hãy tự chọn.', 'Không có ngày: dùng hôm nay.',
    'Danh mục sẽ để trống để bạn tự chọn hoặc chủ động yêu cầu gợi ý ML.'];
  const {n}=setup(async()=>response(data));await n['quick-fill'].fire('click');
  assert.equal(n['quick-summary'].textContent,'30.000 VND · 25/10/2026 · Chưa chọn loại');
  assert.equal(n['quick-status'].textContent,'Đã điền, chưa lưu.');
  assert.equal(n['quick-details'].open,false);
  assert.equal(n['quick-default-date'].hidden,false);
  assert.equal(n['quick-attention'].hidden,false);
  assert.deepEqual(n['quick-needed'].children.map(e=>e.textContent),['Chọn loại thu/chi.','Chọn danh mục.']);
  assert.equal(n['quick-warnings'].children.length,3); // Full explanation is still available.
});
test('future/unknown warnings stay outside details; original warnings remain available; large VND is intact',async()=>{
  const data=parsed();data.fields.amount='999999999999999';data.date_defaulted=false;
  data.warnings=['Ngày đã nhận diện ở tương lai; hãy kiểm tra.', 'Cảnh báo mới cần xem lại'];
  const {n}=setup(async()=>response(data));await n['quick-fill'].fire('click');
  assert.equal(n['quick-summary'].textContent,'999.999.999.999.999 VND · 25/10/2026 · Chi tiêu');
  assert.equal(n['quick-default-date'].hidden,true);
  assert.ok(n['quick-needed'].children.some(e=>e.textContent==='Ngày ở tương lai: kiểm tra trước khi lưu.'));
  assert.ok(n['quick-needed'].children.some(e=>e.textContent==='Cảnh báo mới cần xem lại'));
  assert.equal(n['quick-warnings'].children[0].textContent,data.warnings[0]);
});
