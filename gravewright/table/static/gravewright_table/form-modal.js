import { mountModal } from './modal.js';
import { createTranslator } from '/static/gravewright_modules/i18n.js';

const translator = createTranslator();
export const modalText = (en, pt) => translator.has(en) ? translator.t(en) : translator.locale.toLowerCase().startsWith('pt') ? pt ?? en : en;

export function openFormModal(title, fields, save, {key = 'form', submitLabel} = {}) {
  const modal = document.createElement('section');
  modal.className = 'table-form-modal';
  modal.dataset.movable = '';
  modal.dataset.windowKey = key;
  const titleId = 'modal-title-' + crypto.randomUUID();
  modal.setAttribute('aria-labelledby', titleId);
  modal.innerHTML = '<form><header data-move-handle><strong></strong><button type="button" data-close>×</button></header><div class="table-form-modal__body"><p role="alert" hidden></p><div data-fields></div></div><footer><button type="button" data-cancel></button><button type="submit"></button></footer></form>';
  modal.querySelector('strong').id = titleId;
  modal.querySelector('strong').textContent = title;
  const close = modal.querySelector('[data-close]'), cancel = modal.querySelector('[data-cancel]');
  close.setAttribute('aria-label', modalText('Close', 'Fechar'));
  cancel.textContent = modalText('Cancel', 'Cancelar');
  const submit = modal.querySelector('[type=submit]');
  submit.textContent = submitLabel || modalText('Save', 'Salvar');
  let saving = false;
  close.onclick = cancel.onclick = () => { if (!saving) modal.close(); };
  for (const field of fields) {
    const label = document.createElement('label'), caption = document.createElement('span');
    caption.textContent = field.label;
    const input = document.createElement(field.options ? 'select' : field.multiline ? 'textarea' : 'input');
    input.name = field.name;
    if (field.options) for (const option of field.options) input.add(new Option(option.label, option.value));
    else input.type = field.type || 'text';
    input.value = field.value ?? '';
    if (field.type === 'checkbox') input.checked = !!field.value;
    input.required = !!field.required;
    label.append(caption, input); modal.querySelector('[data-fields]').append(label);
  }
  modal.querySelector('form').onsubmit = async event => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    submit.disabled = close.disabled = cancel.disabled = true;
    const alert = modal.querySelector('[role=alert]'); alert.hidden = true;
    try { await save(event.currentTarget); modal.close(); }
    catch (error) { alert.textContent = error.message; alert.hidden = false; }
    finally { saving = false; submit.disabled = close.disabled = cancel.disabled = false; }
  };
  return mountModal(modal, {canClose: () => !saving});
}

export function mountFormTabs(form) {
  const tabs = [...form.querySelectorAll('[data-modal-tab]')];
  const activate = selected => {
    if (!selected) return;
    for (const tab of tabs) { const on = tab === selected; tab.setAttribute('aria-selected', String(on)); tab.tabIndex = on ? 0 : -1; }
    for (const panel of form.querySelectorAll('[data-modal-panel]')) panel.hidden = panel.dataset.modalPanel !== selected.dataset.modalTab;
  };
  for (const tab of tabs) {
    if (tab.dataset.labelEn) tab.textContent = modalText(tab.dataset.labelEn, tab.dataset.labelPt);
    tab.onclick = () => activate(tab);
    tab.onkeydown = event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      activate(tabs[index]); tabs[index].focus();
    };
    const panel = form.querySelector(`[data-modal-panel="${tab.dataset.modalTab}"]`);
    tab.id = 'modal-tab-' + crypto.randomUUID(); panel.id = tab.id + '-panel';
    tab.setAttribute('aria-controls', panel.id); panel.setAttribute('aria-labelledby', tab.id);
  }
  form.addEventListener('invalid', event => {
    if (event.target !== form.querySelector('input:invalid,select:invalid,textarea:invalid')) return;
    const panel = event.target.closest('[data-modal-panel]');
    if (panel) activate(tabs.find(tab => tab.dataset.modalTab === panel.dataset.modalPanel));
  }, true);
  if (tabs.length) activate(tabs[0]);
}
