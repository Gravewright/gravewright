/** Let ProseMirror insert the character before opening the native resource picker. */
export function referenceTextInput(view, from, _to, typed, { isActive, choose }) {
  if (typed !== '@' || !isActive() || view.composing) return false;
  const position = view.state.doc.resolve(from);
  if (position.parent.type?.spec?.code || (view.state.storedMarks || position.marks?.() || []).some(mark => mark.type?.spec?.code)) return false;
  const before = position.parent.textBetween(0, position.parentOffset, '\n', '\ufffc');
  if (before && !/\s$/.test(before)) return false;
  queueMicrotask(() => {
    if (!isActive() || view.isDestroyed || view.composing) return;
    const state = view.state, end = from + 1;
    if (!state.selection.empty || state.selection.from !== end || state.selection.to !== end
      || state.doc.content.size < end || state.doc.textBetween(from, end, '\n', '\ufffc') !== '@') return;
    choose({ from, to: end, text: '@' });
  });
  return false;
}
