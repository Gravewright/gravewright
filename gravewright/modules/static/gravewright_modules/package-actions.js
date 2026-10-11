const label = (en, pt, es) => document.documentElement.lang.startsWith('pt') ? pt : document.documentElement.lang.startsWith('es') ? es : en;

function confirmRemoval(pkg, preview) {
  if (!preview.tables.length) return Promise.resolve(true);
  if (!document.querySelector('[data-package-actions-style]')) {
    const style = document.createElement('link');
    style.rel = 'stylesheet';
    style.href = new URL('./package-actions.css', import.meta.url).href;
    style.dataset.packageActionsStyle = '';
    document.head.append(style);
  }
  return new Promise(resolve => {
    const previous = document.activeElement;
    const scrim = document.createElement('div');
    scrim.className = 'package-removal';
    scrim.innerHTML = '<section role="dialog" aria-modal="true" aria-labelledby="package-removal-title" aria-describedby="package-removal-message"><h2 id="package-removal-title"></h2><p id="package-removal-message"></p><ul></ul><p data-system-warning hidden></p><p data-question></p><footer><button type="button" data-cancel></button><button type="button" data-remove></button></footer></section>';
    scrim.querySelector('h2').textContent = label('Remove ', 'Remover ', 'Eliminar ') + (pkg.name || pkg.id);
    scrim.querySelector('#package-removal-message').textContent = preview.system
      ? label('This system is used by these tables:', 'Este sistema está sendo usado nas seguintes mesas:', 'Este sistema se usa en estas mesas:')
      : label('This module is used by these tables:', 'Este módulo está sendo usado nas seguintes mesas:', 'Este módulo se usa en estas mesas:');
    for (const table of preview.tables) {
      const item = document.createElement('li'); item.textContent = table.name;
      scrim.querySelector('ul').append(item);
    }
    const warning = scrim.querySelector('[data-system-warning]');
    warning.hidden = !preview.resetsSystem;
    warning.textContent = label('Tables using this system will use Gravewright PDF System.', 'As mesas que usam este sistema passarão a usar Gravewright PDF System.', 'Las mesas que usan este sistema pasarán a usar Gravewright PDF System.');
    scrim.querySelector('[data-question]').textContent = label('Remove it anyway?', 'Deseja remover mesmo assim?', '¿Eliminar de todos modos?');
    const cancel = scrim.querySelector('[data-cancel]'), remove = scrim.querySelector('[data-remove]');
    cancel.textContent = label('Cancel', 'Cancelar', 'Cancelar');
    remove.textContent = label('Remove', 'Remover', 'Eliminar');
    function close(confirmed) { scrim.remove(); resolve(confirmed); setTimeout(() => previous?.focus(), 0); }
    cancel.onclick = () => close(false);
    remove.onclick = () => close(true);
    scrim.onclick = event => { if (event.target === scrim) close(false); };
    scrim.onkeydown = event => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(false); }
      if (event.key === 'Tab') {
        event.preventDefault(); event.stopPropagation(); (document.activeElement === cancel ? remove : cancel).focus();
      }
    };
    document.body.append(scrim);
    cancel.focus();
  });
}

async function awaitRestart(http) {
  const deadline = Date.now() + 15 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    let progress;
    try { progress = (await http.get('/api/admin/status')).updates.automatic; }
    catch { continue; }
    if (progress.busy) continue;
    if (progress.stage !== 'complete') throw Error(label('Module operation failed.', 'Falha ao alterar o módulo.', 'Error al modificar el módulo.'));
    return;
  }
  throw Error(label('The server is still restarting.', 'O servidor ainda está reiniciando.', 'El servidor sigue reiniciándose.'));
}

export async function packageAction(http, pkg, action) {
  const payload = {id: pkg.id, version: pkg.version};
  if (action === 'remove') {
    const preview = await http.post('/api/module-packages/removal-preview', payload);
    if (!await confirmRemoval(pkg, preview)) return {cancelled: true};
    payload.confirmedTables = preview.tables.map(table => table.id);
  }
  let result;
  try { result = await http.post(`/api/module-packages/${action}`, payload, {timeoutMs: null}); }
  catch (error) {
    if (error.code === 'removal_confirmation_required') return packageAction(http, pkg, action);
    throw error;
  }
  if (result.restartRequired) {
    await awaitRestart(http);
    await http.post('/api/module-packages/remove', payload, {timeoutMs: null});
  }
  return result;
}
