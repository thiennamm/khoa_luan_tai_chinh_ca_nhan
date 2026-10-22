// Máy chủ luôn kiểm lại chế độ; không tự lọc hoặc sửa dữ liệu.
(() => {
  const form = document.getElementById('transaction-filters');
  if (!form) return;
  const period = form.querySelector('[name=period]');
  function update() {
    for (const name of ['month', 'start', 'end']) {
      const field = form.querySelector(`[data-filter-field="${name}"]`);
      const active = period.value === (name === 'month' ? 'month' : 'range');
      field.hidden = !active;
      field.querySelector('input').disabled = !active;
    }
  }
  period.addEventListener('change', update);
  update();
})();
