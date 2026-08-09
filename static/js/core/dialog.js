



















(function () {
  const Core = (window.GravewrightCore = window.GravewrightCore || {});


  const DEFAULTS = {
    confirmText: "OK",
    cancelText: "Cancel",
    title: "",
  };

  let host = null;
  let active = null;

  function readDefaults() {
    const data = document.body?.dataset || {};
    return {
      confirmText: data.dialogConfirmLabel || DEFAULTS.confirmText,
      cancelText: data.dialogCancelLabel || DEFAULTS.cancelText,
      title: DEFAULTS.title,
    };
  }

  function build() {
    if (host) return host;
    host = document.createElement("div");
    host.className = "gw-dialog-backdrop";
    host.hidden = true;
    host.setAttribute("role", "presentation");
    host.innerHTML = `
      <section class="gw-dialog" role="alertdialog" aria-modal="true"
               aria-labelledby="gw-dialog-title" aria-describedby="gw-dialog-message">
        <h2 class="gw-dialog__title" id="gw-dialog-title"></h2>
        <p class="gw-dialog__message" id="gw-dialog-message"></p>
        <div class="gw-dialog__actions">
          <button class="gw-dialog__btn gw-dialog__btn--ghost" type="button" data-gw-dialog-cancel></button>
          <button class="gw-dialog__btn gw-dialog__btn--primary" type="button" data-gw-dialog-confirm></button>
        </div>
      </section>`;
    document.body.appendChild(host);

    host.addEventListener("click", (event) => {
      if (event.target === host) settle(false);
      if (event.target.closest("[data-gw-dialog-cancel]")) settle(false);
      if (event.target.closest("[data-gw-dialog-confirm]")) settle(true);
    });
    return host;
  }

  function settle(result) {
    if (!active) return;
    const { resolve, returnFocus } = active;
    active = null;
    host.hidden = true;
    document.removeEventListener("keydown", onKeydown, true);


    if (returnFocus && document.contains(returnFocus)) returnFocus.focus();
    resolve(result);
  }

  function onKeydown(event) {
    if (!active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      settle(false);
      return;
    }
    if (event.key !== "Tab") return;


    const focusables = [...host.querySelectorAll("button:not([hidden])")];
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function open(message, options, { withCancel }) {
    build();


    if (active) settle(false);

    const defaults = readDefaults();
    const opts = { ...defaults, ...(options || {}) };

    const titleEl = host.querySelector(".gw-dialog__title");
    const messageEl = host.querySelector(".gw-dialog__message");
    const cancelEl = host.querySelector("[data-gw-dialog-cancel]");
    const confirmEl = host.querySelector("[data-gw-dialog-confirm]");

    titleEl.textContent = opts.title || "";
    titleEl.hidden = !opts.title;


    messageEl.textContent = message == null ? "" : String(message);
    confirmEl.textContent = opts.confirmText;
    cancelEl.textContent = opts.cancelText;
    cancelEl.hidden = !withCancel;

    host.querySelector(".gw-dialog").classList.toggle(
      "gw-dialog--danger",
      opts.variant === "danger",
    );

    host.hidden = false;
    document.addEventListener("keydown", onKeydown, true);

    return new Promise((resolve) => {
      active = { resolve, returnFocus: document.activeElement };
      confirmEl.focus();
    });
  }

  Core.dialog = {
    alert: (message, options) => open(message, options, { withCancel: false }),
    confirm: (message, options) => open(message, options, { withCancel: true }),
  };
})();
