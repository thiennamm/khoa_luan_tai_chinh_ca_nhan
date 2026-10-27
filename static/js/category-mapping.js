/* Display-only enhancement. Server repeats ownership/type filtering. */
(() => {
  'use strict';
  const data = document.getElementById('category-mapping-peers');
  const kind = document.getElementById('id_kind');
  const label = document.getElementById('id_canonical_label');
  const notice = document.getElementById('mapping-peers');
  if (!data || !kind || !label || !notice) return;
  let peers;
  try { peers = JSON.parse(data.textContent); } catch { return; }
  function update() {
    const names = peers[kind.value]?.[label.value] || [];
    notice.textContent = names.length ? 'Nhãn này đang liên kết với các danh mục: ' + names.join(', ') : '';
    notice.hidden = !names.length;
  }
  kind.addEventListener('change', update);
  label.addEventListener('change', update);
  update();
})();
