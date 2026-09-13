// Translate browser-created interface controls from the installed, static catalog.
// Values, editable documents, resource names and chat are deliberately excluded.
const config = document.getElementById('gravewright-language');
if (config) {
  const {id, messages} = JSON.parse(config.textContent);
  const translated = new Set(Object.values(messages));
  const missing = new Set();
  const originals = new WeakMap();
  const attributes = new WeakMap();
  const excluded = 'script,style,code,pre,textarea,[contenteditable],[data-text], [translate=no],#chat-log,[data-message-id],.chat-message,.journal-editor,.journal-content,.gw-campaign,.directory-entry,.game-directory__item,.module-catalog__details,.campaign-hub__owner-copy,.player-home__account,.gw-avatar,[data-member-id]';
  const controls = '.module-catalog [data-status],button,label,option,legend,summary,h1,h2,h3,h4,[role=alert],[role=status],form p,dialog p,.directory-dialog header,.module-catalog__header p,.module-catalog__setup p';
  const dynamicOptions = 'select[name=source],select[name=template],select[name=actorId],select[name=folderId]';
  const patterns = Object.entries(messages).filter(([key]) => /\{[A-Za-z_]/.test(key)).map(([key, translation]) => {
    const names = [];
    const parts = key.split(/(\{[A-Za-z_][A-Za-z0-9_.]*\})/g);
    const pattern = parts.map(part => {
      if (/^\{[A-Za-z_][A-Za-z0-9_.]*\}$/.test(part)) { names.push(part); return '(.+?)'; }
      return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }).join('');
    return {regex: new RegExp('^' + pattern + '$'), names, translation};
  });
  function value(text) {
    const key = text.trim();
    if (Object.hasOwn(messages, key)) return text.replace(key, messages[key]);
    for (const {regex, names, translation} of patterns) {
      const match = key.match(regex);
      if (match) return text.replace(key, () => translation.replace(/\{[A-Za-z_][A-Za-z0-9_.]*\}/g, name => match[names.indexOf(name) + 1]));
    }
    if (id !== 'en' && key && /[A-Za-z]/.test(key) && !translated.has(key)) missing.add(key);
    return text;
  }
  function element(el) {
    if (el.closest(excluded)) return;
    for (const attr of ['title', 'aria-label', 'placeholder', 'alt']) {
      if (el.hasAttribute(attr) && !el.hasAttribute(`data-attr:${attr}`)) {
        const before = el.getAttribute(attr);
        const known = attributes.get(el) || {};
        if (known[attr] === before) continue;
        const after = value(before);
        known[attr] = after; attributes.set(el, known);
        if (before !== after) el.setAttribute(attr, after);
      }
    }
  }
  function text(node) {
    const el = node.parentElement;
    if (!el || el.closest(excluded) || !el.closest(controls) || el.closest(dynamicOptions)) return;
    if (originals.get(node) === node.data) return;
    const after = value(node.data);
    originals.set(node, after);
    if (node.data !== after) node.data = after;
  }
  function scan(root) {
    if (root.nodeType === Node.TEXT_NODE) return text(root);
    if (root.nodeType !== Node.ELEMENT_NODE || root.closest(excluded)) return;
    element(root);
    for (const el of root.querySelectorAll('[title],[aria-label],[placeholder],[alt]')) element(el);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) text(walker.currentNode);
  }
  new MutationObserver((changes) => {
    for (const change of changes) {
      if (change.type === 'characterData') text(change.target);
      else if (change.type === 'attributes') element(change.target);
      else for (const node of change.addedNodes) scan(node);
    }
  }).observe(document.body, {subtree:true, childList:true, characterData:true, attributes:true,
                            attributeFilter:['title','aria-label','placeholder','alt']});
  scan(document.body);
  document.documentElement.lang = id;
  window.gravewrightTranslator = Object.freeze({locale:id, missing:() => [...missing].sort()});
}
