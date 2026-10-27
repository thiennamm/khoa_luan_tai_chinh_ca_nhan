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
  let applyVersion = 0;
  const interaction = globalThis.SoThuChiInteraction;
  function message(text, error = false) { interaction.announce(result, text, error); }

  function clear() {
    const oldReceipt = receiptInput.value;
    receiptInput.value = '';
    if (oldReceipt) {
      interaction.requestJson(panel.dataset.actionUrl, {
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
    message('');
  }
  description.addEventListener('input', clear);
  kindInput.addEventListener('change', clear);
  modeInput.addEventListener('change', clear);
  form.addEventListener('submit', event => {
    if (applying) {
      event.preventDefault();
      message('Đang xác nhận áp dụng. Vui lòng chờ rồi bấm Lưu giao dịch.');
    }
  });
  choices.addEventListener('change', () => { apply.disabled = applying || !offered.has(choices.value); });

  button.addEventListener('click', async () => {
    if (button.disabled || applying) return;
    clear();
    if (description.value.length > 500) {
      message('Mô tả tối đa 500 ký tự.', true);
      return;
    }
    const current = generation;
    snapshot = {description: description.value, kind: kindInput.value, mode: modeInput.value};
    button.disabled = true;
    message('Đang lấy gợi ý…');
    try {
      const {response, data} = await interaction.requestJson(panel.dataset.url, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': token.value, 'Accept': 'application/json'},
        body: new URLSearchParams({...snapshot, transaction_id: panel.dataset.transactionId || ''}),
      });
      if (current !== generation) return;
      if (!snapshot || snapshot.description !== description.value || snapshot.kind !== kindInput.value
          || snapshot.mode !== modeInput.value) { clear(); return; }
      if (!response.ok && !['unavailable', 'invalid'].includes(data.status)) throw new Error('Gợi ý không sẵn sàng.');
      receiptInput.value = data.suggestion_id || '';
      message((data.label ? `Nhãn dự đoán: ${data.label_display} (${data.label}). ` : '') + data.message,
        !response.ok);
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
      if (current === generation) message('Chưa nhận được kết quả gợi ý do kết nối, thời gian chờ hoặc phiên đăng nhập. Bạn vẫn có thể nhập và lưu giao dịch thủ công; không tự đổi mô hình.', true);
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
    const version = ++applyVersion;
    apply.disabled = true;
    message('Đang xác nhận áp dụng…');
    try {
      const {response, data} = await interaction.requestJson(panel.dataset.actionUrl, {
        method: 'POST', credentials: 'same-origin', mode: 'same-origin',
        headers: {'X-CSRFToken': token.value, 'Accept': 'application/json'},
        body: new URLSearchParams({...snapshot, transaction_id: panel.dataset.transactionId || '',
          action: 'apply', suggestion_id: receiptInput.value, category: chosen}),
      });
      if (current !== generation) return;
      if (response.redirected || !response.ok || data.status !== 'applied' || String(data.category_id) !== chosen) {
        throw new Error('Invalid receipt');
      }
      if (snapshot.description !== description.value || snapshot.kind !== kindInput.value
          || snapshot.mode !== modeInput.value) { clear(); return; }
      categoryInput.value = chosen;
      categoryInput.dispatchEvent(new Event('change', {bubbles: true}));
      message('Đã áp dụng danh mục vào biểu mẫu. Kiểm tra các thông tin và bấm Lưu giao dịch khi bạn muốn lưu.');
    } catch (_) {
      if (current === generation) {
        clear();
        message('Chưa xác nhận được áp dụng. Hãy yêu cầu gợi ý lại hoặc chọn danh mục thủ công. Thao tác Áp dụng không tự lưu giao dịch.', true);
      }
    } finally {
      if (version === applyVersion) applying = false;
    }
  });
  window.addEventListener('pageshow', event => {
    if (!event.persisted) return;
    applyVersion += 1; applying = false; clear();
    message('Đã trở lại biểu mẫu. Kiểm tra dữ liệu và yêu cầu gợi ý mới nếu cần.');
  });
})();
