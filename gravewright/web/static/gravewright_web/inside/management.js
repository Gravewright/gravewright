import { HttpClient } from "/static/gravewright_modules/http-client.js";
const http = new HttpClient();
const text = (root, selector, value) => {
  const el = root.querySelector(selector);
  if (el) el.textContent = value ?? "";
};
const show = (root, selector, visible) => root.querySelector(selector)?.toggleAttribute("hidden", !visible);
const marketplaceErrors = {
  marketplace_catalog_missing: "Set GRAVEWRIGHT_MARKETPLACE_URL to the publisher's HTTPS JSON catalog, then restart the host.",
  marketplace_catalog_invalid: "GRAVEWRIGHT_MARKETPLACE_URL must be a valid HTTPS catalog URL without credentials or a fragment. Correct it and restart the host.",
  marketplace_keys_missing: "Set GRAVEWRIGHT_MARKETPLACE_KEYS_FILE to the publisher's trusted public keys file, then restart the host.",
  marketplace_keys_unreadable: "The host cannot read GRAVEWRIGHT_MARKETPLACE_KEYS_FILE. Check that the file exists and the server can read it, then refresh.",
  marketplace_keys_invalid: "The trusted keys file must be a JSON object mapping key IDs to valid base64 Ed25519 public keys (32 bytes). Correct the file and refresh.",
  marketplace_keys_empty: "The trusted keys file is empty. Add the publisher's Ed25519 public key and refresh.",
  unavailable: "The marketplace or selected release is unavailable. Check the publisher URL and connection, then refresh.",
  unreachable: "The host could not be reached. Check your connection and refresh.",
  invalid_data: "The publisher returned an invalid catalog or package. Check the configured catalog and contact its publisher.",
  permission_denied: "The publisher's signature could not be verified, or this release was revoked. Refresh and check the trusted public keys.",
  not_found: "This release is no longer in the catalog. Refresh to see available releases.",
  request_failed: "The marketplace request failed. Check the host and publisher connection, then refresh."
};
function summary(root, values) {
  root.replaceChildren();
  for (const [key, value] of Object.entries(values)) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = typeof value === "object" ? JSON.stringify(value) : String(value);
    root.append(dt, dd);
  }
}
async function run(root, work) {
  if (root.dataset.busy === "true") return;
  root.dataset.busy = "true";
  root.setAttribute("aria-busy", "true");
  show(root, "[role=alert]", false);
  const disabled = [...root.querySelectorAll("button,input,select")].map((el) => [el, el.disabled]);
  disabled.forEach(([el]) => el.disabled = true);
  try {
    await work();
  } catch (error) {
    text(root, "[role=alert]", (root.dataset.moduleCatalog && marketplaceErrors[error.code ?? error.message]) || (error.status === 403 ? "Only the installation owner or campaign GM can perform this action." : error.status === 409 ? "The state changed. Refresh before trying again." : error.status === 413 ? "The archive exceeds the 256 MB upload limit." : error.message || "The operation failed. Check the file or connection and try again."));
    show(root, "[role=alert]", true);
  } finally {
    root.dataset.busy = "false";
    root.setAttribute("aria-busy", "false");
    disabled.forEach(([el, value]) => el.disabled = el.dataset.unavailable === undefined ? value : el.dataset.unavailable === 'true');
  }
}
function modules(root) {
  let installed = [], releases = [], ready = false, page = 1, category = '';
  const normalize = value => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const collator = new Intl.Collator(document.documentElement.lang, {numeric:true, sensitivity:"base"});
  const installedOnly = root.dataset.moduleCatalog === "installed";
  const kind = root.dataset.packageKind;
  const manager = root.closest('[data-package-manager]');
  const browser = manager.querySelector('[data-package-browser]');
  const detail = root.querySelector('[data-package-detail]');
  const native = root.querySelector('[data-native-system]');
  const language = document.documentElement.lang;
  const ui = (en, pt, es) => language === 'pt-BR' ? pt : language === 'es' ? es : en;
  const nativeRow = native ? (() => { const r = JSON.parse(native.textContent); return {id:r.systemId, name:r.title, version:'', builtin:true, system:{}, description:ui('Built into Gravewright. Available when creating a table.', 'Integrado ao Gravewright. Disponível ao criar uma mesa.', 'Integrado en Gravewright. Disponible al crear una mesa.')}; })() : null;
  const packageType = r => r.system ? 'system' : r.type ?? 'module';
  function view(mode) {
    root.dataset.view = !installedOnly || mode === 'list' ? 'list' : 'tiles';
    root.querySelectorAll('[data-view-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.viewMode === root.dataset.view)));
    try { if (installedOnly) localStorage.setItem('gravewright.packages.' + kind + '.view', root.dataset.view); } catch {}
  }
  try { view(localStorage.getItem('gravewright.packages.' + kind + '.view')); } catch {}
  root.querySelectorAll('[data-view-mode]').forEach(button => button.onclick = () => view(button.dataset.viewMode));
  root.querySelector('[data-action=close-detail]').onclick = () => detail.close();
  async function installPackage(row) {
    const area = root.querySelector('[data-install-progress]');
    const bar = area.querySelector('progress');
    area.hidden = false;
    text(area, '[data-progress-name]', row.name ?? row.id);
    function progress(event) {
      const labels = {
        catalog: ui('Checking catalog…', 'Consultando catálogo…', 'Consultando catálogo…'),
        download: ui('Downloading package…', 'Baixando pacote…', 'Descargando paquete…'),
        verify: ui('Verifying signature and installing…', 'Verificando assinatura e instalando…', 'Verificando firma e instalando…'),
        complete: ui('Installation complete', 'Instalação concluída', 'Instalación completada'),
        error: ui('Installation failed', 'Falha na instalação', 'Error de instalación')
      };
      let label = labels[event.stage];
      if (event.stage === 'download' && event.total) {
        bar.value = Math.min(100, 100 * event.received / event.total);
        label += ` ${Math.floor(bar.value)}% · ${(event.received / 1048576).toFixed(1)} / ${(event.total / 1048576).toFixed(1)} MB`;
      } else if (event.stage === 'complete') bar.value = 100;
      else { bar.removeAttribute('value'); if (event.stage === 'download') label += ` ${(event.received / 1048576).toFixed(1)} MB`; }
      text(area, '[data-progress-label]', label);
      area.dataset.stage = event.stage;
    }
    const close = manager.querySelector('[data-action=close-browser]');
    close.disabled = true;
    progress({stage:'catalog'});
    try {
      const csrfPath = document.querySelector('meta[name="gravewright-csrf-url"]')?.content || '/__gravewright/csrf';
      const {token, header} = await http.get(csrfPath);
      const api = document.querySelector('meta[name="gravewright-backend-api"]')?.content || '/api';
      const response = await fetch(api + '/marketplace/install', {method:'POST', headers:{[header]:token, 'Content-Type':'application/json', Accept:'application/x-ndjson'}, body:JSON.stringify({id:row.id, version:row.version})});
      if (!response.ok) { const payload = await response.json(); throw Object.assign(new Error(payload.error), {code:payload.error}); }
      const reader = response.body.getReader(), decoder = new TextDecoder();
      let buffer = '', complete = false;
      try {
        while (true) {
          const {done, value} = await reader.read();
          buffer += decoder.decode(value, {stream:!done});
          const lines = buffer.split('\n'); buffer = lines.pop();
          for (const line of lines) {
            if (!line) continue;
            const event = JSON.parse(line); progress(event);
            if (event.stage === 'error') throw Object.assign(new Error(event.error), {code:event.error});
            if (event.stage === 'complete') complete = true;
          }
          if (done) break;
        }
      } finally { reader.releaseLock(); }
      if (!complete) throw new Error(ui('Installation interrupted. Refresh to check the result.', 'Instalação interrompida. Atualize para conferir o resultado.', 'Instalación interrumpida. Actualiza para comprobar el resultado.'));
    } catch (error) { progress({stage:'error'}); throw error; }
    finally { close.disabled = false; }
  }
  function render() {
    const q = normalize(root.querySelector('input[type=search]').value.trim());
    const filter = root.querySelector('[data-filter]').value;
    root.querySelectorAll('[data-state]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.state === filter)));
    const direction = root.querySelector('[data-sort]').value === 'desc' ? -1 : 1;
    const size = Number(root.querySelector('[data-page-size]').value);
    const localRows = nativeRow ? [...installed, nativeRow] : installed;
    const locals = new Map(localRows.map(r => [r.id + '@' + r.version, r]));
    const all = (installedOnly ? localRows : releases).filter(r => packageType(locals.get(r.id + '@' + r.version) ?? r) === kind);
    const categories = root.querySelector('[data-categories]');
    if (categories) {
      const focusedCategory = categories.contains(document.activeElement) ? document.activeElement.dataset.category : undefined;
      const counts = new Map();
      for (const item of all) for (const tag of new Set(item.tags ?? locals.get(item.id + '@' + item.version)?.tags ?? [])) counts.set(tag, (counts.get(tag) ?? 0) + 1);
      if (category && !counts.has(category) && (installedOnly || ready)) category = '';
      categories.replaceChildren();
      for (const [tag, count] of [['', all.length], ...[...counts].sort((a,b) => collator.compare(a[0],b[0]))]) {
        const button = document.createElement('button'), name = document.createElement('span'), number = document.createElement('span');
        button.type = 'button'; button.dataset.category = tag; button.setAttribute('aria-pressed', String(category === tag));
        name.textContent = tag || ui('All packages', 'Todos os pacotes', 'Todos los paquetes'); name.translate = false;
        number.textContent = count; button.append(name, number);
        button.onclick = () => { category = tag; page = 1; render(); };
        categories.append(button);
        if (focusedCategory === tag) button.focus();
      }
    }
    const rows = all.filter(r => {
      const local = locals.get(r.id + '@' + r.version);
      const info = local ?? r;
      return (!category || (r.tags ?? local?.tags ?? []).includes(category)) && normalize(`${r.id} ${info.name ?? ''} ${r.version} ${info.description ?? ''} ${info.author ?? ''}`).includes(q)
        && (filter === 'all' || filter === 'installed' && !!local
          || filter === 'active' && local?.globalEnabled && !local.revoked
          || filter === 'available' && !local || filter === 'revoked' && local?.revoked);
    }).sort((a,b) => direction * (collator.compare(locals.get(a.id + '@' + a.version)?.name ?? a.name ?? a.id,
      locals.get(b.id + '@' + b.version)?.name ?? b.name ?? b.id) || collator.compare(a.id,b.id) || collator.compare(b.version,a.version)));
    const pages = Math.max(1, Math.ceil(rows.length / size));
    page = Math.min(page, pages);
    text(root, '[data-count]', `${rows.length} / ${all.length}`);
    text(root, '[data-page]', `${page} / ${pages}`);
    root.querySelector('[data-action=previous]').disabled = page === 1;
    root.querySelector('[data-action=next]').disabled = page === pages;
    show(root, '.module-catalog__pagination', all.length > 24);
    const grid = root.querySelector(".module-catalog__grid");
    grid.replaceChildren();
    for (const row of rows.slice((page - 1) * size, page * size)) {
      const local = locals.get(row.id + '@' + row.version), card = root.querySelector("template").content.firstElementChild.cloneNode(true);
      text(card, "h3", local?.name ?? row.name ?? row.id);
      text(card, '[data-card-description]', row.description ?? local?.description ?? '');
      const tags = card.querySelector('[data-tags]');
      if (tags) for (const tag of row.tags ?? local?.tags ?? []) { const badge = document.createElement('span'); badge.textContent = tag; tags.append(badge); }
      text(card, "[data-version]", row.builtin ? "PDF" : `v${row.version}`);
      const status = row.builtin ? ui('Built-in', 'Integrado', 'Integrado') : local?.revoked ? ui('Revoked', 'Revogado', 'Revocado') : local?.globalEnabled ? ui('Active', 'Ativo', 'Activo') : local ? ui('Installed', 'Instalado', 'Instalado') : ui('Available', 'Disponível', 'Disponible');
      text(card, '[data-status]', status);
      card.dataset.status = row.builtin ? 'builtin' : local?.revoked ? 'revoked' : local?.globalEnabled ? 'active' : 'installed';
      card.querySelector('[data-action=details]').onclick = () => {
        text(detail, '[data-detail-title]', local?.name ?? row.name ?? row.id);
        text(detail, '[data-description]', local?.description ?? row.description ?? '');
        text(detail, '[data-identity]', [row.id, row.version, local?.author ?? row.author, local?.license ?? row.license].filter(Boolean).join(' · '));
        text(detail, '[data-detail-status]', status);
        detail.showModal();
      };
      show(card, "[data-action=install]", !local);
      card.querySelector("[data-action=install]").onclick = () => run(root, async () => {
        try {
        await installPackage(row);
        } catch (error) {
          releases = [];
          ready = false;
          render();
          throw error;
        }
        await refresh();
        manager.querySelector('[data-module-catalog=installed]').dispatchEvent(new Event('packages-changed'));
        text(root, '[role=status]', ui('Package installed. It is now in your library.', 'Pacote instalado. Ele já está na sua biblioteca.', 'Paquete instalado. Ya está en tu biblioteca.'));
        show(root, "[role=status]", true);
      });
      if (installedOnly && local?.locales && !local.revoked) {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.action = 'global-activation';
        button.textContent = '⏻';
        button.title = local.globalEnabled ? ui('Deactivate languages', 'Desativar idiomas', 'Desactivar idiomas') : ui('Activate languages', 'Ativar idiomas', 'Activar idiomas');
        button.setAttribute('aria-label', button.title);
        button.setAttribute('aria-pressed', String(!!local.globalEnabled));
        button.onclick = () => run(root, async () => {
          await http.post('/api/module-packages/activation', {id: row.id, version: row.version, enabled: !local.globalEnabled});
          location.reload();
        });
        card.querySelector(".module-catalog__actions").append(button);
      }
      grid.append(card);
    }
    text(root, '.module-catalog__empty', (q || filter !== 'all') ? ui('No matching packages.', 'Nenhum pacote corresponde aos filtros.', 'Ningún paquete coincide con los filtros.') : installedOnly ? ui('Your library is empty. Use Install to add packages.', 'Sua biblioteca está vazia. Use Instalar para adicionar pacotes.', 'Tu biblioteca está vacía. Usa Instalar para añadir paquetes.') : ui('No compatible packages of this type are available.', 'Nenhum pacote compatível deste tipo está disponível.', 'No hay paquetes compatibles de este tipo disponibles.'));
    show(root, ".module-catalog__empty", !rows.length && (installedOnly || ready));
  }
  async function refresh() {
    show(root, "[role=status]", false);
    if (installedOnly) {
      installed = await http.get("/api/module-packages");
      render();
      return;
    }
    releases = [];
    ready = false;
    show(root, ".module-catalog__setup", false);
    render();
    try {
      const [status, packages] = await Promise.all([http.get("/api/marketplace/status"), http.get("/api/module-packages")]);
      installed = packages;
      ready = status.ready ?? (status.catalogConfigured && status.trustedKeysConfigured);
      show(root, ".module-catalog__setup", !ready);
      for (const [field, configured] of [["catalog", status.catalogConfigured], ["keys", status.trustedKeysConfigured]]) {
        const code = status.errors?.find((error) => error.field === field)?.code ?? `marketplace_${field}_missing`;
        text(root, `[data-setup=${field}]`, marketplaceErrors[code] ?? "Check the marketplace configuration on the host.");
        show(root, `[data-setup=${field}]`, !configured);
      }
      if (ready) {
        const records = await http.get("/api/marketplace", { timeoutMs: 6e4 });
        // Reading a catalog applies signed revocations; refresh local status afterwards.
        installed = await http.get("/api/module-packages");
        releases = records;
      }
      render();
    } catch (error) {
      releases = [];
      ready = false;
      render();
      throw error;
    }
  }
  const reset = () => { page = 1; render(); };
  root.querySelector('input[type=search]').oninput = reset;
  root.querySelector('[data-filter]').onchange = reset;
  root.querySelectorAll('[data-state]').forEach(button => button.onclick = () => { root.querySelector('[data-filter]').value = button.dataset.state; reset(); });
  root.querySelector('[data-sort]').onchange = reset;
  root.querySelector('[data-page-size]').onchange = reset;
  root.querySelector('[data-action=previous]').onclick = () => { page = Math.max(1, page - 1); render(); };
  root.querySelector('[data-action=next]').onclick = () => { page += 1; render(); };
  if (installedOnly) root.querySelector('[data-filter] option[value=available]').remove();
  root.querySelector("[data-action=refresh]").onclick = async () => { await run(root, refresh); render(); };
  if (installedOnly) {
    root.querySelector('[data-action=browse]').onclick = () => {
      browser.hidden = false;
      root.inert = true;
      browser.dataset.restoreOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      browser.querySelector('input[type=search]').focus();
      browser.querySelector('[data-module-catalog]').dispatchEvent(new Event('catalog-open'));
    };
    const closeBrowser = () => {
      if (manager.querySelector('[data-action=close-browser]').disabled) return;
      browser.hidden = true; root.inert = false;
      document.body.style.overflow = browser.dataset.restoreOverflow ?? '';
      root.querySelector('[data-action=browse]').focus();
    };
    manager.querySelector('[data-action=close-browser]').onclick = closeBrowser;
    document.addEventListener('keydown', event => {
      if (browser.hidden || browser.querySelector('dialog[open]')) return;
      if (event.key === 'Escape') { event.preventDefault(); closeBrowser(); }
      if (event.key === 'Tab') {
        const focusable = [...browser.querySelectorAll('button,input,select,a[href],[tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
        const first = focusable[0], last = focusable.at(-1);
        if (event.shiftKey && (document.activeElement === first || !browser.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !browser.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
      }
    });
    root.addEventListener('packages-changed', () => void run(root, refresh).then(render));
    void run(root, refresh).then(render);
  } else {
    root.addEventListener('catalog-open', () => void run(root, refresh).then(render));
  }
}
function privacySettings(root) {
  const language = document.documentElement.lang;
  const ui = (en, pt, es) => language === 'pt-BR' ? pt : language === 'es' ? es : en;
  root.querySelector('[data-privacy-form]').onsubmit = event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    data.enabled = event.target.elements.enabled.checked;
    void run(root, async () => {
      try {
        await http.post('/api/admin/settings/privacy', data);
      } catch {
        throw Error(ui('Could not save the policy. Check the fields and try again.','Não foi possível salvar a política. Confira os campos e tente novamente.','No se pudo guardar la política. Revisa los campos e inténtalo de nuevo.'));
      }
      text(root, '[role=status]', data.enabled ? ui('Saved. The policy is visible on login.','Salva. A política está visível no login.','Guardada. La política está visible al iniciar sesión.') : ui('Saved. The policy is hidden on login.','Salva. A política está oculta no login.','Guardada. La política está oculta al iniciar sesión.'));
      show(root, '[role=status]', true);
    });
  };
}
function administration(root) {
  let report, preview, release, automatic = {}, pollTimer;
  const language = document.documentElement.lang;
  const ui = (en, pt, es) => language === 'pt-BR' ? pt : language === 'es' ? es : en;
  const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const categories = {module:ui('Modules','Módulos','Módulos'), campaign:ui('Tables','Mesas','Mesas'), snapshot:ui('Backups','Backups','Copias de seguridad'), updates:ui('Updates','Atualizações','Actualizaciones'), settings:ui('Settings','Configurações','Configuración')};
  const actions = {
    'module.install':ui('Package installed','Pacote instalado','Paquete instalado'),
    'module.global_activation':ui('Language options changed','Opções de idioma alteradas','Opciones de idioma modificadas'),
    'module.activate':ui('Module activated','Módulo ativado','Módulo activado'),
    'updates.check':ui('Update check','Verificação de atualização','Comprobación de actualización'),
    'updates.channel':ui('Update channel changed','Canal de atualização alterado','Canal de actualización modificado'),
    'campaign.clone':ui('Table copied','Mesa copiada','Mesa copiada'),
    'campaign.import':ui('Table imported','Mesa importada','Mesa importada'),
    'campaign.export':ui('Table exported','Mesa exportada','Mesa exportada'),
    'snapshot.create':ui('Backup created','Backup criado','Copia de seguridad creada'),
    'snapshot.restore':ui('Backup restored','Backup restaurado','Copia de seguridad restaurada')
  };
  function updates(value) {
    release = value;
    automatic = value.automatic ?? automatic;
    const stages = {queued:ui('Update queued','Atualização na fila','Actualización en cola'),download:ui('Downloading release','Baixando versão','Descargando versión'),verify:ui('Verifying release','Validando versão','Validando versión'),dependencies:ui('Preparing dependencies','Preparando dependências','Preparando dependencias'),backup:ui('Backing up database and files','Salvando banco e arquivos','Guardando base y archivos'),migrate:ui('Applying migrations','Aplicando migrações','Aplicando migraciones'),restart:ui('Restarting server','Reiniciando servidor','Reiniciando servidor'),rollback:ui('Restoring previous version','Restaurando versão anterior','Restaurando versión anterior'),rolled_back:ui('Update failed; previous version restored','A atualização falhou; versão anterior restaurada','La actualización falló; versión anterior restaurada'),failed:ui('Update failed; check the update log','A atualização falhou; consulte o log de atualização','La actualización falló; consulta el registro'),complete:ui('Update installed','Atualização instalada','Actualización instalada')};
    text(root, '[data-automatic-help]', automatic.supported ? ui('Installation includes backup and a server restart. Open tables will disconnect briefly.','A instalação inclui backup e reinício do servidor. As mesas abertas serão desconectadas por um momento.','La instalación incluye copia de seguridad y reinicio. Las mesas abiertas se desconectarán brevemente.') : ui('Automatic installation is available through the Gravewright launcher on Windows, Linux and macOS. Restart using the updated launcher.','A instalação automática funciona pelo inicializador do Gravewright no Windows, Linux e macOS. Reinicie pelo inicializador atualizado.','La instalación automática está disponible desde el iniciador de Gravewright en Windows, Linux y macOS. Reinicia con el iniciador actualizado.'));
    const installButton = root.querySelector('[data-action=apply-update]');
    installButton.hidden = false;
    installButton.dataset.unavailable = String(!automatic.supported || automatic.busy || value.status !== 'available');
    installButton.disabled = installButton.dataset.unavailable === 'true';
    text(root, '[data-automatic-progress]', (stages[automatic.stage] ?? '') + (automatic.stage === 'download' && automatic.total ? ` · ${Math.floor(100 * automatic.received / automatic.total)}%` : ''));
    show(root, '[data-automatic-progress]', !!stages[automatic.stage]);
    if (automatic.busy && !pollTimer) pollTimer = setTimeout(pollUpdate, 1500);
    const statuses = {current:ui('Up to date','Atualizado','Actualizado'),available:ui('Update available','Atualização disponível','Actualización disponible'),failed:ui('Check failed','Falha na consulta','Error de consulta'),unchecked:ui('Not checked yet','Ainda não verificado','Todavía sin comprobar'),'ahead-of-channel':ui('Newer than this channel','Mais recente que este canal','Más reciente que este canal')};
    summary(root.querySelector('[data-update-summary]'), {[ui('Installed version','Versão instalada','Versión instalada')]:value.currentVersionLabel ?? value.currentVersion,[ui('Status','Situação','Estado')]:statuses[value.status] ?? value.status,...value.availableVersion ? {[ui('Published version','Versão publicada','Versión publicada')]:value.availableVersionLabel ?? value.availableVersion} : {},...value.checkedAt ? {[ui('Last check','Última verificação','Última comprobación')]:new Date(value.checkedAt*1000).toLocaleString(language)} : {}});
    root.querySelector("[name=channel]").value = value.channel;
    show(root, "[data-channel-risk]", value.channel !== "stable");
    show(root, "[data-source-update]", false);
    show(root, "[data-container-update]", value.installFormat === "container");
    text(root, "[data-release-notes]", value.releaseNotes);
    const history = root.querySelector('[data-release-history]');
    history.replaceChildren();
    for (const item of value.releases ?? []) {
      const row = document.createElement('details');
      const heading = document.createElement('summary');
      const title = document.createElement('strong');
      title.textContent = item.name;
      const meta = document.createElement('span');
      const date = item.publishedAt ? new Date(item.publishedAt) : null;
      meta.textContent = [item.version, item.channel, date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString(language) : '', item.installed ? ui('Installed','Instalada','Instalada') : ''].filter(Boolean).join(' · ');
      heading.append(title, meta);
      const body = document.createElement('div');
      const notes = document.createElement('pre');
      notes.textContent = item.notes || ui('No release notes.','Sem notas da versão.','Sin notas de versión.');
      body.append(notes);
      for (const [url, caption] of [[item.url, ui('Open release','Abrir release','Abrir versión')], [item.artifact?.url, ui('Download','Baixar','Descargar')]]) {
        try {
          const parsed = new URL(url);
          if (parsed.protocol !== 'https:' || parsed.hostname !== 'github.com' || parsed.username || parsed.password) continue;
          const anchor = document.createElement('a');
          anchor.href = parsed.href; anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; anchor.textContent = caption;
          body.append(anchor);
        } catch {}
      }
      row.append(heading, body); history.append(row);
    }
    if (!history.childElementCount) history.textContent = ui('Check for updates to load published releases.','Verifique as atualizações para carregar as releases publicadas.','Busca actualizaciones para cargar las versiones publicadas.');

    const link = root.querySelector("[data-release]");
    let valid = false;
    try {
      const u = new URL(value.releaseUrl);
      valid = u.protocol === "https:" && u.hostname === "github.com" && !u.username && !u.password;
      if (valid) link.href = u.href;
    } catch {
    }
    link.hidden = !valid;
    show(root, "[data-artifact]", !!value.artifact && value.installFormat === "win64");
    if (value.artifact) {
      text(root, "[data-artifact-name]", value.artifact.name);
      text(root, "[data-artifact-hash]", value.artifact.sha256);
      root.querySelector("[data-artifact-link]").href = value.artifact.url;
    }
  }
  async function refresh() {
    updates((await http.get('/api/admin/status')).updates);
  }
  async function pollUpdate() {
    pollTimer = null;
    if (!root.isConnected) return;
    try { await refresh(); }
    catch { text(root, '[data-automatic-progress]', ui('Waiting for the server to restart…','Aguardando o servidor reiniciar…','Esperando el reinicio del servidor…'));pollTimer = setTimeout(pollUpdate, 2000); }
  }
  function events() {
    const area = root.querySelector('[data-events]');
    area.replaceChildren();
    const q = normalize(root.querySelector('[data-event-search]').value);
    const category = root.querySelector('[data-event-category]').value;
    const all = report?.recent_events ?? [];
    const filtered = all.filter(e => (!category || e.event.split('.')[0] === category) && normalize(`${actions[e.event] ?? ''} ${e.event} ${JSON.stringify(e.fields)}`).includes(q));
    text(root, '[data-event-count]', `${filtered.length} / ${all.length}`);
    if (!filtered.length) {
      const empty = document.createElement('p');empty.className = 'diagnostics__empty';
      empty.textContent = all.length ? ui('No events match these filters.','Nenhum evento corresponde aos filtros.','Ningún evento coincide con los filtros.') : ui('No administrative activity recorded yet.','Nenhuma atividade administrativa registrada ainda.','Todavía no hay actividad administrativa registrada.');
      area.append(empty);
    }
    for (const e of filtered) {
      const fields = e.fields ?? {};
      const entry = document.createElement('details');entry.className = 'diagnostics__event';
      const heading = document.createElement('summary'), copy = document.createElement('div'), title = document.createElement('strong'), subtitle = document.createElement('span'), time = document.createElement('time');
      title.textContent = actions[e.event] ?? e.event;
      if (e.event === 'module.global_activation') title.textContent = fields.enabled ? ui('Languages activated','Idiomas ativados','Idiomas activados') : ui('Languages deactivated','Idiomas desativados','Idiomas desactivados');
      subtitle.textContent = [categories[e.event.split('.')[0]] ?? e.event.split('.')[0], fields.module, fields.version ? `v${fields.version}` : '', fields.status === 'failed' ? '' : fields.status, fields.channel].filter(Boolean).join(' · ');
      copy.append(title, subtitle);
      time.dateTime = new Date(e.ts * 1000).toISOString();time.textContent = new Date(e.ts * 1000).toLocaleString(language);
      heading.append(copy, time);entry.append(heading);
      if (fields.status === 'failed') {
        const badge = document.createElement('span');badge.className = 'diagnostics__failure';badge.textContent = ui('Failed','Falhou','Falló');heading.append(badge);
      }
      const detail = document.createElement('div'), code = document.createElement('code'), pre = document.createElement('pre');detail.className = 'diagnostics__detail';
      code.textContent = e.event;pre.textContent = JSON.stringify(fields, null, 2);detail.append(code,pre);entry.append(detail);area.append(entry);
    }
  }
  async function diagnostics() {
    report = await http.get('/api/admin/diagnostics');
    const area = root.querySelector('[data-metrics]');area.replaceChildren();
    const names = {campaigns:ui('Tables','Mesas','Mesas'),users:ui('Accounts','Contas','Cuentas'),backups:ui('Backups','Backups','Copias de seguridad')};
    for (const [group, values] of Object.entries(report.metrics)) for (const [key, value] of Object.entries(values)) {
      const metric = document.createElement('div'), number = document.createElement('strong'), name = document.createElement('span');metric.className = 'diagnostics__metric';
      name.textContent = names[key] ?? `${group} · ${key}`;number.textContent = typeof value === 'number' ? value.toLocaleString(language) : String(value);metric.append(name,number);area.append(metric);
    }
    const select = root.querySelector('[data-event-category]'), selected = select.value;
    while (select.options.length > 1) select.remove(1);
    for (const category of [...new Set(report.recent_events.map(e => e.event.split('.')[0]))].sort()) {
      const option = document.createElement('option');option.value = category;option.textContent = categories[category] ?? category;select.append(option);
    }
    select.value = [...select.options].some(o => o.value === selected) ? selected : '';
    events();
  }
  root.querySelector('[data-event-search]').oninput = events;
  root.querySelector('[data-event-category]').onchange = events;
  root.querySelectorAll("[data-tab]").forEach((button) => button.onclick = () => {
    root.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("administration__tab--active", b === button));
    root.querySelectorAll("[data-content]").forEach((el) => el.hidden = el.dataset.content !== button.dataset.tab);
    if (button.dataset.tab === "diagnostics") void run(root, diagnostics);
  });
  root.addEventListener("click", (event) => {
    const action = event.target.closest("[data-action]")?.dataset.action;
    if (action === "refresh") void run(root, async () => { await refresh(); if (!root.querySelector('[data-content=diagnostics]').hidden) await diagnostics(); });
    if (action === "diagnostics") void run(root, diagnostics);
    if (action === 'apply-update') void run(root, async () => {
      try { automatic = await http.post('/api/admin/updates/apply', {version: release.availableVersion}, {timeoutMs:null}); }
      catch (error) { throw Error(ui('Could not start the update. Check for local changes, another update or a changed release.','Não foi possível iniciar a atualização. Verifique alterações locais, outra atualização em curso ou mudança na release.','No se pudo iniciar la actualización. Comprueba cambios locales, otra actualización o cambios en la versión.')); }
      updates({...release, automatic});
    });
    if (action === "check-updates") void run(root, async () => updates(await http.post("/api/admin/updates/check", {}, { timeoutMs: null })));
    if (action === "export-diagnostics" && report) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      a.download = "gravewright-diagnostics.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1e3);
    }
  });
  root.addEventListener("submit", (event) => {
    const form = event.target.closest("form");
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    void run(root, async () => {
      if (form.dataset.form === "channel") {
        updates(await http.post("/api/admin/updates/channel", { channel: data.get("channel") }));
        return;
      }
      if (form.dataset.form === "import") {
        const file = data.get("archive");
        if (file.size > 256 * 1024 * 1024) throw Error("Choose a ZIP smaller than 256 MB.");
        const progress = form.querySelector("progress");
        progress.hidden = false;
        await http.upload("/api/admin/campaigns/import", data, (p) => progress.value = p);
        location.assign("/inside");
        return;
      }
      if (form.dataset.form === "clone") {
        const options = Object.fromEntries(["scenes", "actors", "items", "journals", "settings"].map((k) => [k, data.has(k)]));
        const result = await http.post(`/api/admin/campaigns/${data.get("source")}/clone/${preview ? "create" : "preview"}`, { title: data.get("title"), options }, { timeoutMs: null });
        if (preview) {
          location.assign("/inside");
          return;
        }
        preview = result.summary;
        summary(form.querySelector("[data-preview]"), preview);
        show(form, "[data-preview]", true);
        text(form, "button", "Create copy");
      }
    });
  });
  const clone = root.querySelector("[data-form=clone]");
  clone.onchange = (event) => {
    preview = void 0;
    show(clone, "[data-preview]", false);
    text(clone, "button", "Preview copy");
    if (event.target.name === "source") clone.querySelector("[name=title]").value = `${event.target.selectedOptions[0].textContent} \u2014 copy`;
  };
  void run(root, refresh);
}
function initialize() {
  for (const [selector, start] of [["[data-module-catalog]", modules], ["[data-administration]", administration], ["[data-privacy-settings]", privacySettings]]) document.querySelectorAll(selector).forEach((root) => {
    if (root.dataset.initialized) return;
    root.dataset.initialized = "true";
    start(root);
  });
}
new MutationObserver(initialize).observe(document.body, { subtree: true, childList: true });
initialize();
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-backup]");
  if (button) openBackups(button.dataset.backup, button.dataset.backupName);
});
function openBackups(id, name) {
  const scrim = document.createElement("div");
  scrim.className = "campaign-backups-scrim";
  Object.assign(scrim.style, { position: "fixed", inset: 0, zIndex: 1e3, display: "grid", placeItems: "center", background: "#0009" });
  scrim.innerHTML = `<div class="campaign-backups" role="dialog" aria-modal="true" aria-labelledby="backup-title"><header><h2 id="backup-title"></h2><button type="button" data-close>Close</button></header><p>Snapshots restore this campaign's native state on this host. Account sessions and JavaScript module packages/settings are separate.</p><a data-export download>Export portable campaign ZIP</a><p>Exports transfer native campaign content and supported assets; they do not include accounts, invitations or chat history.</p><form data-create><label>Snapshot name<input name="name" required minlength="2" maxlength="120" value="Before the next session" /></label><button>Create snapshot</button></form><p role="alert" hidden></p><p data-empty>No snapshots yet.</p><div data-snapshots></div><form data-confirm hidden><h3></h3><p data-warning></p><details><summary>Restoration details</summary><pre></pre></details><label><span data-prompt></span><input name="confirm" required autocomplete="off" /></label><button>Confirm</button><button type="button" data-cancel>Cancel</button></form></div>`;
  const root = scrim.firstElementChild, base = `/api/containers/${id}`;
  let confirmation;
  document.body.append(scrim);
  text(root, "h2", `Copies \xB7 ${name}`);
  root.querySelector("[data-export]").href = base + "/export";
  const close = () => {
    if (root.dataset.busy !== "true") {
      scrim.remove();
      document.querySelector(`[data-backup="${id}"]`)?.focus();
    }
  };
  root.querySelector("[data-close]").onclick = close;
  scrim.onkeydown = (e) => {
    if (e.key === "Escape") close();
  };
  async function refresh() {
    const { snapshots } = await http.get(base + "/snapshots");
    const list = root.querySelector("[data-snapshots]");
    list.replaceChildren();
    show(root, "[data-empty]", !snapshots.length);
    for (const item of snapshots) {
      const article = document.createElement("article"), copy = document.createElement("div"), strong = document.createElement("strong"), small = document.createElement("small");
      strong.textContent = item.name;
      small.textContent = new Date(item.createdAt).toLocaleString();
      copy.append(strong, small);
      article.append(copy);
      for (const action of ["restore", "delete"]) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = action === "restore" ? "Restore" : "Delete";
        b.onclick = () => run(root, async () => {
          let preview;
          if (action === "restore") preview = (await http.post(`${base}/snapshots/${item.id}/preview`, {})).preview;
          confirmation = { ...item, action };
          const form = root.querySelector("[data-confirm]");
          text(form, "h3", `${b.textContent} ${item.name}`);
          text(form, "[data-warning]", action === "restore" ? "This replaces the current native campaign state. All participants must leave the table first." : "This permanently removes this snapshot.");
          text(form, "pre", JSON.stringify(preview, null, 2));
          show(form, "details", !!preview);
          text(form, "[data-prompt]", `Type ${action.toUpperCase()}`);
          form.querySelector("input").value = "";
          show(root, "[data-confirm]", true);
        });
        article.append(b);
      }
      list.append(article);
    }
  }
  root.querySelector("[data-create]").onsubmit = (e) => {
    e.preventDefault();
    const name2 = new FormData(e.target).get("name");
    void run(root, async () => {
      await http.post(base + "/snapshots", { name: name2 }, { timeoutMs: null });
      await refresh();
    });
  };
  root.querySelector("[data-cancel]").onclick = () => show(root, "[data-confirm]", false);
  root.querySelector("[data-confirm]").onsubmit = (e) => {
    e.preventDefault();
    const confirm = new FormData(e.target).get("confirm");
    if (confirm !== confirmation.action.toUpperCase()) {
      text(root, "[role=alert]", "Type the confirmation exactly as shown.");
      show(root, "[role=alert]", true);
      return;
    }
    void run(root, async () => {
      await http.post(`${base}/snapshots/${confirmation.id}/${confirmation.action}`, { confirm }, { timeoutMs: null });
      show(root, "[data-confirm]", false);
      await refresh();
    });
  };
  void run(root, refresh);
}
