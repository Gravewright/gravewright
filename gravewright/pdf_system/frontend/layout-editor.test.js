import { test } from 'node:test';
import assert from 'node:assert/strict';
import { layoutBounds, moveLayoutFields, alignLayoutFields, distributeLayoutFields, snapLayoutRect } from './layout-editor.js';

const field = (id, changes = {}) => ({ id, source: 'template:generic', page: 1,
    x: .1, y: .1, width: .1, height: .05, ...changes });
const apply = (fields, updates) => fields.map(field => ({ ...field,
    ...(updates.find(update => update.id === field.id)?.changes || {}) }));
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-10, `${actual} differs from ${expected}`);

test('selection bounds ignore duplicate or invalid geometry without modifying fields', () => {
    const rows = [field('one'), field('two', { x: .5, y: .3, width: .2 })];
    const before = structuredClone(rows);
    assert.deepEqual(layoutBounds(rows), { x: .1, y: .1, width: .6, height: .24999999999999997 });
    assert.equal(layoutBounds([field('bad', { width: Infinity })]), null);
    assert.deepEqual(moveLayoutFields([...rows, rows[0]], 0, 0), []);
    assert.deepEqual(rows, before);
});

test('moving a group against a boundary preserves its relative spacing', () => {
    const rows = [field('one', { x: .1 }), field('two', { x: .6 })];
    const moved = apply(rows, moveLayoutFields(rows, 4, -4));
    near(moved[0].x, .4); near(moved[1].x, .9);
    near(moved[1].x - moved[0].x, .5);
    assert.equal(moved[0].y, 0); assert.equal(moved[1].y, 0);
    assert.deepEqual(moveLayoutFields(rows, NaN, 1), []);
});

test('movement snapping moves the group once rather than changing internal gaps', () => {
    const rows = [field('one', { x: .103 }), field('two', { x: .317 })];
    const moved = apply(rows, moveLayoutFields(rows, .019, .013, { x: .02, y: .02 }));
    near(moved[0].x, .12); near(moved[1].x, .334);
    near(moved[0].y, .12); near(moved[1].y, .12);
});

test('spread and source operations clamp each page independently', () => {
    const rows = [field('one'), field('two', { x: .8, page: 2 }), field('three', { source: 'template:other' })];
    const moved = apply(rows, moveLayoutFields(rows, .3, 0));
    near(moved[0].x, .4); near(moved[1].x, .9); near(moved[2].x, .4);
    assert.deepEqual(alignLayoutFields(rows, 'left'), []);
});

test('all six alignments retain identity, dimensions and the opposite axis', () => {
    const rows = [field('one'), field('two', { x: .5, y: .4, width: .2, height: .1 })];
    for (const alignment of ['left', 'right', 'top', 'bottom', 'center-x', 'center-y']) {
        const aligned = apply(rows, alignLayoutFields(rows, alignment));
        for (let i = 0; i < rows.length; i++) {
            assert.equal(aligned[i].id, rows[i].id);
            assert.equal(aligned[i].width, rows[i].width);
            assert.equal(aligned[i].height, rows[i].height);
            assert.equal(aligned[i][['left', 'right', 'center-x'].includes(alignment) ? 'y' : 'x'],
                rows[i][['left', 'right', 'center-x'].includes(alignment) ? 'y' : 'x']);
        }
        if (alignment === 'left') near(aligned[0].x, aligned[1].x);
        if (alignment === 'right') near(aligned[0].x + aligned[0].width, aligned[1].x + aligned[1].width);
        if (alignment === 'top') near(aligned[0].y, aligned[1].y);
        if (alignment === 'bottom') near(aligned[0].y + aligned[0].height, aligned[1].y + aligned[1].height);
        if (alignment === 'center-x') near(aligned[0].x + aligned[0].width / 2, aligned[1].x + aligned[1].width / 2);
        if (alignment === 'center-y') near(aligned[0].y + aligned[0].height / 2, aligned[1].y + aligned[1].height / 2);
    }
    assert.deepEqual(alignLayoutFields(rows, 'unknown'), []);
});

test('horizontal distribution keeps outer edges fixed and equalizes available gaps', () => {
    const rows = [field('last', { x: .8 }), field('middle', { x: .2, width: .2 }), field('first', { x: .1 })];
    const result = apply(rows, distributeLayoutFields(rows, 'horizontal'));
    const [first, middle, last] = [...result].sort((a, b) => a.x - b.x);
    near(first.x, .1); near(last.x, .8);
    near(middle.x - first.x - first.width, last.x - middle.x - middle.width);
    assert.deepEqual(result.map(field => field.id), rows.map(field => field.id));
});

test('vertical distribution keeps page and source groups separate', () => {
    const rows = [field('one'), field('two', { y: .15 }), field('three', { y: .7 }), field('other', { page: 2 })];
    const result = apply(rows, distributeLayoutFields(rows, 'vertical'));
    near(result[1].y, .4); assert.deepEqual(result[3], rows[3]);
    assert.deepEqual(distributeLayoutFields(rows.slice(0, 2), 'vertical'), []);
});

test('distribution does not force overlapping selections outside the page', () => {
    const rows = [field('one', { width: .8 }), field('two', { x: .11, width: .8 }), field('three', { x: .12, width: .8 })];
    assert.deepEqual(distributeLayoutFields(rows, 'horizontal'), []);
});

test('snapping rectangles remains valid at page edges and for tiny gestures', () => {
    const result = snapLayoutRect({ x: .013, y: .027, width: .096, height: .082 }, { x: .02, y: .02 });
    near(result.x, .02); near(result.y, .02); near(result.width, .08); near(result.height, .08);
    const edge = snapLayoutRect({ x: .999, y: .999, width: .1, height: .1 }, { x: .02, y: .02 });
    near(edge.x + edge.width, 1); near(edge.y + edge.height, 1);
    assert.ok(edge.width >= .001 - 1e-12 && edge.height >= .001 - 1e-12);
    assert.equal(snapLayoutRect({ x: Infinity, y: 0, width: .1, height: .1 }), null);
});
