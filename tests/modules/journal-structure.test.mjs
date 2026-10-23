import test from 'node:test';
import assert from 'node:assert/strict';
import { MAX_CHAPTERS, validateChapters, chapterRows, chapterPath, selectedChapter, canParentChapter, saveChapter, reorderChapter,
  deleteChapter, movePageToChapter } from '../../gravewright/journals/static/gravewright_journals/journal-structure.js';

const chapter = (id, parentId = null, sortOrder = 10) => ({ id, name: id, parentId, sortOrder });

test('empty chapters persist independently of pages and retain identity through rename and reparenting', () => {
  let chapters = saveChapter([], { id: 'chapter', name: 'Empty chapter', parentId: null });
  assert.deepEqual(chapters, [{ id: 'chapter', name: 'Empty chapter', parentId: null, sortOrder: 10 }]);
  chapters = saveChapter(chapters, { id: 'parent', name: 'Parent', parentId: null });
  chapters = saveChapter(chapters, { id: 'chapter', name: 'Renamed chapter', parentId: 'parent' });
  const restored = JSON.parse(JSON.stringify({ chapters, sections: [] }));
  assert.equal(restored.sections.length, 0); assert.equal(restored.chapters.length, 2);
  assert.equal(chapterPath(restored.chapters, 'chapter'), 'Parent / Renamed chapter');
});

test('pages belong to exactly one selected existing chapter or none without creating a category container', () => {
  const chapters = [chapter('root'), chapter('child', 'root')], content = { doc: { type: 'doc', content: [{ type: 'text', text: 'Authored notes' }] } };
  const page = { id: 'page', title: 'Page', chapterId: 'root', category: 'root', content, assetId: 'asset' };
  const moved = movePageToChapter(page, chapters, 'child');
  assert.equal(moved.chapterId, 'child'); assert.equal(moved.category, 'child'); assert.equal(moved.content, content);
  const unassigned = movePageToChapter(moved, chapters, null);
  assert.equal(unassigned.chapterId, null); assert.equal(unassigned.category, ''); assert.equal(unassigned.assetId, 'asset');
  assert.equal(chapters.length, 2); assert.equal(page.chapterId, 'root');
  assert.throws(() => movePageToChapter(page, chapters, 'new-category'), /Chapter not found/);
});

test('chapter selectors expose complete paths in stable sibling order', () => {
  const chapters = [chapter('second', null, 20), chapter('grandchild', 'child'), chapter('child', 'first'), chapter('first')];
  assert.deepEqual(chapterRows(chapters).map(row => [row.id, row.depth]), [['first', 0], ['child', 1], ['grandchild', 2], ['second', 0]]);
  assert.equal(chapterPath(chapters, 'grandchild'), 'first / child / grandchild');
});

test('legacy page IDs containing chapter prefixes remain pages and chapter navigation cannot collide with any string ID', () => {
  const chapters = [chapter('synthetic-root'), chapter('actual-parent')],
    pages = [{ id: 'chapter:synthetic-root', chapterId: 'actual-parent', title: 'A real legacy page' }];
  assert.equal(selectedChapter(chapters, pages, 'chapter:synthetic-root').id, 'actual-parent');
  assert.equal(selectedChapter(chapters, pages, { chapterId: 'synthetic-root' }).id, 'synthetic-root');
  assert.equal(selectedChapter(chapters, pages, 'chapter:actual-parent'), undefined);
  assert.equal(selectedChapter(chapters, pages, 'unmatched'), undefined);
});

test('reparenting rejects self and descendants and accounts for the whole moved subtree depth', () => {
  const chapters = Array.from({ length: 8 }, (_, index) => chapter(`level${index}`, index ? `level${index - 1}` : null));
  assert.equal(canParentChapter(chapters, 'level0', 'level7'), false);
  assert.equal(canParentChapter(chapters, 'level3', 'level3'), false);
  assert.equal(canParentChapter(chapters, null, 'level7'), false);
  assert.equal(canParentChapter(chapters, null, 'level6'), true);
  assert.equal(canParentChapter([...chapters, chapter('sibling')], 'level0', 'sibling'), false);
  assert.equal(canParentChapter(chapters, 'level4', null), true);
  assert.throws(() => saveChapter(chapters, { ...chapters[0], parentId: 'level7' }), /cannot contain/);
});

