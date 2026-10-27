// Chỉ phản hồi giao diện khi trình duyệt đã chấp nhận gửi form.
// Không đổi giá trị, vô hiệu trường hoặc thay cơ chế xác nhận của máy chủ.
(() => {
  // Shared by quick entry and ML. Abort means acknowledgement is unknown, never
  // permission to retry a financial POST. No request body is persisted or logged.
  async function requestJson(url, options, timeout = 20000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(url, {...options, signal: controller.signal});
      if (response.redirected) throw new Error('Unconfirmed response');
      return {response, data: await response.json()};
    } finally { clearTimeout(timer); }
  }
  function announce(node, text, error = false) {
    node.setAttribute('role', 'status');
    node.setAttribute('aria-live', 'polite');
    node.setAttribute('aria-atomic', 'true');
    node.setAttribute('data-state', error ? 'error' : 'status');
    if (node.textContent !== text) node.textContent = text;
    if (error) { node.tabIndex = -1; node.focus(); }
  }
  globalThis.SoThuChiInteraction = {requestJson, announce};

  const summary = document.querySelector('[data-error-summary]');
  const pending = new Map();
  document.addEventListener('submit', event => {
    const form = event.target;
    if (event.defaultPrevented || form.method.toLowerCase() !== 'post') return;
    if (pending.has(form)) {
      event.preventDefault();
      return;
    }
    const status = document.createElement('p');
    status.className = 'submit-feedback';
    status.setAttribute('role', 'status');
    status.textContent = (event.submitter?.dataset.pendingLabel || form.dataset.pendingLabel
      || 'Đang xử lý…') + ' Vui lòng chờ.';
    const guidance = document.createElement('p');
    guidance.className = 'submit-feedback-help';
    guidance.textContent = 'Nếu kết nối gián đoạn, chưa xác nhận được kết quả. Kiểm tra danh sách và trạng thái thao tác trước khi gửi lại; không bấm liên tục.';
    const buttons = [...form.querySelectorAll('button[type="submit"], input[type="submit"]')]
      .map(button => [button, button.getAttribute('aria-disabled')]);
    for (const [button] of buttons) button.setAttribute('aria-disabled', 'true');
    const previousBusy = form.getAttribute('aria-busy');
    form.setAttribute('aria-busy', 'true');
    form.appendChild(status);
    form.appendChild(guidance);
    pending.set(form, { status, guidance, previousBusy, buttons });
  });
  // Trở lại bằng Back/Forward phải thao tác lại được, kể cả trang từ bfcache.
  window.addEventListener('pageshow', () => {
    for (const [form, { status, guidance, previousBusy, buttons }] of pending) {
      status.remove();
      guidance.remove();
      for (const [button, previous] of buttons) {
        if (previous === null) button.removeAttribute('aria-disabled');
        else button.setAttribute('aria-disabled', previous);
      }
      if (previousBusy === null) form.removeAttribute('aria-busy');
      else form.setAttribute('aria-busy', previousBusy);
    }
    pending.clear();
    // Run after navigation/hash/autofocus restoration, rather than losing focus
    // back to #main when a POST followed the skip-navigation link.
    if (summary) summary.focus();
  });
})();
