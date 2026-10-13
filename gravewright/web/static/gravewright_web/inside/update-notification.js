import { HttpClient } from '/static/gravewright_modules/http-client.js';

const http = new HttpClient();
const POLL_MS = 5 * 60 * 1000;
let root, latest, open = false, lastRequest = 0, pending, controller, timer, generation = 0;
let updating = false;

function text(selector, value) {
  const element = root?.querySelector(selector);
  if (element && element.textContent !== value) element.textContent = value;
}

function render() {
  if (!root) return;
  const value = latest ?? {status: 'checking'};
  const available = value.status === 'available' && value.available !== false && !!value.availableVersion;
  const labels = root.dataset;
  const messages = {available: labels.labelNew, current: labels.labelCurrent,
    'ahead-of-channel': labels.labelAhead, failed: labels.labelFailed};
  root.dataset.updateStatus = value.status;
  root.classList.toggle('gw-update-notification--available', available);
  root.querySelector('.gw-update-notification__badge').hidden = !available;
  const trigger = root.querySelector('[data-update-toggle]');
  trigger.title = available ? labels.labelAvailable : labels.labelTitle;
  trigger.setAttribute('aria-label', trigger.title);
  trigger.setAttribute('aria-expanded', String(open));
  root.querySelector('.gw-update-notification__panel').hidden = !open;
  text('[data-update-message]', messages[value.status] ?? labels.labelChecking);
  text('[data-update-current]', value.currentVersionLabel ?? value.currentVersion ?? '');
  text('[data-update-available]', value.availableVersionLabel ?? value.availableVersion ?? '');
  root.querySelector('[data-update-current-row]').hidden = !value.currentVersion;
  root.querySelector('[data-update-available-row]').hidden = !available;
  root.querySelector('[data-update-action]').hidden = !available;
  text('[data-update-announcement]', available ? `${labels.labelAvailable}: ${value.availableVersionLabel ?? value.availableVersion}` : '');
}

function close(restoreFocus = false) {
  if (!open) return;
  open = false;
  render();
  if (restoreFocus) root?.querySelector('[data-update-toggle]').focus();
}

function schedule() {
  clearTimeout(timer);
  if (!root || document.hidden || updating) return;
  const delay = latest?.status === 'checking' ? 5000 : Math.max(1000, POLL_MS - (Date.now() - lastRequest));
  timer = setTimeout(() => void refresh(), delay);
}

async function refresh() {
  if (!root || document.hidden || pending || updating) return;
  if (Date.now() - lastRequest < POLL_MS && latest?.status !== 'checking') return schedule();
  const revision = generation;
  controller = new AbortController();
  lastRequest = Date.now();
  pending = http.post('/api/admin/updates/notification', {}, {signal: controller.signal, timeoutMs: 60000});
  try {
    const value = await pending;
    if (revision === generation) { latest = value; render(); }
  } catch (error) {
    if (revision === generation && error.name !== 'AbortError') {
      latest = {...latest, status: 'failed', available: false};
      render();
    }
  } finally {
    if (revision === generation) { pending = undefined; controller = undefined; schedule(); }
  }
}

function sync() {
  const current = document.querySelector('[data-update-notification]');
  if (root !== current) {
    root = current;
    open = false;
    if (!root) {
      ++generation;
      controller?.abort();
      controller = pending = latest = undefined;
      lastRequest = 0;
      clearTimeout(timer);
      return;
    }
    render();
    void refresh();
  } else render();
}

document.addEventListener('click', event => {
  if (!root) return;
  if (event.target.closest('[data-update-toggle]')) {
    open = !open;
    render();
    if (open) { root.querySelector('[data-update-close]').focus(); void refresh(); }
  } else if (event.target.closest('[data-update-close]')) close(true);
  else if (!root.contains(event.target) || event.target.closest('[data-update-action]')) close();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && open && !event.defaultPrevented) {
    event.preventDefault();
    close(true);
  }
});
document.addEventListener('focusin', event => {
  if (open && !root?.contains(event.target)) close();
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) clearTimeout(timer);
  else void refresh();
});
window.addEventListener('gravewright:core-update-status', event => {
  if (!root || !event.detail?.status) return;
  ++generation;
  controller?.abort();
  controller = pending = undefined;
  latest = event.detail;
  lastRequest = latest.status === 'unchecked' ? 0 : Date.now();
  render();
  if (latest.status === 'unchecked') void refresh();
  else schedule();
});
window.addEventListener('gravewright:core-update-progress', event => {
  updating = event.detail?.active === true;
  if (updating) {
    ++generation;
    controller?.abort();
    controller = pending = undefined;
    clearTimeout(timer);
  } else schedule();
});
new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true});
sync();
