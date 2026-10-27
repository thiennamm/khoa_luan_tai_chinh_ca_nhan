// Kiểm thử sự kiện UI bằng Node chuẩn, DOM/fetch giả chỉ trong tiến trình test.
// Không gọi website, ghi DB, tải mô hình hoặc tạo dữ liệu dùng thật.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const shared = fs.readFileSync(path.join(__dirname, '../static/js/form-feedback.js'), 'utf8');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../static/js/transaction-form.js'), 'utf8');

class Element {
  constructor(value = '') {
    this.value = value;
    this.options = [];
    this.handlers = {};
    this.disabled = false;
    this.hidden = false;
    this.textContent = '';this.dataset={};
  }
  setAttribute(name,value){this[name]=value;}
  focus(){this.focused=true;}
  get selectedOptions() { return this.options.filter(option => option.value === this.value); }
  addEventListener(name, handler) { (this.handlers[name] ??= []).push(handler); }
  async fire(name, event = {}) { for (const handler of this.handlers[name] ?? []) await handler(event); }
  dispatchEvent(event) { this.fire(event.type); }
  replaceChildren() { this.options = []; this.value = ''; }
  append(option) { this.options.push(option); }
}

function setup(fetchImpl, actionImpl) {
  const nodes = Object.fromEntries(['id_kind', 'id_category', 'category-kinds', 'classification-suggestion',
    'id_description', 'suggest-category', 'suggestion-result', 'suggestion-actions',
    'suggestion-category', 'apply-suggestion', 'suggestion-mode', 'suggestion-id', 'transaction-form'].map(id => [id, new Element()]));
  nodes['suggestion-mode'].value = 'en';
  nodes.id_kind.value = 'expense';
  nodes.id_description.value = 'purchase';
  nodes.id_category.options = [new Element(''), new Element('1'), new Element('2'), new Element('3')];
  nodes.id_category.value = '1';
  nodes['category-kinds'].textContent = JSON.stringify({'1': 'expense', '2': 'expense', '3': 'income'});
  nodes['classification-suggestion'].dataset = {url: '/giao-dich/goi-y-danh-muc/', actionUrl: '/suggestion-action/'};
  nodes['suggestion-actions'].hidden = true;
  nodes['apply-suggestion'].disabled = true;
  const requests = [];
  const windowHandlers={};
  const sandbox={
    window:{addEventListener:(name,fn)=>{windowHandlers[name]=fn;}},AbortController,setTimeout,clearTimeout,
    document: {addEventListener(){},getElementById: id => nodes[id], createElement: () => new Element(),
      querySelector: selector => selector==='[data-error-summary]'?null:({value: 'test-csrf'})},
    Event: class { constructor(type) { this.type = type; } }, URLSearchParams,
    fetch: async (url, options) => {
      requests.push({url, options});
      if (url === '/suggestion-action/') {
        if (actionImpl) return actionImpl(options);
        return response(options.body.get('action') === 'apply'
          ? {status: 'applied', category_id: Number(options.body.get('category'))}
          : {status: 'revoked'});
      }
      return fetchImpl();
    },
  };
  vm.createContext(sandbox);vm.runInContext(shared,sandbox);vm.runInContext(source,sandbox);
  return {nodes, requests, windowHandlers};
}
const response = data => ({ok: true, redirected: false, json: async () => data});
const suggestion = {status: 'suggestion', suggestion_id: 'server-receipt', label: 'Groceries', label_display: 'Thực phẩm', message: 'Chọn danh mục',
  categories: [{id: 1, name: 'Hiện tại'}, {id: 2, name: '<img src=x onerror=alert(1)>'}, {id: 3, name: 'Sai loại'}, {id: 99, name: 'Không có trong form'}]};

test('gợi ý/việc chọn không ghi đè; chỉ Áp dụng đổi danh mục; fetch chỉ POST gợi ý với CSRF', async () => {
  const {nodes: n, requests} = setup(async () => response(suggestion));
  await n['suggest-category'].fire('click');
  assert.equal(n.id_category.value, '1');
  assert.deepEqual(n['suggestion-category'].options.map(o => o.value), ['', '1', '2']);
  assert.equal(n['suggestion-category'].options[2].textContent, suggestion.categories[1].name);
  assert.equal(n['apply-suggestion'].disabled, true);
  n['suggestion-category'].value = '2';
  await n['suggestion-category'].fire('change');
  assert.equal(n.id_category.value, '1');
  assert.equal(n['apply-suggestion'].disabled, false);
  await n['apply-suggestion'].fire('click');
  assert.equal(n.id_category.value, '2');
  assert.equal(requests.length, 2); // POST Apply xác nhận server; không lưu giao dịch.
  assert.equal(requests[1].url, '/suggestion-action/');
  assert.equal(requests[1].options.body.get('action'), 'apply');
  assert.equal(requests[1].options.body.get('suggestion_id'), 'server-receipt');
  assert.equal(n['suggestion-id'].value, 'server-receipt');
  assert.equal(requests[0].url, '/giao-dich/goi-y-danh-muc/');
  assert.equal(requests[0].options.method, 'POST');
  assert.equal(requests[0].options.headers['X-CSRFToken'], 'test-csrf');
  assert.equal(requests[0].options.body.get('description'), 'purchase');
  assert.equal(requests[0].options.body.get('mode'), 'en');
});

