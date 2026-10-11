import { mountModal } from './modal.js';
const root = () => document.querySelector('#table-workspace');
const pt = () => document.documentElement.lang.toLowerCase().startsWith('pt');
const text = (en, br) => pt() ? br : en;
const labels = () => ({none: text('None', 'Nenhum'), limited: text('Limited', 'Limitado'), read: text('Observer', 'Observador'), owner: text('Owner', 'Proprietário'), inherit: text('Inherit from journal', 'Herdar do diário'), unchanged: text('No change', 'Não alterar'), default: text('Default', 'Padrão')});

async function request(url, payload) {
  const csrf = payload ? await (await fetch('/__gravewright/csrf')).json() : null;
  const response = await fetch(url, payload ? {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type': 'application/json', [csrf.header || 'X-CSRF-Token']: csrf.token},
    body: JSON.stringify(payload),
  } : {credentials: 'same-origin'});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || text('Could not save permissions.', 'Não foi possível salvar as permissões.'));
  return data;
}

export async function openPermissions(kind, id, {onSave} = {}) {
  const url = `/api/containers/${root().dataset.tableId}/ownership/${encodeURIComponent(kind)}/${encodeURIComponent(id)}`;
  const data = await request(url);
  const dialog = document.createElement('section');
  dialog.className = 'ownership-dialog';
  dialog.dataset.movable = '';
  dialog.dataset.windowKey = 'permissions:' + kind;
  dialog.setAttribute('role', 'dialog');
  dialog.setAttribute('aria-modal', 'true');
  dialog.tabIndex = -1;
  dialog.innerHTML = '<form><header data-move-handle><strong id="ownership-title"></strong><button type="button" data-close>×</button></header><p data-hint></p><label class="ownership-dialog__gm"><span></span><input type="checkbox" name="showGM"></label><div data-rows></div><p class="ownership-dialog__help"></p><p role="alert" hidden></p><footer><button type="button" data-reload hidden></button><button type="submit"></button></footer></form>';
  dialog.setAttribute('aria-labelledby', 'ownership-title');
  dialog.querySelector('strong').textContent = `${text('Permissions', 'Permissões')}: ${data.title}`;
  const close = dialog.querySelector('[data-close]');
  close.setAttribute('aria-label', text('Close', 'Fechar'));
  close.onclick = () => { if (!save.disabled) dialog.close(); };
  dialog.querySelector('[data-hint]').textContent = data.bulk
    ? text('Apply access to documents directly inside this folder. Subfolders are excluded.', 'Aplicar acesso aos documentos desta pasta. O conteúdo de subpastas não será alterado.')
    : data.roles ? text('Configure access for each table role.', 'Configure o acesso de cada função na mesa.')
    : text('Choose the default access and exceptions for each player.', 'Escolha o acesso padrão e as exceções de cada jogador.');
  const gm = dialog.querySelector('.ownership-dialog__gm');
  gm.querySelector('span').textContent = text('Show game masters', 'Mostrar mestres');
  gm.hidden = data.roles;
  gm.querySelector('input').onchange = event => dialog.querySelectorAll('[data-gm]').forEach(row => row.hidden = !event.target.checked);
  const host = dialog.querySelector('[data-rows]');
  const controls = new Map();
  const names = labels();
  function row(key, name, values, value, isGM = false) {
    const label = document.createElement('label');
    label.className = 'ownership-dialog__row';
    const caption = document.createElement('span');
    caption.textContent = name;
    const select = document.createElement('select');
    select.name = key;
    for (const v of values) select.add(new Option(names[v], v));
    select.value = values.includes(value) ? value : values[0];
    if (isGM) {
      label.dataset.gm = '';
      label.hidden = true;
      select.disabled = true;
      select.replaceChildren(new Option(text('Owner (always)', 'Proprietário (sempre)'), 'owner'));
    } else controls.set(key, select);
    label.append(caption, select);
    host.append(label);
  }
  const choices = data.bulk ? ['unchanged', ...data.levels] : data.levels;
  row('default', text('All players', 'Todos os jogadores'), choices, data.permissions.default);
  if (data.roles) {
    for (const [key, en, br] of [['player', 'Player', 'Jogador'], ['streamer', 'Streamer', 'Transmissão']])
      row(key, text(en, br), ['default', ...choices], data.permissions[key] ?? 'default');
  } else for (const m of data.members) {
    row(m.id, m.name, ['default', ...choices.filter(v => m.role !== 'streamer' || v !== 'owner')], data.permissions[m.id] ?? (data.bulk ? 'unchanged' : 'default'), m.role === 'gm');
  }
  dialog.querySelector('.ownership-dialog__help').textContent = data.gmOnlyPage
    ? text('This page is GM-only. Make it public before sharing access.', 'Esta página é exclusiva do mestre. Torne-a pública antes de compartilhar o acesso.')
    : data.kind === 'pages' ? text('Page access also requires access to the journal.', 'O acesso à página também exige acesso ao diário.')
    : data.kind === 'scenes' || data.kind === 'scene-folders' ? text('Players can view an allowed scene while it is active and visible to players.', 'Os jogadores podem ver uma cena permitida enquanto ela estiver ativa e visível aos jogadores.')
    : text('Default follows “All players”. Limited shows the directory entry without opening its content.', 'Padrão segue “Todos os jogadores”. Limitado mostra a entrada no diretório sem abrir seu conteúdo.');
  const save = dialog.querySelector('[type=submit]');
  save.textContent = text('Save changes', 'Salvar alterações');
  const reload = dialog.querySelector('[data-reload]');
  reload.textContent = text('Reload permissions', 'Recarregar permissões');
  reload.onclick = () => openPermissions(kind, id, {onSave}).catch(error => { alert.textContent = error.message; });
  const alert = dialog.querySelector('[role=alert]');
  dialog.querySelector('form').onsubmit = async event => {
    event.preventDefault();
    save.disabled = true;
    close.disabled = true;
    const permissions = {}, reset = [];
    for (const [key, select] of controls) {
      if (select.value !== 'default') permissions[key] = select.value;
      else if (data.bulk) { permissions[key] = 'unchanged'; reset.push(key); }
    }
    try {
      const result = await request(url, {version: data.version, permissions, reset});
      await onSave?.(result);
      window.dispatchEvent(new CustomEvent('gravewright:permissions-saved', {detail: {kind: data.kind, id: data.id}}));
      dialog.close();
    } catch (error) {
      alert.textContent = error.message;
      alert.hidden = false;
      reload.hidden = false;
    } finally { save.disabled = false; close.disabled = false; }
  };
  mountModal(dialog, {canClose: () => !save.disabled});
  controls.get('default')?.focus();
  return dialog;
}

window.gravewrightPermissions = {open: openPermissions};
