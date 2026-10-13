import { mountModal } from '/static/gravewright_table/modal.js';

const POLL_MS = 1500;
const MAX_FAILURES = 10;

export function createUpdateProgress(root, {locale, requestStatus, onStatus}) {
  const ui = (en, pt, es) => locale === 'pt-BR' ? pt : locale === 'es' ? es : en;
  const stages = {
    requesting: ui('Confirming update', 'Confirmando atualização', 'Confirmando actualización'),
    queued: ui('Update queued', 'Atualização na fila', 'Actualización en cola'),
    download: ui('Downloading release', 'Baixando versão', 'Descargando versión'),
    verify: ui('Verifying download', 'Validando download', 'Verificando descarga'),
    dependencies: ui('Preparing dependencies', 'Preparando dependências', 'Preparando dependencias'),
    backup: ui('Saving a recovery copy', 'Salvando uma cópia de recuperação', 'Guardando una copia de recuperación'),
    migrate: ui('Applying migrations', 'Aplicando migrações', 'Aplicando migraciones'),
    replace: ui('Installing application files', 'Instalando arquivos da aplicação', 'Instalando archivos de la aplicación'),
    restart: ui('Restarting server', 'Reiniciando servidor', 'Reiniciando servidor'),
    rollback: ui('Restoring previous version', 'Restaurando versão anterior', 'Restaurando versión anterior'),
    rolled_back: ui('Previous version restored', 'Versão anterior restaurada', 'Versión anterior restaurada'),
    failed: ui('Update could not be completed', 'Não foi possível concluir a atualização', 'No se pudo completar la actualización'),
    complete: ui('Update complete', 'Atualização concluída', 'Actualización completada'),
  };
  const steps = [
    ['download', ['requesting', 'queued', 'download', 'verify'], ui('Download and verification', 'Download e verificação', 'Descarga y verificación')],
    ['dependencies', ['dependencies'], ui('Preparation', 'Preparação', 'Preparación')],
    ['backup', ['backup'], ui('Recovery copy', 'Cópia de recuperação', 'Copia de recuperación')],
    ['install', ['migrate', 'replace'], ui('Installation', 'Instalação', 'Instalación')],
    ['restart', ['restart', 'complete'], ui('Restart', 'Reinício', 'Reinicio')],
  ];
  let modal, state = {}, target = '', initialVersion = '', startedAt = 0, finishedAt = 0;
  let active = false, paused = false, disconnected = false, disposed = false, inFlight = false;
  let failures = 0, mismatches = 0, confirmingStart = false, emptyChecks = 0;
  let reloaded = false, timer, elapsedTimer, controller;

  const find = selector => modal?.querySelector(selector);
  const setText = (selector, value) => {
    const node = find(selector);
    if (node && node.textContent !== value) node.textContent = value;
  };
  const announceBusy = value => window.dispatchEvent(new CustomEvent('gravewright:core-update-progress', {detail: {active: value}}));
  const runnable = () => !disposed && root.isConnected && !document.hidden && navigator.onLine !== false;

  function ensureModal() {
    if (modal?.isConnected) return;
    modal = document.createElement('section');
    modal.className = 'gw-update-progress';
    modal.dataset.updateProgress = '';
    const titleId = 'update-progress-' + crypto.randomUUID();
    modal.setAttribute('aria-labelledby', titleId);
    // All markup and localized labels below are fixed application copy.
    // Release names, versions and server responses only enter textContent.
    modal.innerHTML = `
      <header class="gw-update-progress__header"><span class="gw-update-progress__symbol" aria-hidden="true">↻</span><div><p>${ui('Gravewright update', 'Atualização do Gravewright', 'Actualización de Gravewright')}</p><h2 id="${titleId}" data-update-stage></h2></div></header>
      <p class="gw-update-progress__version" data-update-target></p>
      <div class="gw-update-progress__meter"><progress data-update-progress-bar max="100" aria-label="${ui('Current step progress', 'Progresso da etapa atual', 'Progreso del paso actual')}"></progress><span data-update-progress-value aria-hidden="true" hidden></span></div>
      <ol class="gw-update-progress__steps" data-update-steps></ol>
      <p class="gw-update-progress__hint" data-update-hint></p>
      <p class="gw-update-progress__last" data-update-last hidden></p>
      <footer><span data-update-elapsed></span><div><button class="gw-button" type="button" data-update-reconnect hidden>${ui('Check connection', 'Verificar conexão', 'Comprobar conexión')}</button><button class="gw-button gw-button--primary" type="button" data-update-refresh hidden>${ui('Reload page', 'Recarregar página', 'Recargar página')}</button><button class="gw-button" type="button" data-update-close hidden>${ui('Close', 'Fechar', 'Cerrar')}</button></div></footer>`;
    const list = find('[data-update-steps]');
    for (const [key, , label] of steps) {
      const item = document.createElement('li');
      item.dataset.step = key;
      item.textContent = label;
      list.append(item);
    }
    modal.querySelector('header').setAttribute('role', 'status');
    modal.querySelector('header').setAttribute('aria-live', 'polite');
    find('[data-update-reconnect]').onclick = () => {
      failures = mismatches = 0; paused = false;
      render(); schedule(0);
    };
    find('[data-update-refresh]').onclick = () => location.reload();
    find('[data-update-close]').onclick = () => modal.close();
    modal.addEventListener('close', () => { modal.remove(); modal = undefined; }, {once: true});
    mountModal(modal, {canClose: () => !active || paused});
    modal.parentElement.classList.add('gw-update-progress-overlay');
  }

  function render() {
    if (!modal) return;
    const terminal = !active && ['complete', 'failed', 'rolled_back'].includes(state.stage);
    const success = terminal && state.stage === 'complete';
    const failed = terminal && state.stage !== 'complete';
    modal.dataset.state = success ? 'complete' : failed ? 'failed' : paused ? 'paused' : disconnected ? 'reconnecting' : 'working';
    const title = paused ? ui('Waiting for confirmation', 'Aguardando confirmação', 'Esperando confirmación')
      : confirmingStart ? stages.requesting
      : disconnected ? ui('Waiting for the server to restart', 'Aguardando o servidor reiniciar', 'Esperando el reinicio del servidor')
      : stages[state.stage] ?? stages.requesting;
    setText('[data-update-stage]', title);
    setText('[data-update-target]', target ? `Gravewright ${target}` : 'Gravewright');
    const elapsed = startedAt ? Math.max(0, Math.floor(((finishedAt || Date.now()) - startedAt) / 1000)) : 0;
    setText('[data-update-elapsed]', startedAt ? `${ui('Elapsed', 'Tempo decorrido', 'Tiempo transcurrido')} · ${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}` : '');
    let hint = ui('Keep the Runner open. This page will reload when the update finishes.', 'Mantenha o Runner aberto. Esta página será recarregada quando a atualização terminar.', 'Mantén el Runner abierto. Esta página se recargará cuando termine la actualización.');
    if (active && elapsed >= 120) hint = ui('This step can take a few minutes. Keep the Runner open; checking the connection does not start another update.', 'Esta etapa pode levar alguns minutos. Mantenha o Runner aberto; verificar a conexão não inicia outra atualização.', 'Este paso puede tardar unos minutos. Mantén el Runner abierto; comprobar la conexión no inicia otra actualización.');
    if (disconnected) hint = confirmingStart
      ? ui('The connection was interrupted before the request was confirmed. Checking the server does not send the update again.', 'A conexão foi interrompida antes de confirmar a solicitação. Verificar o servidor não envia a atualização novamente.', 'La conexión se interrumpió antes de confirmar la solicitud. Comprobar el servidor no vuelve a enviar la actualización.')
      : ui('The server is temporarily unavailable while the update finishes. Reconnection is automatic.', 'O servidor fica temporariamente indisponível enquanto conclui a atualização. A reconexão é automática.', 'El servidor está temporalmente no disponible mientras termina la actualización. La reconexión es automática.');
    if (paused) hint = ui('The result has not been confirmed yet. Check the Runner window or its logs, then try the connection again.', 'Ainda não foi possível confirmar o resultado. Confira a janela ou os logs do Runner e tente verificar a conexão novamente.', 'Todavía no se ha confirmado el resultado. Comprueba la ventana o los registros del Runner y vuelve a comprobar la conexión.');
    if (navigator.onLine === false && active) hint = ui('Your connection is offline. Checks resume when it returns.', 'Sua conexão está offline. As verificações serão retomadas quando ela voltar.', 'Tu conexión está sin conexión. Las comprobaciones se reanudarán cuando vuelva.');
    if (success) hint = reloaded ? ui('The server is ready with the updated version. Reloading the page…', 'O servidor está pronto com a versão atualizada. Recarregando a página…', 'El servidor está listo con la versión actualizada. Recargando la página…') : ui('The server is ready with the updated version.', 'O servidor está pronto com a versão atualizada.', 'El servidor está listo con la versión actualizada.');
    if (failed) hint = state.stage === 'rolled_back'
      ? ui('The update failed and the previous version was restored. Check the Runner log before trying again.', 'A atualização falhou e a versão anterior foi restaurada. Confira o log do Runner antes de tentar novamente.', 'La actualización falló y se restauró la versión anterior. Comprueba el registro del Runner antes de intentarlo de nuevo.')
      : ui('Check the Runner log and try again. The page can be closed without starting another update.', 'Confira o log do Runner e tente novamente. Você pode fechar esta janela sem iniciar outra atualização.', 'Comprueba el registro del Runner e inténtalo de nuevo. Puedes cerrar esta ventana sin iniciar otra actualización.');
    setText('[data-update-hint]', state.startError || hint);
    setText('[data-update-last]', `${ui('Last confirmed step', 'Última etapa confirmada', 'Último paso confirmado')}: ${stages[state.stage] ?? stages.requesting}`);
    find('[data-update-last]').hidden = !disconnected;
    const received = Number(state.received), total = Number(state.total);
    const determinate = !disconnected && state.stage === 'download' && Number.isFinite(received) && Number.isFinite(total) && total > 0;
    const percentage = success ? 100 : determinate ? Math.max(0, Math.min(100, Math.floor(100 * received / total))) : null;
    const bar = find('[data-update-progress-bar]');
    if (percentage === null) bar.removeAttribute('value'); else bar.value = percentage;
    setText('[data-update-progress-value]', percentage === null ? '' : `${percentage}%`);
    find('[data-update-progress-value]').hidden = percentage === null;
    const index = steps.findIndex(([, values]) => values.includes(state.stage));
    for (const [position, item] of [...find('[data-update-steps]').children].entries()) {
      item.dataset.state = success || position < index ? 'done' : position === index ? 'active' : 'pending';
      if (position === index && !terminal) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
    }
    find('[data-update-close]').hidden = active && !paused;
    find('[data-update-reconnect]').hidden = !active || (!paused && elapsed < 120);
    find('[data-update-reconnect]').disabled = inFlight || navigator.onLine === false;
    find('[data-update-refresh]').hidden = !success;
  }

  function schedule(delay = POLL_MS) {
    clearTimeout(timer);
    timer = undefined;
    if (!active || paused || !runnable()) return;
    timer = setTimeout(poll, delay);
  }

  async function poll() {
    timer = undefined;
    if (!active || paused || inFlight || !runnable()) return;
    inFlight = true;
    controller = new AbortController();
    render();
    try {
      const value = await requestStatus(controller.signal);
      if (!disposed) onStatus(value);
    } catch (error) {
      if (disposed || error.name === 'AbortError') return;
      disconnected = true;
      failures += 1;
      paused = failures >= MAX_FAILURES || [401, 403].includes(error.status);
      schedule(Math.min(10000 * 2 ** (failures - 1), 30000));
    } finally {
      inFlight = false;
      controller = undefined;
      render();
    }
  }

  function begin(version) {
    target = version || '';
    startedAt = Date.now();
    finishedAt = 0;
    active = true; paused = disconnected = false;
    failures = mismatches = emptyChecks = 0;
    confirmingStart = false;
    announceBusy(true);
    clearInterval(elapsedTimer);
    elapsedTimer = setInterval(render, 1000);
    ensureModal();
  }

  function update(value) {
    if (disposed) return;
    initialVersion ||= value.currentVersion || value.installedRelease?.version || '';
    if (confirmingStart) {
      const progress = value.automatic ?? {};
      // Intermediate supervisor stages omit the version. An active job is
      // enough to resume tracking; completion still confirms the installed version.
      const running = progress.busy && (!progress.version || progress.version === target);
      const completed = !progress.busy && progress.stage === 'complete' && (value.currentVersion || value.installedRelease?.version) === target;
      if (!running && !completed) {
        failures = 0;
        disconnected = true;
        if (++emptyChecks >= 3) {
          failStart(ui('The server is available, but no update to this version is running. Check the release and try again.', 'O servidor está disponível, mas nenhuma atualização para esta versão está em andamento. Verifique a versão e tente novamente.', 'El servidor está disponible, pero no hay ninguna actualización a esta versión en curso. Comprueba la versión e inténtalo de nuevo.'));
        } else { render(); schedule(5000); }
        return;
      }
      confirmingStart = false;
    }
    state = value.automatic ?? state;
    if (!active) {
      if (!state.busy) return;
      begin(state.version || value.availableVersion);
    }
    failures = 0; paused = disconnected = false;
    target ||= state.version || value.availableVersion || '';
    const terminal = !state.busy && ['complete', 'failed', 'rolled_back'].includes(state.stage);
    if (terminal && state.stage === 'complete' && target && (value.currentVersion || value.installedRelease?.version) !== target) {
      paused = ++mismatches >= 3;
      disconnected = true;
      render(); schedule(5000); return;
    }
    if (terminal) {
      active = false;
      finishedAt = Date.now();
      clearTimeout(timer); clearInterval(elapsedTimer);
      announceBusy(false);
      if (state.stage === 'complete' && target && target !== initialVersion && !reloaded) {
        reloaded = true;
        timer = setTimeout(() => { if (!disposed && root.isConnected) location.reload(); }, 1500);
      }
    } else schedule();
    render();
  }

  function start(version) {
    state = {stage: 'requesting', busy: true};
    begin(version);
    render();
  }

  function failStart(message) {
    active = false;
    paused = disconnected = confirmingStart = false;
    finishedAt = Date.now();
    state = {stage: 'failed', startError: message};
    clearTimeout(timer); clearInterval(elapsedTimer);
    announceBusy(false);
    render();
  }

  function awaitConfirmation() {
    confirmingStart = disconnected = true;
    render(); schedule(10000);
  }

  function resume() {
    if (!active) return;
    render();
    if (runnable()) schedule(2000); else clearTimeout(timer);
  }
  document.addEventListener('visibilitychange', resume);
  window.addEventListener('online', resume);
  window.addEventListener('offline', resume);
  const observer = new MutationObserver(() => { if (!root.isConnected) dispose(); });
  observer.observe(document.documentElement, {childList: true, subtree: true});
  function dispose() {
    if (disposed) return;
    disposed = true;
    clearTimeout(timer); clearInterval(elapsedTimer);
    controller?.abort(); observer.disconnect();
    document.removeEventListener('visibilitychange', resume);
    window.removeEventListener('online', resume);
    window.removeEventListener('offline', resume);
    modal?.close(true);
    announceBusy(false);
  }
  return {update, start, failStart, awaitConfirmation, dispose, isActive: () => active,
    hasProgress: () => active || startedAt > 0,
    open: () => { ensureModal(); render(); }};
}
