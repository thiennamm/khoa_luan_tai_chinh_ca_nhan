// Chỉ phản hồi giao diện khi trình duyệt đã chấp nhận gửi form.
// Không đổi giá trị, vô hiệu trường hoặc thay cơ chế xác nhận của máy chủ.
(() => {
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
    status.textContent = 'Đang xử lý… Vui lòng chờ.';
    const previousBusy = form.getAttribute('aria-busy');
    form.setAttribute('aria-busy', 'true');
    form.appendChild(status);
    pending.set(form, { status, previousBusy });
  });
  // Trở lại bằng Back/Forward phải thao tác lại được, kể cả trang từ bfcache.
  window.addEventListener('pageshow', () => {
    for (const [form, { status, previousBusy }] of pending) {
      status.remove();
      if (previousBusy === null) form.removeAttribute('aria-busy');
      else form.setAttribute('aria-busy', previousBusy);
    }
    pending.clear();
  });
})();
