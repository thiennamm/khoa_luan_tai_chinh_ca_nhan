const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/monthly-report.js'), 'utf8');

test('print is invoked only by explicit click, with no data request or automatic PDF', () => {
  let printed = 0;
  const button = { hidden: true, addEventListener(name, action) { assert.equal(name, 'click'); this.click = action; } };
  vm.runInNewContext(source, { document: { getElementById: () => button }, window: { print() { printed++; } } });
  assert.equal(button.hidden, false);
  assert.equal(printed, 0);
  button.click();
  assert.equal(printed, 1);
});
test('invalid/absent report has no print action and causes no script error', () => {
  assert.doesNotThrow(() => vm.runInNewContext(source, { document: { getElementById: () => null } }));
});
