import { mountModal } from '/static/gravewright_table/modal.js';

const text = (en, br) => document.documentElement.lang.toLowerCase().startsWith('pt') ? br : en;
export const presentationLabel = () => text('Show to players', 'Exibir para os jogadores');

export function openPresentation(journal, {members, targeted, page, send}) {
  const modal = document.createElement('section');
  modal.className = 'ownership-dialog journal-presentation-modal';
  modal.dataset.movable = '';
  modal.dataset.windowKey = 'journal-presentation';
  modal.innerHTML = '<form><header><strong id="presentation-title"></strong><button type="button" data-close>×</button></header><fieldset><legend></legend><label class="ownership-dialog__gm"><span></span><input type="checkbox" name="allPlayers" checked></label><div data-players></div></fieldset><label class="journal-field" data-access><span></span><select name="ownership"></select></label><p class="ownership-dialog__help"></p><p role="alert" hidden></p><footer><button type="submit"></button></footer></form>';
  modal.setAttribute('aria-labelledby', 'presentation-title');
  modal.querySelector('strong').textContent = `${presentationLabel()}: ${page?.title || journal.title}`;
  modal.querySelector('legend').textContent = text('Show to', 'Exibir para');
  modal.querySelector('.ownership-dialog__gm span').textContent = text('All players', 'Todos os jogadores');
  const all = modal.querySelector('[name=allPlayers]');
  const players = members.filter(member => member.role !== 'gm');
  const host = modal.querySelector('[data-players]');
  for (const member of targeted ? players : []) {
    const label = document.createElement('label');
    label.className = 'ownership-dialog__gm';
    const caption = document.createElement('span');
    caption.textContent = member.name;
    const checkbox = document.createElement('input');
    Object.assign(checkbox, {type: 'checkbox', name: 'players', value: member.id, checked: true, disabled: true});
    label.append(caption, checkbox);
    host.append(label);
  }
  all.disabled = !targeted;
  all.onchange = () => host.querySelectorAll('input').forEach(input => {
    input.checked = all.checked;
    input.disabled = all.checked;
  });
  modal.querySelector('[data-access] span').textContent = text('Configure ownership', 'Configurar permissões');
  modal.querySelector('[data-access]').hidden = Boolean(page);
  const ownership = modal.querySelector('[name=ownership]');
  for (const [value, en, br] of [['unchanged', 'No change', 'Não alterar'], ['none', 'None', 'Nenhum'], ['limited', 'Limited', 'Limitado'], ['read', 'Observer', 'Observador'], ['owner', 'Owner', 'Proprietário']])
    ownership.add(new Option(text(en, br), value));
  modal.querySelector('.ownership-dialog__help').textContent = page
    ? text('Show this page temporarily. GM-only content stays hidden.', 'Exibe esta página temporariamente. O conteúdo exclusivo do mestre permanece oculto.')
    : text('No change shows the document temporarily. Choose an access level to also grant permanent access. Higher permissions are preserved.', 'Não alterar exibe o documento temporariamente. Escolha um nível para também conceder acesso permanente. Permissões superiores serão preservadas.');
  const submit = modal.querySelector('[type=submit]'), close = modal.querySelector('[data-close]');
  submit.textContent = presentationLabel();
  close.setAttribute('aria-label', text('Close', 'Fechar'));
  close.onclick = () => { if (!submit.disabled) modal.close(); };
  modal.querySelector('form').onsubmit = async event => {
    event.preventDefault();
    const alert = modal.querySelector('[role=alert]');
    const targets = all.checked ? null : [...host.querySelectorAll('input:checked')].map(input => input.value);
    if (!players.length || targets?.length === 0) {
      alert.textContent = text('Choose at least one player.', 'Selecione pelo menos um jogador.');
      alert.hidden = false;
      return;
    }
    submit.disabled = close.disabled = true;
    try {
      await send({journal_id: journal.id, targets, ownership: page ? 'unchanged' : ownership.value, ...(page ? {page_id: page.id} : {})});
      modal.close();
    } catch (error) {
      alert.textContent = error.message;
      alert.hidden = false;
    } finally { submit.disabled = close.disabled = false; }
  };
  mountModal(modal, {canClose: () => !submit.disabled});
  return modal;
}
