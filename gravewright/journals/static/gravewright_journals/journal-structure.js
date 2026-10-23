export const MAX_CHAPTERS = 128;
export const MAX_CHAPTER_DEPTH = 8;

export function validateChapters(chapters) {
  if (!Array.isArray(chapters) || chapters.length > MAX_CHAPTERS) throw Error('Use up to 128 chapters per journal.');
  const index = new Map();
  for (const chapter of chapters) {
    if (!chapter || typeof chapter.id !== 'string' || !/^[A-Za-z0-9_-]{1,40}$/.test(chapter.id) || index.has(chapter.id)
      || typeof chapter.name !== 'string' || !chapter.name.trim() || chapter.name.length > 80
      || !Number.isInteger(chapter.sortOrder) || Math.abs(chapter.sortOrder) > 2147483647
      || chapter.parentId !== null && typeof chapter.parentId !== 'string') throw Error('Invalid journal chapters.');
    index.set(chapter.id, chapter);
  }
  for (const chapter of chapters) {
    let current = chapter; const visited = new Set();
    while (current) {
      if (visited.has(current.id)) throw Error('A chapter cannot contain itself or one of its ancestors.');
      visited.add(current.id);
      if (visited.size > MAX_CHAPTER_DEPTH) throw Error('Use up to 8 chapter levels.');
      if (current.parentId !== null && !index.has(current.parentId)) throw Error('Chapter not found.');
      current = index.get(current.parentId);
    }
  }
  return chapters;
}

export function orderedChapters(chapters, parentId = null) {
  return chapters.filter(chapter => chapter.parentId === parentId).sort((a, b) => a.sortOrder - b.sortOrder || a.id.localeCompare(b.id));
}

export function chapterRows(chapters, parentId = null, depth = 0) {
  if (depth >= MAX_CHAPTER_DEPTH) return [];
  return orderedChapters(chapters, parentId).flatMap(chapter => [{ ...chapter, depth }, ...chapterRows(chapters, chapter.id, depth + 1)]);
}

export function chapterPath(chapters, id) {
  const index = new Map(chapters.map(chapter => [chapter.id, chapter])), names = [], seen = new Set();
  let current = index.get(id);
  while (current && !seen.has(current.id)) { names.unshift(current.name); seen.add(current.id); current = index.get(current.parentId); }
  return names.join(' / ');
}

/** Chapter navigation never reserves any string that a legacy page may use. */
export function selectedChapter(chapters, pages, selection) {
  const id = selection && typeof selection === 'object' ? selection.chapterId : pages.find(page => page.id === selection)?.chapterId;
  return chapters.find(chapter => chapter.id === id);
}

export function canParentChapter(chapters, id, parentId) {
  try {
    const existing = chapters.find(chapter => chapter.id === id);
    let newId = id || 'new_chapter', suffix = 0;
    while (!id && chapters.some(chapter => chapter.id === newId)) newId = `new_chapter_${++suffix}`;
    const candidate = existing ? chapters.map(chapter => chapter.id === id ? { ...chapter, parentId } : chapter)
      : [...chapters, { id: newId, name: 'Chapter', parentId, sortOrder: 0 }];
    validateChapters(candidate); return true;
  } catch { return false; }
}

export function saveChapter(chapters, chapter) {
  const existing = chapters.find(row => row.id === chapter.id), sameParent = existing?.parentId === chapter.parentId;
  const siblings = orderedChapters(chapters, chapter.parentId).filter(row => row.id !== chapter.id);
  const next = { id: chapter.id, name: chapter.name.trim(), parentId: chapter.parentId,
    sortOrder: sameParent ? existing.sortOrder : (siblings.at(-1)?.sortOrder || 0) + 10 };
  const result = existing ? chapters.map(row => row.id === next.id ? next : row) : [...chapters, next];
  return validateChapters(result);
}

export function reorderChapter(chapters, id, direction) {
  const chapter = chapters.find(row => row.id === id); if (!chapter) throw Error('Chapter not found.');
  const siblings = orderedChapters(chapters, chapter.parentId), from = siblings.findIndex(row => row.id === id), to = from + direction;
  if (![-1, 1].includes(direction) || to < 0 || to >= siblings.length) return chapters;
  [siblings[from], siblings[to]] = [siblings[to], siblings[from]];
  const orders = new Map(siblings.map((row, index) => [row.id, (index + 1) * 10]));
  return chapters.map(row => orders.has(row.id) ? { ...row, sortOrder: orders.get(row.id) } : row);
}

export function movePageToChapter(page, chapters, chapterId) {
  const chapter = chapters.find(row => row.id === chapterId);
  if (chapterId !== null && !chapter) throw Error('Chapter not found.');
  return { ...page, chapterId, category: chapter?.name || '' };
}

/** Remove only this container: its pages become unassigned, its children rise. */
export function deleteChapter(chapters, pages, id) {
  const chapter = chapters.find(row => row.id === id); if (!chapter) throw Error('Chapter not found.');
  const siblings = orderedChapters(chapters, chapter.parentId), children = orderedChapters(chapters, id);
  const promoted = siblings.flatMap(row => row.id === id ? children : [row]);
  const orders = new Map(promoted.map((row, index) => [row.id, (index + 1) * 10]));
  return { chapters: validateChapters(chapters.filter(row => row.id !== id).map(row => ({ ...row,
    parentId: row.parentId === id ? chapter.parentId : row.parentId,
    sortOrder: orders.get(row.id) ?? row.sortOrder }))),
  pages: pages.map(page => page.chapterId === id ? movePageToChapter(page, [], null) : page) };
}
