import { registerEscapeClose } from '/static/gravewright_web/escape.js';
const layoutKey = 'gravewright.conditions.anonymous';
export function conditionLayout() {
  try { return localStorage.getItem(layoutKey) === 'classic' ? 'classic' : 'gravewright'; }
  catch { return 'gravewright'; }
}
const labels = {
  en: ['Bar 1', 'Bar 2', 'Conditions', 'Add', 'Remove', 'Positive', 'Negative', 'Neutral', 'Only GM', 'Open character sheet', 'Could not save the change.'],
  'pt-BR': ['Barra 1', 'Barra 2', 'Condições', 'Adicionar', 'Remover', 'Positiva', 'Negativa', 'Neutra', 'Só o mestre', 'Abrir ficha', 'Não foi possível salvar a alteração.'],
  es: ['Barra 1', 'Barra 2', 'Condiciones', 'Añadir', 'Eliminar', 'Positiva', 'Negativa', 'Neutra', 'Solo director', 'Abrir ficha', 'No se pudo guardar el cambio.'],
};
function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function badge(condition) {
  const el = element('span', 'token-condition token-condition--' + condition.kind,
    condition.kind === 'negative' ? '☠' : condition.kind === 'positive' ? '✦' : '◆');
  el.title = condition.label;
  el.setAttribute('aria-label', condition.label);
  return el;
}
export function conditionTooltip(condition) {
  const description = typeof condition.description === 'string' ? condition.description.trim() : '';
  const clock = condition.duration;
  const text = durationLabels();
  const remaining = clock?.remaining ?? clock?.value;
  const duration = ['turns','rounds'].includes(clock?.type) && Number.isInteger(remaining)
    ? `\n${remaining} ${text[clock.type + (remaining === 1 ? 'Single' : '')]} · ${text[clock.type + (clock.expires === 'start' ? 'Start' : 'End')]}` : '';
  return condition.label + (description ? '\n' + description : '') + duration;
}

function durationLabels() {
  const lang = document.documentElement.lang;
  const values = lang.startsWith('pt')
    ? ['Duração','Sem duração','Turnos','Rodadas','Quantidade','Expira','Início do turno','Fim do turno','Início da rodada','Fim da rodada','turnos restantes','rodadas restantes','turno restante','rodada restante']
    : lang.startsWith('es')
    ? ['Duración','Sin duración','Turnos','Rondas','Cantidad','Expira','Inicio del turno','Final del turno','Inicio de la ronda','Final de la ronda','turnos restantes','rondas restantes','turno restante','ronda restante']
    : ['Duration','No duration','Turns','Rounds','Amount','Expires','Start of turn','End of turn','Start of round','End of round','turns remaining','rounds remaining','turn remaining','round remaining'];
  return Object.fromEntries(['duration','none','turnsLabel','roundsLabel','amount','expires','turnsStart','turnsEnd','roundsStart','roundsEnd','turns','rounds','turnsSingle','roundsSingle'].map((key,i)=>[key,values[i]]));
}

export function conditionDurationFields(form) {
  const text = durationLabels(), wrap = element('div','token-condition-duration');
  const unit = element('select'), count = element('input'), phase = element('select');
  unit.name = 'conditionDurationUnit'; count.name = 'conditionDurationCount'; phase.name = 'conditionDurationPhase';
  for (const [value,label] of [['',text.none],['turns',text.turnsLabel],['rounds',text.roundsLabel]]) unit.add(new Option(label,value));
  count.type='number'; count.min='1'; count.max='10000'; count.step='1'; count.value='1';
  const field=(caption,input)=>{const label=element('label','',caption);label.append(input);wrap.append(label);return label;};
  field(text.duration,unit);
  const amount=field(text.amount,count), expires=field(text.expires,phase);
  const update=()=>{
    amount.hidden=expires.hidden=!unit.value;count.disabled=phase.disabled=!unit.value;count.required=!!unit.value;
    const old=phase.value||'end';phase.replaceChildren();
    for(const value of ['end','start'])phase.add(new Option(text[(unit.value||'turns')+(value==='end'?'End':'Start')],value));
    phase.value=old;
  };
  unit.onchange=update;update();form.append(wrap);
  return ()=>unit.value?{type:unit.value,value:Number(count.value),expires:phase.value}:null;
}

