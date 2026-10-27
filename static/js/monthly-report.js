// Print only after an explicit user action; no data request, PDF upload or save.
(() => {
  const button = document.getElementById('print-report');
  if (!button) return;
  button.hidden = false;
  button.addEventListener('click', () => window.print());
})();