test('Transfer/không ánh xạ/không có gợi ý không có hành động áp dụng', async () => {
  for (const data of [{status:'review',label:'Transfer',message:'Xem lại',categories:[]},
    {status:'suggestion',label:'Travel',message:'Chưa ánh xạ',categories:[]},
    {status:'no_suggestion',message:'Trống'}]) {
    const {nodes:n} = setup(async () => response(data));
    await n['suggest-category'].fire('click');
    assert.equal(n['suggestion-actions'].hidden, true);
    assert.equal(n['apply-suggestion'].disabled, true);
    assert.equal(n.id_category.value, '1');
  }
});

test('đổi mô tả hủy gợi ý, không thể áp dụng gợi ý cũ', async () => {
  const {nodes:n} = setup(async () => response(suggestion));
  await n['suggest-category'].fire('click');
  n['suggestion-category'].value = '2';
  await n['suggestion-category'].fire('change');
  n.id_description.value = 'changed';
  await n.id_description.fire('input');
  await n['apply-suggestion'].fire('click');
  assert.equal(n.id_category.value, '1');
  assert.equal(n['suggestion-actions'].hidden, true);
});

test('đáp ứng request cũ sau thay loại giao dịch bị bỏ qua', async () => {
  let resolve;
  const {nodes:n} = setup(() => new Promise(done => {resolve = done;}));
  const pending = n['suggest-category'].fire('click');
  n.id_kind.value = 'income';
  await n.id_kind.fire('change');
  resolve(response(suggestion));
  await pending;
  assert.equal(n['suggestion-actions'].hidden, true);
  assert.equal(n['suggestion-result'].textContent, '');
  assert.equal(n.id_category.value, ''); // Bộ lọc loại hiện có của website.
});

test('mất kết nối hoặc lỗi tải giữ danh mục thủ công', async () => {
  for (const fetchImpl of [async () => {throw Error('offline');},
    async () => ({ok:false,json:async () => ({status:'unavailable',message:'Tạm không sẵn sàng'})})]) {
    const {nodes:n} = setup(fetchImpl);
    await n['suggest-category'].fire('click');
    assert.equal(n.id_category.value, '1');
    assert.equal(n['suggest-category'].disabled, false);
    assert.equal(n['suggestion-actions'].hidden, true);
    assert.ok(n['suggestion-result'].textContent);
  }
});

test('đầu vào quá dài bị chặn ngay trên UI', async () => {
  const {nodes:n, requests} = setup(async () => response(suggestion));
  n.id_description.value = 'x'.repeat(501);
  await n['suggest-category'].fire('click');
  assert.equal(requests.length, 0);
  assert.equal(n.id_category.value, '1');
});

test('đổi chế độ hủy gợi ý; đổi lại vẫn phải yêu cầu mới', async () => {
  const {nodes:n, requests} = setup(async () => response(suggestion));
  await n['suggest-category'].fire('click');
  n['suggestion-category'].value = '2';
  await n['suggestion-category'].fire('change');
  n['suggestion-mode'].value = 'vi';
  await n['suggestion-mode'].fire('change');
  n['suggestion-mode'].value = 'en';
  await n['suggestion-mode'].fire('change');
  await n['apply-suggestion'].fire('click');
  assert.equal(n.id_category.value, '1');
  assert.equal(n['suggestion-actions'].hidden, true);
  n['suggestion-mode'].value = 'vi';
  await n['suggest-category'].fire('click');
  assert.equal(requests.filter(r => r.url === '/giao-dich/goi-y-danh-muc/')[1].options.body.get('mode'), 'vi');
});

test('đổi chế độ khi đang fetch hoặc đọc JSON bỏ phản hồi cũ', async () => {
  for (const delayJSON of [false, true]) {
    let resolve;
    let started;
    const ready = new Promise(done => {started = done;});
    const {nodes:n} = setup(() => delayJSON
      ? {ok:true, json:() => new Promise(done => {resolve = done; started();})}
      : new Promise(done => {resolve = done; started();}));
    const pending = n['suggest-category'].fire('click');
    await ready;
    n['suggestion-mode'].value = 'vi';
    await n['suggestion-mode'].fire('change');
    resolve(delayJSON ? suggestion : response(suggestion));
    await pending;
    assert.equal(n['suggestion-result'].textContent, '');
    assert.equal(n['suggestion-actions'].hidden, true);
    assert.equal(n.id_category.value, '1');
  }
});