export function quickControls(surface, { campaign, gm, command, read, openSheet, repaint }) {
  const text = labels[document.documentElement.lang] || labels.en;
  const panel = element('section', 'token-quick-controls');
  const hud = element('aside', 'token-condition-hud');
  const tooltip = element('div', 'token-condition-tooltip');
  tooltip.id = 'token-hud-condition-tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  panel.hidden = hud.hidden = true;
  panel.setAttribute('aria-label', text[2]);
  hud.setAttribute('aria-label', text[2]);
  surface.append(panel, hud, tooltip);
  const hideTooltip = () => { tooltip.hidden = true; };
  const showTooltip = event => {
    const icon = event.target.closest?.('.token-condition');
    if (!icon) return;
    tooltip.textContent = icon.dataset.conditionTooltip;
    tooltip.hidden = false;
    const rect = icon.getBoundingClientRect();
    tooltip.style.left = Math.max(8, Math.min(window.innerWidth - tooltip.offsetWidth - 8, rect.left)) + 'px';
    tooltip.style.top = Math.max(42, rect.top - tooltip.offsetHeight - 8) + 'px';
  };
  hud.addEventListener('pointerover', showTooltip);
  hud.addEventListener('focusin', showTooltip);
  hud.addEventListener('pointerout', hideTooltip);
  hud.addEventListener('focusout', hideTooltip);
  hud.addEventListener('scroll', hideTooltip);
  const unregisterEscape = registerEscapeClose(panel, () => {
    if (!busy) { opened = undefined; panel.hidden = true; }
  });
  for (const name of ['pointerdown', 'click', 'dblclick', 'contextmenu', 'keydown'])
    panel.addEventListener(name, event => event.stopPropagation());
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !busy) { opened = undefined; panel.hidden = true; }
  });
  let selected, opened, signature = '', hudSignature = '', busy = false, destroyed = false;
  const error = element('p', 'token-quick-controls__error');
  error.setAttribute('role', 'alert'); error.hidden = true;
  async function save(task) {
    if (busy || destroyed) return;
    busy = true; error.hidden = true;
    for (const el of panel.querySelectorAll('button,input,select,textarea')) el.disabled = true;
    try { await task(); await read(); }
    catch (failure) { error.textContent = failure.message || text[10]; error.hidden = false; }
    finally {
      busy = false; signature = '';
      for (const el of panel.querySelectorAll('button,input,select,textarea')) el.disabled = false;
      if (!destroyed) repaint();
    }
  }
  function button(label, run) {
    const el = element('button', '', label); el.type = 'button'; el.onclick = run; return el;
  }
  function build(token) {
    panel.replaceChildren();
    const header = element('header');
    header.append(element('strong', '', token.name), button('×', () => { opened = undefined; panel.hidden = true; }));
    header.lastChild.setAttribute('aria-label', 'Close');
    panel.append(header);
    for (const [slot, bar] of Object.entries(token.bars || {})) {
      if (!(bar.max > 0)) continue;
      const form = element('form', 'token-quick-controls__bar');
      const label = element('label', '', slot === 'bar_1' ? text[0] : text[1]);
      const input = element('input'); input.type = 'number'; input.step = 'any'; input.value = bar.value;
      input.setAttribute('aria-label', label.textContent);
      const track = element('progress'); track.max = bar.max; track.value = Math.max(0, bar.value);
      track.style.setProperty('--bar-color', bar.color); track.setAttribute('aria-label', label.textContent);
      label.append(track);
      async function update(value, delta = false) {
        if (!Number.isFinite(value)) return;
        await save(async () => {
          const response = await fetch(`/api/containers/${campaign}/actors/${token.actorId}/sheet?tokenId=${token.id}`, { cache: 'no-store' });
          if (!response.ok) throw Error(text[10]);
          const sheet = await response.json();
          if (!sheet.canEdit || !sheet.data?.bars?.[slot]) throw Error(text[10]);
          sheet.data.bars[slot].value = delta ? sheet.data.bars[slot].value + value : value;
          await window.gravewrightRealtime.resourceCommand('actors', 'sheet.save', {
            actorId: token.actorId, tokenId: token.id, name: sheet.name,
            version: sheet.version, sheetVersion: sheet.sheetVersion, data: sheet.data,
          });
        });
      }
      form.onsubmit = event => { event.preventDefault(); if (input.value !== '') void update(input.valueAsNumber); };
      input.onchange = () => { if (input.value !== '') void update(input.valueAsNumber); };
      const minus = button('−', () => update(-1, true)), plus = button('+', () => update(1, true));
      minus.setAttribute('aria-label', label.firstChild.textContent + ' −1');
      plus.setAttribute('aria-label', label.firstChild.textContent + ' +1');
      form.append(label, minus, input, element('span', '', '/ ' + bar.max), plus); panel.append(form);
    }
    const conditions = element('div', 'token-quick-controls__conditions');
    conditions.append(element('strong', '', text[2]));
    for (const condition of token.conditions || []) {
      const row = element('div', 'token-quick-controls__condition');
      row.title = conditionTooltip(condition);
      const remove = button('×', () => save(() => command('condition-remove', { tokenIds: [token.id], conditionId: condition.condition_id })));
      remove.setAttribute('aria-label', text[4] + ' ' + condition.label);
      row.append(badge(condition), element('span', '', condition.label), remove); conditions.append(row);
    }
    const form = element('form', 'token-quick-controls__add');
    const name = element('input'); name.required = true; name.maxLength = 191; name.placeholder = text[2]; name.setAttribute('aria-label', text[2]);
    const kind = element('select'); kind.setAttribute('aria-label', text[2]);
    ['neutral', 'positive', 'negative'].forEach((value, i) => { const option = element('option', '', text[[7,5,6][i]]); option.value = value; kind.append(option); });
    const add = button('+'); add.type = 'submit'; add.setAttribute('aria-label', text[3]);
    form.append(name, kind, add);
    const description = element('textarea', 'token-quick-controls__description');
    description.maxLength = 4000; description.rows = 2;
    description.placeholder = document.documentElement.lang === 'pt-BR' ? 'Descrição do efeito' : document.documentElement.lang === 'es' ? 'Descripción del efecto' : 'Effect description';
    description.setAttribute('aria-label', description.placeholder);
    form.append(description);
    const getDuration = conditionDurationFields(form);
    let visibility;
    if (gm) {
      const label = element('label', 'token-quick-controls__visibility', text[8]);
      visibility = element('input'); visibility.type = 'checkbox'; label.prepend(visibility); form.append(label);
    }
    form.onsubmit = event => {
      event.preventDefault();
      void save(() => command('condition-add', { tokenIds: [token.id], label: name.value.trim(), description: description.value, kind: kind.value, visibility: visibility?.checked ? 'gm' : 'everyone', duration: getDuration() }));
    };
    conditions.append(form); panel.append(conditions);
    if (token.canOpenSheet) panel.append(button(text[9], () => openSheet(token)));
    panel.append(error);
  }
  return {
    open(id) { opened = id; repaint(); },
    update(tokens, selection, interactive, position) {
      const token = selection.length === 1 ? tokens.find(t => t.id === selection[0] && t.canControl) : null;
      if (selected !== token?.id) {
        selected = token?.id;
        if (opened !== selected) opened = undefined;
        signature = ''; error.hidden = true;
      }
      panel.hidden = !token || !interactive || opened !== selected;
      if (!panel.hidden) {
        const key = JSON.stringify(token);
        if (key !== signature && !busy && !panel.contains(document.activeElement)) { signature = key; build(token); }
        const point = position(token);
        panel.style.left = Math.max(8, Math.min(surface.clientWidth - panel.offsetWidth - 8, point.x + 12)) + 'px';
        panel.style.top = Math.max(42, Math.min(surface.clientHeight - panel.offsetHeight - 80, point.y)) + 'px';
      }
      const visible = conditionLayout() === 'gravewright' ? tokens.filter(t => t.conditions?.length) : [];
      const key = JSON.stringify(visible.map(t => [t.id, t.name, t.conditions]));
      hud.hidden = !visible.length;
      if (key !== hudSignature) {
        hideTooltip();
        hudSignature = key; hud.replaceChildren();
        for (const t of visible) {
          const row = element('div', 'token-condition-hud__group');
          row.append(element('strong', '', t.name));
          const badges = element('div');
          badges.append(...t.conditions.map(condition => {
            const icon = badge(condition);
            icon.removeAttribute('title');
            icon.tabIndex = 0;
            icon.dataset.conditionTooltip = conditionTooltip(condition);
            icon.setAttribute('aria-describedby', tooltip.id);
            return icon;
          }));
          row.append(badges); hud.append(row);
        }
      }
    },
    destroy() { destroyed = true; unregisterEscape(); panel.remove(); hud.remove(); tooltip.remove(); },
  };
}
