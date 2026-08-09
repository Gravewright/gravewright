(() => {
  "use strict";

  const root = document.querySelector("[data-inside-join-code]");
  if (!root) return;

  const notice = root.querySelector("[data-inside-join-code-notice]");
  const form = root.querySelector("[data-inside-join-code-form]");
  const input = root.querySelector("[data-inside-join-code-input]");

  function errorMessage(key) {
    const values = {
      "campaign.join_code.errors.unavailable": document.body.dataset.joinCodeUnavailable,
      "http.errors.rate_limited": document.body.dataset.joinCodeRateLimited,
      "http.errors.network": document.body.dataset.joinCodeNetwork,
      "auth.errors.session_expired": document.body.dataset.joinCodeSession,
    };
    return values[key] || document.body.dataset.joinCodeRequestError || key || "";
  }

  function showError(key) {
    notice.textContent = errorMessage(key);
    notice.hidden = false;
    notice.classList.add("notice--danger");
    notice.setAttribute("role", "alert");
    notice.focus();
  }

  function setBusy(busy) {
    root.setAttribute("aria-busy", String(busy));
    root.querySelectorAll("button, input").forEach((element) => {
      element.disabled = busy;
    });
  }

  async function redeem(code) {
    const http = window.GravewrightCore?.http;
    if (!http) {
      showError("http.errors.network");
      return;
    }


    const data = new URLSearchParams();
    data.set("code", code || "");
    setBusy(true);
    notice.hidden = true;
    const result = await http.postForm("/campaigns/join-code/redeem", data, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    setBusy(false);
    if (!result.ok || result.data?.ok === false) {
      showError(result.errorKey || result.data?.error_key);
      return;
    }
    window.location.assign(result.data.redirect || "/inside");
  }

  input.addEventListener("input", () => {
    const caretAtEnd = input.selectionStart === input.value.length;
    const compact = input.value.toUpperCase().replace(/[\s-]+/g, "").slice(0, 12);
    input.value = compact.replace(/(.{4})(?=.)/g, "$1-");
    if (caretAtEnd) input.setSelectionRange(input.value.length, input.value.length);
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    redeem(input.value);
  });

  root.querySelector("[data-inside-redeem-pending]")?.addEventListener("click", () => redeem(""));
})();