test('không áp dụng khi mode đổi bằng mã mà chưa phát sự kiện', async () => {
  const {nodes:n} = setup(async () => response(suggestion));
  await n['suggest-category'].fire('click');
  n['suggestion-category'].value = '2';
  n['suggestion-mode'].value = 'vi';
  await n['apply-suggestion'].fire('click');
  assert.equal(n.id_category.value, '1');
});

test('lỗi ở mỗi chế độ không gửi yêu cầu đổi mô hình', async () => {
  for (const mode of ['vi', 'en']) {
    const {nodes:n, requests} = setup(async () => {throw Error('unavailable');});
    n['suggestion-mode'].value = mode;
    await n['suggest-category'].fire('click');
    assert.equal(requests.length, 1);
    assert.equal(requests[0].options.body.get('mode'), mode);
    assert.equal(n.id_category.value, '1');
  }
});

test('đổi đầu vào xóa receipt trong form và gửi POST thu hồi', async () => {
  for (const [field, event] of [['id_description','input'], ['id_kind','change'], ['suggestion-mode','change']]) {
    const {nodes:n, requests} = setup(async () => response(suggestion));
    await n['suggest-category'].fire('click');
    assert.equal(n['suggestion-id'].value, 'server-receipt');
    await n[field].fire(event);
    assert.equal(n['suggestion-id'].value, '');
    assert.equal(requests[1].options.body.get('action'), 'revoke');
    assert.equal(requests[1].options.headers['X-CSRFToken'], 'test-csrf');
  }
});

test('server từ chối Apply thì giữ lựa chọn thủ công và bỏ receipt', async () => {
  const {nodes:n} = setup(async () => response(suggestion), async () => ({
    ok:false, json:async () => ({status:'invalid'}),
  }));
  await n['suggest-category'].fire('click');
  n['suggestion-category'].value = '2';
  await n['apply-suggestion'].fire('click');
  assert.equal(n.id_category.value, '1');
  assert.equal(n['suggestion-id'].value, '');
  assert.match(n['suggestion-result'].textContent, /Chưa xác nhận/);
});

test('không lưu khi Apply đang chờ; kết quả Apply đến muộn không ghi đè sau đổi mô tả', async () => {
  let finish;
  const {nodes:n} = setup(async () => response(suggestion), options =>
    options.body.get('action') === 'apply'
      ? new Promise(resolve => {finish=resolve;}) : Promise.resolve(response({status:'revoked'})));
  await n['suggest-category'].fire('click');
  n['suggestion-category'].value = '2';
  const pending = n['apply-suggestion'].fire('click');
  let prevented = false;
  await n['transaction-form'].fire('submit', {preventDefault() {prevented=true;}});
  assert.equal(prevented, true);
  n.id_description.value = 'mới';
  await n.id_description.fire('input');
  finish(response({status:'applied',category_id:2}));
  await pending;
  assert.equal(n.id_category.value, '1');
  assert.equal(n['suggestion-id'].value, '');
});

test('two rapid suggestion clicks start one request; failure restores manual input',async()=>{
  let finish;const {nodes:n,requests}=setup(()=>new Promise(resolve=>{finish=resolve;}));
  const pending=n['suggest-category'].fire('click');await n['suggest-category'].fire('click');
  assert.equal(requests.length,1);assert.equal(n['suggest-category'].disabled,true);
  finish({ok:false,status:500,json:async()=>({status:'error',message:'private trace must not display'})});await pending;
  assert.equal(n['suggest-category'].disabled,false);assert.equal(n.id_category.value,'1');
  assert.equal(n['suggestion-result'].focused,true);assert.doesNotMatch(n['suggestion-result'].textContent,/private trace/);
});
test('Back/Forward restores fetch controls, invalidates old receipt and ignores late reply',async()=>{
  let finish;const {nodes:n,windowHandlers}=setup(()=>new Promise(resolve=>{finish=resolve;}));
  const pending=n['suggest-category'].fire('click');
  windowHandlers.pageshow({persisted:true});
  assert.equal(n['suggest-category'].disabled,false);assert.equal(n['suggestion-id'].value,'');
  finish(response(suggestion));await pending;assert.equal(n['suggestion-id'].value,'');
  assert.equal(n['suggestion-actions'].hidden,true);assert.equal(n.id_category.value,'1');
});
