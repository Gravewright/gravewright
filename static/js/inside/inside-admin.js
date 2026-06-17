




(function () {
  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-confirm]");
    if (form && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
    }
  });

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-reset-toggle]");
    if (!toggle) return;
    const form = document.getElementById(toggle.dataset.resetToggle);
    if (form) form.hidden = !form.hidden;
  });
})();
