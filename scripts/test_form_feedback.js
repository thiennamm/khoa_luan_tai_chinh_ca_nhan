// Kiểm tra hành vi gửi form; không kiểm tra các chi tiết trình bày CSS.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function fixture(method = 'post') {
  const handlers = {};
  const attributes = new Map();
  const children = [];
  const buttonAttributes = new Map();
  const button = {name:'action', value:'preview_mapping', disabled:false, dataset:{},
    getAttribute:key=>buttonAttributes.get(key)??null, setAttribute:(key,value)=>buttonAttributes.set(key,value), removeAttribute:key=>buttonAttributes.delete(key)};
  const form = {
    method, dataset: {}, querySelectorAll:()=>[button],
    getAttribute: key => attributes.get(key) ?? null,
    setAttribute: (key, value) => attributes.set(key, value),
    removeAttribute: key => attributes.delete(key),
    appendChild: child => children.push(child),
  };
  const document = {
    addEventListener: (name, fn) => { handlers[name] = fn; }, querySelector:()=>null,
    createElement: () => ({ setAttribute() {}, remove() { children.splice(children.indexOf(this), 1); } }),
  };
  const window = { addEventListener: (name, fn) => { handlers[name] = fn; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/js/form-feedback.js'), 'utf8'), { document, window });
  const submit = (prevented = false) => {
    const event = { target: form, defaultPrevented: prevented, preventDefault() { this.defaultPrevented = true; } };
    handlers.submit(event);
    return event;
  };
  return { form, button, children, handlers, submit };
}

test('POST giữ lần gửi đầu, phản hồi chờ, chặn lần gửi lặp', () => {
  const f = fixture();
  assert.equal(f.submit().defaultPrevented, false);
  assert.equal(f.form.getAttribute('aria-busy'), 'true');
  assert.match(f.children[0].textContent, /Đang xử lý/);
  assert.equal(f.submit().defaultPrevented, true);
  assert.equal(f.children.length, 2);
});
test('GET và submit đã bị hủy không bị can thiệp', () => {
  const get = fixture('get');
  assert.equal(get.submit().defaultPrevented, false);
  assert.equal(get.children.length, 0);
  const canceled = fixture();
  canceled.submit(true);
  assert.equal(canceled.children.length, 0);
});
test('pageshow khôi phục thao tác sau Back/Forward', () => {
  const f = fixture();
  f.submit(); f.handlers.pageshow();
  assert.equal(f.children.length, 0);
  assert.equal(f.form.getAttribute('aria-busy'), null);
  assert.equal(f.submit().defaultPrevented, false);
});
test('khôi phục aria-busy có trước mà không đổi thuộc tính khác', () => {
  const f = fixture();
  f.form.setAttribute('aria-busy', 'false');
  f.form.setAttribute('data-test', 'giữ nguyên');
  f.submit(); f.handlers.pageshow();
  assert.equal(f.form.getAttribute('aria-busy'), 'false');
  assert.equal(f.form.getAttribute('data-test'), 'giữ nguyên');
});

test('submitter name/value and enabled state remain intact; aria-disabled is restored',()=>{
  const f=fixture();f.submit();
  assert.equal(f.button.name,'action');assert.equal(f.button.value,'preview_mapping');
  assert.equal(f.button.disabled,false);assert.equal(f.button.getAttribute('aria-disabled'),'true');
  assert.match(f.children[1].textContent,/chưa xác nhận được kết quả/);
  assert.match(f.children[1].textContent,/Kiểm tra danh sách/);
  f.handlers.pageshow();assert.equal(f.button.getAttribute('aria-disabled'),null);
});
test('pending label is per form and canceled validation never locks',()=>{
  const f=fixture();f.form.dataset.pendingLabel='Đang lưu…';
  f.submit(true);assert.equal(f.children.length,0);
  f.submit();assert.match(f.children[0].textContent,/Đang lưu/);
});