test('deleting only the container preserves all authored content, unassigns its pages and promotes immediate children', () => {
  const chapters = [chapter('root'), chapter('delete', 'root', 10), chapter('next', 'root', 20), chapter('child', 'delete'), chapter('grandchild', 'child')];
  const rich = { type: 'gwResourceLink', attrs: { reference: { unavailable: true, key: 'opaque-private-link' } } };
  const pages = [{ id: 'direct', chapterId: 'delete', category: 'delete', content: rich },
    { id: 'child-page', chapterId: 'child', category: 'child', src: '/protected/image' },
    { id: 'free', chapterId: null, category: '', title: 'Unassigned page' }];
  const next = deleteChapter(chapters, pages, 'delete');
  assert.equal(next.chapters.some(row => row.id === 'delete'), false);
  assert.equal(next.chapters.find(row => row.id === 'child').parentId, 'root');
  assert.equal(next.chapters.find(row => row.id === 'grandchild').parentId, 'child');
  assert.deepEqual(next.pages[0], { ...pages[0], chapterId: null, category: '' }); assert.equal(next.pages[0].content, rich);
  assert.equal(next.pages[1], pages[1]); assert.equal(next.pages[2], pages[2]); assert.equal(pages[0].chapterId, 'delete');
  assert.deepEqual(chapterRows(next.chapters).map(row => row.id), ['root', 'child', 'grandchild', 'next']);
});

test('deleting a root promotes its children to roots and preserves unrelated empty chapters and nested pages', () => {
  const chapters = [chapter('root'), chapter('empty', null, 20), chapter('child', 'root')],
    pages = [{ id: 'nested-page', chapterId: 'child', title: 'Keep this page', content: { text: 'Authored content' } }];
  const next = deleteChapter(chapters, pages, 'root');
  assert.deepEqual(chapterRows(next.chapters).map(row => [row.id, row.parentId]), [['child', null], ['empty', null]]);
  assert.equal(next.pages[0], pages[0]); assert.equal(chapters[2].parentId, 'root');
});

test('sibling ordering moves only the requested chapter and preserves parentage and nested order', () => {
  const chapters = [chapter('first'), chapter('second', null, 20), chapter('child', 'first'), chapter('other-child', 'first', 20)];
  const next = reorderChapter(chapters, 'second', -1);
  assert.deepEqual(chapterRows(next).map(row => row.id), ['second', 'first', 'child', 'other-child']);
  assert.equal(next.find(row => row.id === 'child').parentId, 'first');
  assert.equal(reorderChapter(next, 'second', -1), next);
  assert.deepEqual(chapterRows(reorderChapter(next, 'second', 1)).map(row => row.id), ['first', 'child', 'other-child', 'second']);
});

test('bounded validation rejects duplicate identifiers, orphan parents and invalid names without mutating drafts', () => {
  const original = [chapter('valid')];
  assert.throws(() => validateChapters([...original, chapter('valid')]), /Invalid/);
  assert.throws(() => saveChapter(original, { id: 'orphan', name: 'Orphan', parentId: 'missing' }), /not found/);
  assert.throws(() => saveChapter(original, { id: 'blank', name: '   ', parentId: null }), /Invalid/);
  assert.throws(() => saveChapter(original, { id: 'invalid id', name: 'Name', parentId: null }), /Invalid/);
  assert.throws(() => validateChapters([{ ...chapter('valid'), id: 123 }]), /Invalid/);
  assert.equal(canParentChapter([chapter('new_chapter'), chapter('new_chapter_1')], null, 'new_chapter'), true);
  assert.deepEqual(original, [chapter('valid')]);
  const full = Array.from({ length: MAX_CHAPTERS }, (_, index) => chapter(`chapter${index}`, null, index * 10));
  assert.equal(canParentChapter(full, null, null), false); assert.equal(canParentChapter(full, 'chapter0', 'chapter1'), true);
  assert.throws(() => saveChapter(full, { id: 'overflow', name: 'Overflow', parentId: null }), /128/);
});
