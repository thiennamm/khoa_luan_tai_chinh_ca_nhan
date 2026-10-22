// Chỉ hỗ trợ chọn nhanh; máy chủ luôn kiểm tra chủ sở hữu và loại danh mục.
const kindInput = document.getElementById('id_kind');
const categoryInput = document.getElementById('id_category');
const kindsNode = document.getElementById('category-kinds');
if (kindInput && categoryInput && kindsNode) {
  const kinds = JSON.parse(kindsNode.textContent);
  function filterCategories() {
    for (const option of categoryInput.options) {
      const mismatch = Boolean(option.value) && kinds[option.value] !== kindInput.value;
      option.hidden = mismatch;
      option.disabled = mismatch;
    }
    if (categoryInput.selectedOptions[0]?.disabled) categoryInput.value = '';
  }
  kindInput.addEventListener('change', filterCategories);
  filterCategories();
}

// Chỉ nút Áp dụng mới thay đổi trường danh mục; không submit hoặc tự học.
(() => {
  const panel = document.getElementById('classification-suggestion');
  const description = document.getElementById('id_description');
  const modeInput = document.getElementById('suggestion-mode');
  if (!panel || !description || !kindInput || !categoryInput || !modeInput) return;
  const button = document.getElementById('suggest-category');
  const result = document.getElementById('suggestion-result');
  const actions = document.getElementById('suggestion-actions');
  const choices = document.getElementById('suggestion-category');
  const apply = document.getElementById('apply-suggestion');
  const token = document.querySelector('#transaction-form [name=csrfmiddlewaretoken]');
  const receiptInput = document.getElementById('suggestion-id');
  const form = document.getElementById('transaction-form');
  let applying = false;
  let generation = 0;
  let offered = new Set();
  let snapshot = null;

  function clear() {
    const oldReceipt = receiptInput.value;
    receiptInput.value = '';
    if (oldReceipt) {
      fetch(panel.dataset.actionUrl, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': token.value, 'Accept': 'application/json'},
        body: new URLSearchParams({action: 'revoke', suggestion_id: oldReceipt}),
      }).catch(() => {}); // Backend still checks current input and expiry if offline.
    }
    generation += 1;
    offered = new Set();
    snapshot = null;
    choices.replaceChildren();
    actions.hidden = true;
    apply.disabled = true;
    button.disabled = false;
    result.textContent = '';
  }
  description.addEventListener('input', clear);
  kindInput.addEventListener('change', clear);
  modeInput.addEventListener('change', clear);
  form.addEventListener('submit', event => {
    if (applying) {
      event.preventDefault();
      result.textContent = 'Đang xác nhận áp dụng. Vui lòng chờ rồi bấm Lưu giao dịch.';
    }
  });
  choices.addEventListener('change', () => { apply.disabled = !offered.has(choices.value); });

  button.addEventListener('click', async () => {
    clear();
    if (description.value.length > 500) {
      result.textContent = 'Mô tả tối đa 500 ký tự.';
      return;
    }
    const current = generation;
    snapshot = {description: description.value, kind: kindInput.value, mode: modeInput.value};
    button.disabled = true;
    result.textContent = 'Đang tìm gợi ý…';
    try {
      const response = await fetch(panel.dataset.url, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': token.value, 'Accept': 'application/json'},
        body: new URLSearchParams({...snapshot, transaction_id: panel.dataset.transactionId || ''}),
      });
      if (current !== generation) return;
      if (response.redirected) throw new Error('Phiên đăng nhập đã hết hạn.');
      const data = await response.json();
      if (current !== generation) return;
      if (!snapshot || snapshot.description !== description.value || snapshot.kind !== kindInput.value
          || snapshot.mode !== modeInput.value) { clear(); return; }
      if (!response.ok && !['unavailable', 'invalid'].includes(data.status)) throw new Error('Gợi ý không sẵn sàng.');
      receiptInput.value = data.suggestion_id || '';
      result.textContent = (data.label ? `Nhãn dự đoán: ${data.label_display} (${data.label}). ` : '') + data.message;
      if (data.status !== 'suggestion' || !data.categories?.length) return;
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '— Chọn danh mục để áp dụng —';
      choices.append(placeholder);
      for (const category of data.categories) {
        const id = String(category.id);
        // Chỉ hiển thị ID thực có trong biểu mẫu của người dùng và đúng loại.
        if (![...categoryInput.options].some(option => option.value === id && !option.disabled)) continue;
        const option = document.createElement('option');
        option.value = id;
        option.textContent = category.name;
        choices.append(option);
        offered.add(id);
      }
      actions.hidden = offered.size === 0;
    } catch (_) {
      if (current === generation) result.textContent = 'Gợi ý tạm không sẵn sàng hoặc phiên đăng nhập hết hạn. Bạn vẫn có thể nhập thủ công; đăng nhập lại nếu cần.';
    } finally {
      if (current === generation) button.disabled = false;
    }
  });
  apply.addEventListener('click', async () => {
    if (!snapshot || snapshot.description !== description.value || snapshot.kind !== kindInput.value
        || snapshot.mode !== modeInput.value
        || !offered.has(choices.value) || !receiptInput.value || applying) return;
    const option = [...categoryInput.options].find(option => option.value === choices.value && !option.disabled);
    if (!option) return;
    const current = generation;
    const chosen = option.value;
    applying = true;
    apply.disabled = true;
    try {
      const response = await fetch(panel.dataset.actionUrl, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': token.value, 'Accept': 'application/json'},
        body: new URLSearchParams({...snapshot, transaction_id: panel.dataset.transactionId || '',
          action: 'apply', suggestion_id: receiptInput.value, category: chosen}),
      });
      const data = await response.json();
      if (current !== generation) return;
      if (response.redirected || !response.ok || data.status !== 'applied' || String(data.category_id) !== chosen) {
        throw new Error('Invalid receipt');
      }
      if (snapshot.description !== description.value || snapshot.kind !== kindInput.value
          || snapshot.mode !== modeInput.value) { clear(); return; }
      categoryInput.value = chosen;
      categoryInput.dispatchEvent(new Event('change', {bubbles: true}));
      result.textContent = 'Đã áp dụng danh mục vào biểu mẫu. Kiểm tra các thông tin và bấm Lưu giao dịch khi bạn muốn lưu.';
    } catch (_) {
      if (current === generation) {
        result.textContent = 'Chưa xác nhận được áp dụng. Hãy yêu cầu gợi ý lại hoặc chọn danh mục thủ công.';
        receiptInput.value = '';
      }
    } finally {
      applying = false;
    }
  });
})();
