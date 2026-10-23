import { fieldReference } from './controller.js';

const TOKEN_VALUES = [
  ["", "— none —"], ["bar1Value", "Bar 1 · Current"], ["bar1Max", "Bar 1 · Maximum"],
  ["bar2Value", "Bar 2 · Current"], ["bar2Max", "Bar 2 · Maximum"],
  ["initiative", "Initiative"], ["defense", "Defense"],
];
const ROLL_PRESETS = [
  ["d20", "D20 roll", "1d20 + @value"],
  ["highest", "Keep highest", "2d20kh1 + @value"],
  ["lowest", "Keep lowest", "2d20kl1 + @value"],
  ["2d6", "2d6 roll", "2d6 + @value"],
  ["exploding", "Exploding die", "1d6!"],
  ["fudge", "4dF roll", "4dF + @value"],
];

/** Configure field behavior in a draft; only Save changes the character sheet. */
export function createFieldActionsEditor({ root, hostWindow, controller, t, onClose }) {
  let active, destroyed = false, opening = 0;
  const canConfigure = (view, name) => !!view?.canConfigureFieldActions && !!view.fields?.[name];
  async function open(fieldName) {
    if (destroyed || typeof fieldName !== "string" || !canConfigure(controller.view, fieldName)) return null;
    if (active) {
      active.modal.focus({ preventScroll: true });
      return active.modal;
    }
    const generation = ++opening;
    const openingSource = JSON.stringify(controller.view.currentSource);
    const { mountModal } = await import("/static/gravewright_table/modal.js");
    if (destroyed || generation !== opening || openingSource !== JSON.stringify(controller.view.currentSource)
        || !canConfigure(controller.view, fieldName)) return null;
    const document = root.ownerDocument || hostWindow.ownerDocument;
    if (!document.querySelector("link[data-pdf-field-actions-style]")) {
      const stylesheet = document.createElement("link");
      stylesheet.rel = "stylesheet";
      stylesheet.href = new URL("./field-actions.css", import.meta.url).href;
      stylesheet.dataset.pdfFieldActionsStyle = "";
      document.head.append(stylesheet);
    }
    const view = controller.view;
    const spec = view.fields[fieldName];
    const info = view.fieldIndex?.get(fieldName);
    const fieldLabel = spec.label || info?.manual?.name || fieldName;
    const source = view.currentSource ? `${view.currentSource.kind}:${view.currentSource.id}` : "";
    const configured = view.fieldActions?.[fieldName]?.roll || view.fieldActions?.[fieldName]
      || view.actor?.data?.pdf?.fieldActions?.find((entry) => entry.source === source && entry.field === fieldName)?.roll;
    const abort = new AbortController();
    const { signal } = abort;
    let busy = "";
    function node(tag, attributes = {}, text) {
      const element = document.createElement(tag);
      for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
      if (text !== undefined) element.textContent = text;
      return element;
    }
    function label(text, input) {
      const element = node("label");
      element.append(node("span", {}, t(text)), input);
      return element;
    }
    const modal = node("section", { class: "table-form-modal pdf-field-actions", "data-pdf-field-actions": fieldName });
    const form = node("form");
    const header = node("header");
    const title = node("strong", { id: `pdf-field-actions-${crypto.randomUUID()}` }, t("Field actions"));
    modal.setAttribute("aria-labelledby", title.id);
    const close = node("button", { type: "button", "data-pdf-action-close": "" }, t("Close"));
    header.append(title, close);
    const body = node("div", { class: "table-form-modal__body pdf-field-actions__body" });
    const fieldTitle = node("strong", { class: "pdf-field-actions__field", translate: "no" }, fieldLabel);
    body.append(fieldTitle);
    const bar = node("select", { "data-pdf-action-bar": "" });
    for (const [value, text] of TOKEN_VALUES) bar.append(node("option", { value }, t(text)));
    bar.value = TOKEN_VALUES.find(([slot]) => slot && view.actor?.data?.token?.bars?.[slot] === fieldName)?.[0] || "";
    const barDisabled = spec.type === "boolean" || !!spec.multiline || !!info?.readOnly;
    bar.disabled = barDisabled;
    const barHint = node("p", { class: "pdf-field-actions__hint" }, t("Choose which token value this field controls."));
    body.append(label("Token value", bar), barHint);
    const formula = node("input", {
      type: "text", maxlength: "512", "data-pdf-action-formula": "", autocomplete: "off", spellcheck: "false", translate: "no",
    });
    formula.value = configured?.formula || "";
    const rollLabel = node("input", { type: "text", maxlength: "48", "data-pdf-action-label": "", translate: "no" });
    rollLabel.value = configured?.label || "";
    const hint = node("p", { class: "pdf-field-actions__hint" }, t("Use @value for this field. Leave the formula empty to disable rolling."));
    body.append(label("Roll formula", formula), label("Roll label", rollLabel), hint);
    const calculation = node('input', { type: 'text', maxlength: '512', 'data-pdf-action-calculation': '',
      autocomplete: 'off', spellcheck: 'false', translate: 'no' });
    calculation.value = view.calculatedFields?.[fieldName] || '';
    calculation.disabled = barDisabled;
    body.append(label('Calculated value formula', calculation), node('p', { class: 'pdf-field-actions__hint' },
      t('Leave empty for an editable field. Calculated values update automatically and cannot roll dice.')));
    const references = node('select', { 'data-pdf-action-reference': '' });
    for (const binding of view.referenceFields || []) references.append(node('option', { value: binding.field }, binding.name || binding.field));
    references.setAttribute('translate', 'no');
    const insertion = node('div', { class: 'pdf-field-actions__references' });
    insertion.append(label('Reference field', references));
    function insertReference(input) {
      if (busy || input.disabled || !references.value) return;
      const position = input.selectionStart ?? input.value.length, end = input.selectionEnd ?? position;
      const before = input.value.slice(0, position).trimEnd();
      const prefix = before && !/[+*/,(\-]$/.test(before) ? ' + ' : '';
      input.setRangeText(prefix + fieldReference(references.value), position, end, 'end');
      input.focus();
    }
    for (const [attribute, text, input] of [['data-pdf-action-insert-reference', 'Insert in roll', formula],
      ['data-pdf-action-insert-calculation', 'Insert in calculation', calculation]]) {
      const button = node('button', { type: 'button', [attribute]: '' }, t(text));
      button.disabled = input === calculation && barDisabled;
      button.addEventListener('click', () => insertReference(input), { signal });
      insertion.append(button);
    }
    body.append(insertion);
    const presets = node("fieldset", { class: "pdf-field-actions__presets" });
    presets.append(node("legend", {}, t("Roll presets")));
    const presetButtons = node("div", { class: "pdf-field-actions__preset-buttons" });
    for (const [id, text, expression] of ROLL_PRESETS) {
      const button = node("button", { type: "button", "data-pdf-action-preset": id }, t(text));
      button.title = expression;
      button.addEventListener("click", () => {
        if (busy) return;
        formula.value = expression;
        if (!rollLabel.value.trim()) rollLabel.value = t(text).slice(0, 48);
        formula.focus();
      }, { signal });
      presetButtons.append(button);
    }
    presets.append(presetButtons);
    body.append(presets);
    const issue = node("p", { role: "alert", class: "pdf-field-actions__error", "data-pdf-action-error": "", hidden: "" });
    body.append(issue);
    const footer = node("footer");
    const cancel = node("button", { type: "button", "data-pdf-action-cancel": "" }, t("Cancel"));
    const roll = node("button", { type: "button", "data-pdf-action-roll": "" }, t("Roll saved action"));
    roll.hidden = !configured?.formula;
    roll.disabled = !configured?.formula;
    const save = node("button", { type: "submit", "data-pdf-action-save": "" }, t("Save"));
    footer.append(cancel, roll, save);
    form.append(header, body, footer);
    modal.append(form);
    function setBusy(value) {
      busy = value;
      if (value) modal.setAttribute("aria-busy", "true");
      else modal.removeAttribute("aria-busy");
      for (const control of modal.querySelectorAll("button,input,select")) control.disabled = !!value;
      if (value === "roll") {
        close.disabled = false;
        cancel.disabled = false;
      }
      if (!value) {
        bar.disabled = barDisabled;
        calculation.disabled = barDisabled;
        modal.querySelector('[data-pdf-action-insert-calculation]').disabled = barDisabled;
        roll.disabled = !configured?.formula;
      }
    }
    function currentFieldAvailable() {
      if (JSON.stringify(controller.view.currentSource) === openingSource
          && canConfigure(controller.view, fieldName)) return true;
      issue.textContent = t("This field is no longer available. Reopen the character sheet.");
      issue.hidden = false;
      return false;
    }
    roll.addEventListener("click", async () => {
      if (busy || destroyed || !configured?.formula) return;
      if (!currentFieldAvailable()) return;
      setBusy("roll");
      issue.hidden = true;
      try {
        await controller.call("rollField", fieldName);
      } catch (error) {
        if (!destroyed && !signal.aborted) {
          issue.textContent = t(error.message || "Could not roll this field. Try again.");
          issue.hidden = false;
        }
      } finally {
        if (!destroyed && !signal.aborted) setBusy("");
      }
    }, { signal });
    function closeDraft() { if (busy !== "save") modal.close(); }
    for (const button of [close, cancel]) button.addEventListener("click", closeDraft, { signal });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (busy || destroyed || !form.reportValidity()) return;
      if (!currentFieldAvailable()) return;
      setBusy("save");
      issue.hidden = true;
      try {
        const result = await controller.call("configureFieldAction", fieldName, {
          bar: bar.value, formula: formula.value.trim(), label: rollLabel.value.trim(), calculation: calculation.value.trim(),
        });
        if (result === false || result?.error) throw new Error(result?.error || t("Could not save this field action. Check the formula and try again."));
        if (!destroyed && !signal.aborted) modal.close(true);
      } catch (error) {
        if (!destroyed && !signal.aborted) {
          issue.textContent = t(error.message || "Could not save this field action. Check the formula and try again.");
          issue.hidden = false;
        }
      } finally {
        if (!destroyed && !signal.aborted) {
          setBusy("");
        }
      }
    }, { signal });
    active = { modal, abort };
    modal.addEventListener("close", () => {
      abort.abort();
      if (active?.modal === modal) active = undefined;
      onClose?.(fieldName);
    }, { once: true });
    mountModal(modal, { nested: true, canClose: () => busy !== "save" });
    (barDisabled ? formula : bar).focus({ preventScroll: true });
    return modal;
  }
  return {
    open,
    destroy() {
      destroyed = true;
      ++opening;
      active?.modal.close(true);
      active?.abort.abort();
      active = undefined;
    },
  };
}
