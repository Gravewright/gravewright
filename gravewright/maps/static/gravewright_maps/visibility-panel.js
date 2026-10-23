const modeHints = {
  none: 'The whole map is visible to everyone. Nothing is hidden.',
  dynamic: 'Players only see what their tokens and lights reach. Walls block vision.',
  manual: 'Paint revealed areas by hand, independently of tokens and lights.',
};

/** Keep source keys stable when Translator changes an open or detached panel. */
export function mountVisibilityPanelText(panel, { translator, getPopup = () => undefined }) {
  let state, disposed = false;
  const text = (selector, source) => {
    const element = panel.querySelector(selector), value = translator.t(source);
    if (element.textContent !== value) element.textContent = value;
  };
  function dynamicText() {
    if (disposed || !state) return;
    text('[data-mode-hint]', modeHints[state.mode] || modeHints.none);
    text('[data-fog-status]', state.fogEnabled
      ? 'Manual lighting is active.'
      : 'Manual lighting is off. Choose an initial state to enable it.');
    text('[data-brush-hint]', state.shape === 'polygon'
      ? 'Click to add points. Click the first point to close.'
      : 'Alt+scroll on the map to adjust quickly.');
    text('[role=alert]', state.error || '');
  }
  function translate() {
    if (disposed) return;
    for (const element of panel.querySelectorAll('[data-visibility-text]')) {
      const value = translator.t(element.dataset.visibilityText);
      if (element.textContent !== value) element.textContent = value;
    }
    panel.setAttribute('aria-label', translator.t('Visibility'));
    for (const element of panel.querySelectorAll('[data-visibility-aria]'))
      element.setAttribute('aria-label', translator.t(element.dataset.visibilityAria));
    const actions = { detach: 'Detach', minimize: 'Minimize', close: 'Close' };
    for (const element of panel.querySelectorAll('[data-visibility-action]')) {
      const value = translator.t(actions[element.dataset.visibilityAction]);
      element.setAttribute('aria-label', value);
      element.setAttribute('title', value);
    }
    const popup = getPopup();
    if (popup && !popup.closed) {
      popup.document.title = translator.t('Visibility');
      popup.document.documentElement.lang = translator.locale;
    }
    dynamicText();
  }
  const stop = translator.onChange(translate);
  translate();
  return {
    update(next) { if (!disposed) { state = next; dynamicText(); } },
    destroy() { if (!disposed) { disposed = true; stop(); state = undefined; } },
  };
}
