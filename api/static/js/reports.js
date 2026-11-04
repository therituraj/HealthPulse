// Show times in the visitor's own timezone and confirm destructive forms.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('time.js-local').forEach(function (el) {
    var d = new Date(el.getAttribute('datetime'));
    if (isNaN(d)) return;
    el.textContent = el.dataset.format === 'date'
      ? d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
      : d.toLocaleString(undefined, { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  });
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });
});
