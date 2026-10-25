const {test}=require('node:test');
const assert=require('node:assert/strict');
const money=require('../static/js/money.js');

test('shared VND display: zero, signed, large and unknown without float arithmetic',()=>{
  for(const [raw,want] of [['0','0 VND'],['50000','50.000 VND'],['1250000','1.250.000 VND'],
    ['-50000','-50.000 VND'],['999999999999999','999.999.999.999.999 VND']])assert.equal(money.formatVnd(raw),want);
  assert.equal(money.formatVnd(null),'—');assert.equal(money.formatVnd(undefined),'—');
});
test('strict raw/pasted input accepts only plain integer or complete 3-digit groups',()=>{
  assert.equal(money.inputDigits('50000'),'50000');assert.equal(money.inputDigits('50.000'),'50000');
  for(const raw of ['50,000','50.00','1.25.000','50.000,00','50 000','50.000 VND','-50.000'])assert.equal(money.inputDigits(raw),null);
});
function input(value){
  const handlers={};
  const el={value,selectionStart:value.length,selectionEnd:value.length,selectionDirection:'none',dataset:{},
    addEventListener(type,fn){handlers[type]=fn;},setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b;},
    fire(type,event={}){handlers[type]?.(event);}};
  money.attach(el);return el;
}
test('bulk replacement and invalid pasted groups are not silently repaired',()=>{
  const el=input('');el.value='50000';el.fire('input',{inputType:'insertFromPaste'});assert.equal(el.value,'50.000');
  for(const raw of ['50.00','50,000','1.25.000']){
    el.value=raw;el.fire('input',{inputType:'insertFromPaste'});el.fire('blur');assert.equal(el.value,raw);
  }
});
test('typing a digit inside a known formatted value regroups; backspace at dot selects adjacent digit',()=>{
  const el=input('50000');assert.equal(el.value,'50.000');el.setSelectionRange(4,4);
  el.fire('beforeinput',{inputType:'insertText',data:'1'});el.value='50.0100';el.fire('input',{inputType:'insertText'});
  assert.equal(el.value,'500.100');
  el.value='50.000';el.setSelectionRange(3,3);el.fire('beforeinput',{inputType:'deleteContentBackward'});
  assert.equal(el.selectionStart,1);assert.equal(el.selectionEnd,3);
  el.value='5000';el.fire('input',{inputType:'deleteContentBackward'});assert.equal(el.value,'5.000');
  el.setSelectionRange(0,el.value.length);el.fire('beforeinput',{inputType:'deleteContentBackward'});
  el.value='';el.fire('input',{inputType:'deleteContentBackward'});assert.equal(el.value,'');
});
test('composition is left intact until completed; blur normalizes leading zeros only when valid',()=>{
  const el=input('');el.fire('compositionstart');el.value='50000';el.fire('input',{isComposing:true});assert.equal(el.value,'50000');
  el.fire('compositionend');assert.equal(el.value,'50.000');el.value='00050000';el.fire('input');assert.equal(el.value,'00050000');
  el.fire('blur');assert.equal(el.value,'50.000');
});
