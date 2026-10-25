// Shared display/input formatting. No money arithmetic and no float conversion.
((root) => {
  const plain = /^[0-9]+$/;
  const grouped = /^[1-9][0-9]{0,2}(?:\.[0-9]{3})+$/;
  function inputDigits(value) {
    const text = String(value).trim();
    if (plain.test(text)) return text;
    return grouped.test(text) ? text.replace(/\./g, '') : null;
  }
  function groupDigits(digits) { return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }
  function formatVnd(value) {
    if (value === null || value === undefined) return '—';
    const text = String(value);
    if (!/^-?[0-9]+$/.test(text)) return '—';
    const negative = text.startsWith('-');
    const digits = (negative ? text.slice(1) : text).replace(/^0+(?=\d)/, '');
    return (negative && digits !== '0' ? '-' : '') + groupDigits(digits) + ' VND';
  }
  const countDigits = text => (text.match(/[0-9]/g) || []).length;
  function positionAfterDigits(text, count) {
    if (!count) return 0;
    for (let i=0, seen=0; i<text.length; i++) {
      if (/[0-9]/.test(text[i]) && ++seen === count) return i+1;
    }
    return text.length;
  }
  function formatInputElement(input, trustedDigitEdit=false, blur=false) {
    const raw = input.value;
    const digits = trustedDigitEdit && /^[0-9.]*$/.test(raw)
      ? raw.replace(/\./g, '') : inputDigits(raw);
    if (digits === null) return; // Invalid pasted/raw text is never silently repaired.
    const start = input.selectionStart ?? raw.length, end = input.selectionEnd ?? start;
    const left = countDigits(raw.slice(0,start)), right = countDigits(raw.slice(0,end));
    const canonical = blur ? digits.replace(/^0+(?=\d)/, '') : digits;
    const formatted = !blur && /^0[0-9]/.test(canonical) ? canonical : groupDigits(canonical);
    if (formatted === raw) return;
    input.value = formatted;
    if (!blur && typeof document !== 'undefined' && document.activeElement === input) {
      input.setSelectionRange(positionAfterDigits(formatted,left), positionAfterDigits(formatted,right), input.selectionDirection || 'none');
    }
  }
  function attach(input) {
    if (input.dataset.vndReady) return;
    input.dataset.vndReady = 'true';
    let before = null, composing = false;
    formatInputElement(input, false, true);
    input.addEventListener('compositionstart', () => { composing=true; before=null; });
    input.addEventListener('compositionend', () => { composing=false; before=null; formatInputElement(input); });
    input.addEventListener('beforeinput', event => {
      if (composing || event.isComposing) return;
      const validBefore = inputDigits(input.value) !== null;
      let start=input.selectionStart, end=input.selectionEnd;
      if (validBefore && start===end) {
        // Deleting an automatic dot deletes the adjacent digit in one keystroke.
        if (event.inputType==='deleteContentBackward' && start>1 && input.value[start-1]==='.') start-=2;
        else if (event.inputType==='deleteContentForward' && input.value[start]==='.') end+=2;
        if (start!==end) input.setSelectionRange(start,end);
      }
      before = {valid:validBefore,type:event.inputType,data:event.data};
    });
    input.addEventListener('input', event => {
      if (composing || event.isComposing) return;
      const safeEdit = before?.valid && (before.type?.startsWith('delete')
        || (before.type==='insertText' && /^[0-9]*$/.test(before.data || '')));
      before=null;
      formatInputElement(input, Boolean(safeEdit));
    });
    input.addEventListener('blur', () => { before=null; formatInputElement(input,false,true); });
  }
  const api = {inputDigits,formatVnd,formatInputElement,attach};
  root.SoThuChiMoney = Object.freeze(api);
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  if (typeof document !== 'undefined' && document.querySelectorAll) {
    document.querySelectorAll('[data-vnd-input]').forEach(attach);
  }
})(globalThis);
