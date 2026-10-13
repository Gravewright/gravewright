// Release bodies are publisher-controlled Markdown. Build DOM nodes without HTML.
function localizedNotes(value, locale) {
  const notes = String(value ?? '').replace(/\r\n?/g, '\n');
  const boundary = /^##\s+Portugu[eê]s(?: \(Brasil\))?\s*$/mi.exec(notes);
  if (!boundary) return notes.trim();
  return (locale === 'pt-BR' ? notes.slice(boundary.index + boundary[0].length)
    : notes.slice(0, boundary.index).replace(/\n---\s*$/, '')).trim();
}

function documentationBase(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password) return;
    const release = /^\/([^/]+)\/([^/]+)\/releases\/tag\/(v?([0-9][0-9A-Za-z.-]*))$/.exec(url.pathname);
    return url.hostname === 'github.com' && release
      ? `${url.origin}/${release[1]}/${release[2]}/blob/${release[3]}/docs/releases/${release[4]}.md` : url.href;
  } catch {}
}

function inline(parent, value, base) {
  const document = parent.ownerDocument;
  const pattern = /`([^`\n]+)`|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*|\[([^\]\n]+)\]\(([^)\s]+)\)/g;
  let offset = 0;
  for (const match of value.matchAll(pattern)) {
    parent.append(document.createTextNode(value.slice(offset, match.index)));
    const [raw, code, strong, emphasis, label, destination] = match;
    let element;
    if (code !== undefined || strong !== undefined || emphasis !== undefined) {
      element = document.createElement(code !== undefined ? 'code' : strong !== undefined ? 'strong' : 'em');
      element.textContent = code ?? strong ?? emphasis;
    } else {
      try {
        const url = new URL(destination, base);
        if (url.protocol === 'https:' && !url.username && !url.password) {
          element = document.createElement('a');
          element.href = url.href; element.target = '_blank'; element.rel = 'noopener noreferrer';
          element.textContent = label;
        }
      } catch {}
    }
    parent.append(element ?? document.createTextNode(raw));
    offset = match.index + raw.length;
  }
  parent.append(document.createTextNode(value.slice(offset)));
}

export function renderReleaseNotes(target, value, {locale = 'en', url, title} = {}) {
  let notes = localizedNotes(value, locale);
  const heading = /^#\s+(.+)\n+/.exec(notes);
  if (heading && heading[1].trim() === title?.trim()) notes = notes.slice(heading[0].length).trim();
  const document = target.ownerDocument, fragment = document.createDocumentFragment();
  const base = documentationBase(url);
  let paragraph = [], list, lastItem, code;
  const flush = () => {
    if (paragraph.length) {
      const element = document.createElement('p');
      inline(element, paragraph.join(' '), base); fragment.append(element); paragraph = [];
    }
  };
  for (const line of notes.split('\n')) {
    if (/^\s*```/.test(line)) {
      flush(); list = lastItem = undefined;
      if (code) code = undefined;
      else {
        const pre = document.createElement('pre'); code = document.createElement('code');
        pre.append(code); fragment.append(pre);
      }
      continue;
    }
    if (code) { code.append(document.createTextNode(line + '\n')); continue; }
    if (!line.trim()) { flush(); list = lastItem = undefined; continue; }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    const item = /^\s*(?:([-*+])|([0-9]+)\.)\s+(.+)$/.exec(line);
    if (heading) {
      flush(); list = lastItem = undefined;
      const element = document.createElement('h' + heading[1].length);
      inline(element, heading[2], base); fragment.append(element);
    } else if (/^\s*(?:---+|\*\*\*+)\s*$/.test(line)) {
      flush(); list = lastItem = undefined; fragment.append(document.createElement('hr'));
    } else if (item) {
      flush();
      const kind = item[2] ? 'ol' : 'ul';
      if (!list || list.localName !== kind) { list = document.createElement(kind); fragment.append(list); }
      lastItem = document.createElement('li'); inline(lastItem, item[3], base); list.append(lastItem);
    } else if (/^\s{2,}\S/.test(line) && lastItem) {
      lastItem.append(document.createTextNode(' ')); inline(lastItem, line.trim(), base);
    } else if (/^>\s?/.test(line)) {
      flush(); list = lastItem = undefined;
      const quote = document.createElement('blockquote'); inline(quote, line.replace(/^>\s?/, ''), base); fragment.append(quote);
    } else { list = lastItem = undefined; paragraph.push(line.trim()); }
  }
  flush();
  target.replaceChildren(fragment);
  return !!notes;
}
