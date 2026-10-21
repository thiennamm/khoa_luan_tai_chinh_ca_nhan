// Kiểm thử sự kiện UI bằng Node chuẩn, DOM/fetch giả chỉ trong tiến trình test.
// Không gọi website, ghi DB, tải mô hình hoặc tạo dữ liệu dùng thật.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../static/js/transaction-form.js'), 'utf8');

class Element {
  constructor(value = '') {
    this.value = value;
    this.options = [];
    this.handlers = {};
    this.disabled = false;
    this.hidden = false;
    this.textContent = '';
  }
  get selectedOptions() { return this.options.filter(option => option.value === this.value); }
  addEventListener(name, handler) { (this.handlers[name] ??= []).push(handler); }
  async fire(name) { for (const handler of this.handlers[name] ?? []) await handler(); }
  dispatchEvent(event) { this.fire(event.type); }
  replaceChildren() { this.options = []; this.value = ''; }
  append(option) { this.options.push(option); }
}

function setup(fetchImpl) {
  const nodes = Object.fromEntries(['id_kind', 'id_category', 'category-kinds', 'classification-suggestion',
    'id_description', 'suggest-category', 'suggestion-result', 'suggestion-actions',
    'suggestion-category', 'apply-suggestion'].map(id => [id, new Element()]));
  nodes.id_kind.value = 'expense';
  nodes.id_description.value = 'purchase';
  nodes.id_category.options = [new Element(''), new Element('1'), new Element('2'), new Element('3')];
  nodes.id_category.value = '1';
  nodes['category-kinds'].textContent = JSON.stringify({'1': 'expense', '2': 'expense', '3': 'income'});
  nodes['classification-suggestion'].dataset = {url: '/giao-dich/goi-y-danh-muc/'};
  nodes['suggestion-actions'].hidden = true;
  nodes['apply-suggestion'].disabled = true;
  const requests = [];
  vm.runInNewContext(source, {
    document: {getElementById: id => nodes[id], createElement: () => new Element(),
      querySelector: () => ({value: 'test-csrf'})},
    Event: class { constructor(type) { this.type = type; } }, URLSearchParams,
    fetch: async (url, options) => { requests.push({url, options}); return fetchImpl(); },
  });
  return {nodes, requests};
}
const response = data => ({ok: true, redirected: false, json: async () => data});
const suggestion = {status: 'suggestion', label: 'Groceries', label_display: 'Thực phẩm', message: 'Chọn danh mục',
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
  assert.equal(requests.length, 1); // Áp dụng không có request lưu giao dịch.
  assert.equal(requests[0].url, '/giao-dich/goi-y-danh-muc/');
  assert.equal(requests[0].options.method, 'POST');
  assert.equal(requests[0].options.headers['X-CSRFToken'], 'test-csrf');
  assert.equal(requests[0].options.body.get('description'), 'purchase');
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
