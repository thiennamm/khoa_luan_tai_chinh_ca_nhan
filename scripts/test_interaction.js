const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,'../static/js/form-feedback.js'),'utf8');

function setup(fetch) {
  let fireTimeout, cleared=0, focused=0, onPageShow;
  const sandbox={AbortController,fetch,
    setTimeout:fn=>{fireTimeout=fn;return 17;},clearTimeout:id=>{assert.equal(id,17);cleared++;},
    document:{querySelector:()=>({focus(){focused++;}}),addEventListener(){}},window:{addEventListener:(name,fn)=>{onPageShow=fn;}}};
  vm.runInNewContext(source,sandbox);
  return {api:sandbox.SoThuChiInteraction,timeout:()=>fireTimeout(),cleared:()=>cleared,focused:()=>focused,pageShow:()=>onPageShow()};
}
test('timeout aborts waiting and never retries a POST or changes its body',async()=>{
  let calls=0, options;
  const f=setup((url,opt)=>{calls++;options=opt;return new Promise((resolve,reject)=>{
    opt.signal.addEventListener('abort',()=>reject(new Error('aborted')));
  });});
  const body=new URLSearchParams({action:'apply'});
  const pending=f.api.requestJson('/qa/',{method:'POST',body});
  f.timeout();await assert.rejects(pending);
  assert.equal(options.body,body);assert.equal(calls,1);assert.equal(f.cleared(),1);
});
test('redirect, bad JSON and HTTP error are not automatically retried',async()=>{
  for(const response of [{redirected:true},{json:async()=>{throw new Error('private server detail');}},
    {ok:false,status:500,json:async()=>({status:'error'})}]){
    let calls=0;const f=setup(async()=>{calls++;return response;});
    try{await f.api.requestJson('/qa/',{method:'POST'});}catch{}
    assert.equal(calls,1);assert.equal(f.cleared(),1);
  }
});
test('server error summary receives focus; async text is not repeatedly rewritten',()=>{
  const f=setup();assert.equal(f.focused(),0);f.pageShow();assert.equal(f.focused(),1);
  let writes=0,text='';const attrs={};
  const node={setAttribute:(k,v)=>{attrs[k]=v;},focus(){this.focused=true;},
    get textContent(){return text;},set textContent(value){text=value;writes++;}};
  f.api.announce(node,'Chưa nhận được kết quả',true);
  f.api.announce(node,'Chưa nhận được kết quả',true);
  assert.equal(writes,1);assert.equal(attrs['aria-live'],'polite');assert.equal(node.focused,true);
});
