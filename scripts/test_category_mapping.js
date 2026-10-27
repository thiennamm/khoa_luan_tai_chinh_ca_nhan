const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/category-mapping.js'), 'utf8');

function fixture(raw = JSON.stringify({ expense: { Entertainment: ['Vé <phim>', 'Trò chơi'] } })) {
  const kind = { value: 'expense', addEventListener(event, fn) { this.change = fn; } };
  const label = { value: '', addEventListener(event, fn) { this.change = fn; } };
  const notice = { textContent: '', hidden: true };
  const nodes = { 'category-mapping-peers': { textContent: raw }, id_kind: kind,
    id_canonical_label: label, 'mapping-peers': notice };
  vm.runInNewContext(source, { document: { getElementById: id => nodes[id] } });
  return { kind, label, notice };
}

test('blank mapping stays blank; selecting a linked label displays plain text without editing selection', () => {
  const f = fixture();
  assert.equal(f.label.value, '');
  assert.equal(f.notice.hidden, true);
  f.label.value = 'Entertainment'; f.label.change();
  assert.equal(f.label.value, 'Entertainment');
  assert.equal(f.notice.hidden, false);
  assert.equal(f.notice.textContent, 'Nhãn này đang liên kết với các danh mục: Vé <phim>, Trò chơi');
  assert.equal(f.notice.innerHTML, undefined);
});
test('kind change or clearing label removes stale peer notice', () => {
  const f = fixture();
  f.label.value = 'Entertainment'; f.label.change();
  f.kind.value = 'income'; f.kind.change();
  assert.equal(f.notice.hidden, true);
  assert.equal(f.notice.textContent, '');
  f.kind.value = 'expense'; f.kind.change();
  assert.equal(f.notice.hidden, false);
  f.label.value = ''; f.label.change();
  assert.equal(f.notice.hidden, true);
});
test('missing elements or corrupt JSON leave the ordinary form usable', () => {
  assert.doesNotThrow(() => fixture('not JSON'));
  assert.doesNotThrow(() => vm.runInNewContext(source, { document: { getElementById: () => null } }));
});
