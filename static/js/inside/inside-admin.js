




(function () {





  document.addEventListener("submit", (event) => {
    const form = event.target.closest("form[data-confirm]");
    if (!form) return;
    if (form.dataset.confirmed === "1") {
      delete form.dataset.confirmed;
      return;
    }

    event.preventDefault();
    window.GravewrightCore.dialog
      .confirm(form.dataset.confirm, { variant: "danger" })
      .then((ok) => {
        if (!ok) return;
        form.dataset.confirmed = "1";
        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
  });

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-reset-toggle]");
    if (!toggle) return;
    const form = document.getElementById(toggle.dataset.resetToggle);
    if (form) form.hidden = !form.hidden;
  });
})();
