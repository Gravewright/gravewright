import test from 'node:test';
import assert from 'node:assert/strict';
import { referenceTextInput } from '../../gravewright/journals/static/gravewright_journals/reference-trigger.js';

const tick = () => new Promise(setImmediate);
function fixture(text, position = text.length) {
  let value = text, active = true, cursor = position + 1;
  const calls = [];
  const doc = { get content() { return { size: value.length + 2 }; },
    resolve(from) { return { parent: { textBetween: (start, end) => value.slice(start, end) }, parentOffset: from - 1 }; },
    textBetween(from, to) { return value.slice(from - 1, to - 1); } };
  const view = { composing: false, state: { doc, get selection() { return { empty: true, from: cursor, to: cursor }; } } };
  const options = { isActive: () => active, choose: range => calls.push(range) };
  return { view, options, calls, get value() { return value; }, set active(next) { active = next; }, set cursor(next) { cursor = next; },
    type(typed, from = position + 1, to = from) { const handled = referenceTextInput(view, from, to, typed, options);
      value = value.slice(0, from - 1) + typed + value.slice(to - 1); cursor = from + typed.length; return handled; },
    replace(next) { value = next; } };
}

test('typing @ at a paragraph boundary preserves native insertion and opens only after the committed character exists', async () => {
  const f = fixture(''); assert.equal(f.type('@'), false); assert.deepEqual(f.calls, []); assert.equal(f.value, '@');
  await tick(); assert.deepEqual(f.calls, [{ from: 1, to: 2, text: '@' }]); assert.equal(f.value, '@');
});

test('space and other whitespace permit references while emails and literal midword @ never open the picker', async () => {
  for (const text of ['Notes ', 'Notes\t', 'Notes\u00a0']) { const f = fixture(text); f.type('@'); await tick(); assert.equal(f.calls.length, 1, text); }
  for (const text of ['name', 'some-word', 'prefix.example']) { const f = fixture(text); f.type('@'); await tick(); assert.equal(f.calls.length, 0, text); assert.equal(f.value, text + '@'); }
  const pasted = fixture(''); pasted.type('name@example.com'); await tick(); assert.equal(pasted.calls.length, 0);
});

test('the boundary check uses the whole paragraph even when a new mark split makes @ a fresh text node', async () => {
  const f = fixture('formatted-name'); f.view.state.doc.resolve = () => ({ parentOffset: 14, parent: { textBetween: () => 'formatted-name' }, nodeBefore: { text: '' } });
  f.type('@'); await tick(); assert.equal(f.calls.length, 0);
});

test('closed or readonly editors and incomplete composition never open asynchronous pickers', async () => {
  const readonly = fixture(''); readonly.active = false; readonly.type('@');
  const disposed = fixture(''); disposed.type('@'); disposed.active = false;
  const composing = fixture(''); composing.view.composing = true; composing.type('@');
  const destroyed = fixture(''); destroyed.type('@'); destroyed.view.isDestroyed = true;
  await tick(); for (const f of [readonly, disposed, composing, destroyed]) assert.equal(f.calls.length, 0);
});

test('moving the cursor or replacing the trigger before the microtask cancels opening without mutating content', async () => {
  const moved = fixture(''); moved.type('@'); moved.cursor = 1;
  const replaced = fixture(''); replaced.type('@'); replaced.replace('x');
  await tick(); assert.deepEqual(moved.calls, []); assert.deepEqual(replaced.calls, []); assert.equal(moved.value, '@'); assert.equal(replaced.value, 'x');
});

test('typing @ over selected text keeps surrounding text and passes only the new trigger range for deferred selection', async () => {
  const f = fixture('Before replace after', 7); assert.equal(f.type('@', 8, 15), false);
  await tick(); assert.equal(f.value, 'Before @ after'); assert.deepEqual(f.calls, [{ from: 8, to: 9, text: '@' }]);
});

test('code blocks and both active inline-code mark sources retain literal @ without opening a picker', async () => {
  const block = fixture(''); block.view.state.doc.resolve = () => ({ parent: { type: { spec: { code: true } } } });
  const inline = fixture(''); inline.view.state.storedMarks = [{ type: { spec: { code: true } } }];
  const inherited = fixture(''); inherited.view.state.doc.resolve = () => ({ parent: {}, marks: () => [{ type: { spec: { code: true } } }] });
  for (const f of [block, inline, inherited]) assert.equal(f.type('@'), false);
  await tick(); for (const f of [block, inline, inherited]) { assert.equal(f.value, '@'); assert.equal(f.calls.length, 0); }
});
