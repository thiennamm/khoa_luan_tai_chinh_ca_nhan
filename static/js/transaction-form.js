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
