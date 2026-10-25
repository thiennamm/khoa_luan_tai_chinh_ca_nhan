// Parser stays on the server. This script only previews and prefills existing fields.
(() => {
  const panel = document.getElementById('quick-entry');
  const form = document.getElementById('transaction-form');
  if (!panel || !form) return;
  const input = document.getElementById('quick-text');
  const button = document.getElementById('quick-fill');
  const status = document.getElementById('quick-status');
  const preview = document.getElementById('quick-preview');
  const details = document.getElementById('quick-fields');
  const warnings = document.getElementById('quick-warnings');
  const summary = document.getElementById('quick-summary');
  const needed = document.getElementById('quick-needed');
  const attention = document.getElementById('quick-attention');
  const defaultDate = document.getElementById('quick-default-date');
  const disclosure = document.getElementById('quick-details');
  const detailResult = document.getElementById('quick-detail-result');
  const confirmation = document.getElementById('quick-confirmation');
  const replace = document.getElementById('quick-replace');
  const cancel = document.getElementById('quick-cancel');
  const csrf = form.querySelector('[name=csrfmiddlewaretoken]');
  const fields = Object.fromEntries(['kind', 'amount', 'date', 'category', 'description']
    .map(name => [name, document.getElementById('id_' + name)]));
  const initialDate = fields.date.value;
  let generation = 0;
  let pending = null;
  let filling = false;
  button.disabled = false;
  function message(text, error = false, filled = false) {
    status.textContent = text;
    status.setAttribute('role', error ? 'alert' : 'status');
    status.setAttribute('data-filled', filled ? 'true' : 'false');
  }
  function discard() { pending = null; confirmation.hidden = true; }
  input.addEventListener('input', () => {
    generation += 1;
    button.disabled = false;
    discard(); preview.hidden = true; detailResult.hidden = true;
    message('Câu nhập đã thay đổi. Bấm Điền vào biểu mẫu để phân tích lại.');
  });
  for (const field of Object.values(fields)) {
    for (const name of ['input', 'change']) field.addEventListener(name, () => {
      if (filling || !pending) return;
      discard();
      message('Biểu mẫu đã thay đổi. Hãy phân tích lại nếu muốn thay thế bằng nhập nhanh.');
    });
  }
  function hasData() {
    return fields.kind.value || fields.amount.value || fields.category.value
      || fields.description.value.trim() || fields.date.value !== initialDate;
  }
  function fill(data) {
    discard(); filling = true;
    try {
      for (const name of ['amount', 'date', 'kind', 'description']) fields[name].value = data.fields[name];
      globalThis.SoThuChiMoney.formatInputElement(fields.amount);
      fields.category.value = '';
      // Reuse existing category filtering and receipt revocation/invalidation listeners.
      fields.kind.dispatchEvent(new Event('change', {bubbles: true}));
      fields.description.dispatchEvent(new Event('input', {bubbles: true}));
      fields.category.dispatchEvent(new Event('change', {bubbles: true}));
    } finally { filling = false; }
    message('Đã điền, chưa lưu.', false, true);
  }
  replace.addEventListener('click', () => { if (pending) fill(pending); });
  cancel.addEventListener('click', () => { discard(); message('Đã giữ nguyên dữ liệu biểu mẫu.'); });
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const current = ++generation;
    discard(); preview.hidden = true; detailResult.hidden = true; disclosure.open = false;
    button.disabled = true;
    message('Đang phân tích theo quy tắc…');
    try {
      const response = await fetch(panel.dataset.url, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': csrf.value, 'Accept': 'application/json'},
        body: new URLSearchParams({text: input.value}),
      });
      if (current !== generation) return;
      if (response.redirected) throw new Error('Session expired');
      const data = await response.json();
      if (current !== generation) return;
      if (!response.ok || data.status !== 'ok') {
        message(Array.isArray(data.errors) ? data.errors.join(' ') : 'Chưa phân tích được. Hãy nhập bằng biểu mẫu thường.', true);
        return;
      }
      details.replaceChildren(); warnings.replaceChildren(); needed.replaceChildren();
      const kindLabel = {income: 'Thu nhập', expense: 'Chi tiêu'}[data.fields.kind] || 'Chưa chọn loại';
      // Display only: group the server's integer string without float conversion.
      const amountLabel = globalThis.SoThuChiMoney.formatVnd(data.fields.amount);
      summary.textContent = `${amountLabel} · ${data.fields.date.split('-').reverse().join('/')} · ${kindLabel}`;
      defaultDate.hidden = !data.date_defaulted;
      const notices = data.fields.kind ? ['Chọn danh mục.'] : ['Chọn loại thu/chi.', 'Chọn danh mục.'];
      for (const warning of data.warnings) {
        if (warning.startsWith('Chưa xác định loại thu/chi.') || warning.startsWith('Danh mục sẽ để trống')
            || warning.startsWith('Không có ngày:')) continue; // Already visible as fields/default-date notices.
        if (warning.startsWith('Ngày đã nhận diện ở tương lai')) notices.push('Ngày ở tương lai: kiểm tra trước khi lưu.');
        else if (warning.startsWith('Mô tả còn số chưa diễn giải')) notices.push('Mô tả còn số chưa được hiểu; hãy kiểm tra.');
        else if (warning.startsWith('Mô tả sau xử lý đang trống')) notices.push('Mô tả đang trống (không bắt buộc).');
        else notices.push(warning); // Never hide an unfamiliar warning.
      }
      for (const notice of notices) {
        const item = document.createElement('li'); item.textContent = notice; needed.append(item);
      }
      attention.hidden = notices.length === 0;
      const labels = {amount: 'Số tiền (VND)', date: data.date_defaulted ? 'Ngày (mặc định hôm nay)' : 'Ngày giao dịch',
        kind: 'Loại', description: 'Mô tả sau xử lý'};
      for (const name of ['amount', 'date', 'kind', 'description']) {
        const row = document.createElement('div');
        const term = document.createElement('dt'); term.textContent = labels[name];
        const value = document.createElement('dd');
        value.textContent = name === 'kind' ? ({income: 'Thu nhập', expense: 'Chi tiêu'}[data.fields.kind] || 'Bạn cần chọn')
          : name === 'amount' ? globalThis.SoThuChiMoney.formatVnd(data.fields.amount)
          : name === 'date' ? data.fields.date.split('-').reverse().join('/') : data.fields[name] || '(Trống)';
        row.append(term, value); details.append(row);
      }
      for (const warning of data.warnings) {
        const item = document.createElement('li'); item.textContent = warning; warnings.append(item);
      }
      preview.hidden = false;
      detailResult.hidden = false;
      if (hasData()) {
        pending = data; confirmation.hidden = false;
        message('Đã phân tích, chưa thay đổi biểu mẫu. Xem kết quả và xác nhận nếu muốn thay thế.');
      } else fill(data);
    } catch (_) {
      if (current === generation) message('Nhập nhanh tạm không sẵn sàng hoặc phiên đã hết hạn. Dữ liệu biểu mẫu được giữ; bạn vẫn có thể nhập thủ công.', true);
    } finally {
      if (current === generation) button.disabled = false;
    }
  });
})();
