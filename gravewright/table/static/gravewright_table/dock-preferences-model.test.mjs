import test from 'node:test';
import assert from 'node:assert/strict';
import { dockStorageKey, normalizeDockPreferences, moveDockEntry } from './dock-preferences-model.js';

const entries = [
    { id: 'panel:chat', group: 'panels', defaultPlacement: 'dock' },
    { id: 'panel:actors', group: 'panels', defaultPlacement: 'dock' },
    { id: 'panel:scenes', group: 'panels', defaultPlacement: 'menu' },
    { id: 'tool:game:select', group: 'tools:game', defaultPlacement: 'dock' },
    { id: 'tool:game:measure', group: 'tools:game', defaultPlacement: 'dock' },
];

test('preferences are isolated by both profile and table, including delimiter-like identifiers', () => {
    const keys = [['alice', 'one'], ['bob', 'one'], ['alice', 'two'], ['a:b', 'c'], ['a', 'b:c'], ['a.b', 'c'], ['a', 'b.c']]
        .map(([profile, table]) => dockStorageKey(profile, table));
    assert.equal(new Set(keys).size, keys.length);
});

test('malformed or future preferences restore defaults without introducing controls', () => {
    const defaults = normalizeDockPreferences(null, entries);
    for (const value of [null, false, [], { version: 2 }, { version: 1, order: { panels: true }, placement: {} }])
        assert.deepEqual(normalizeDockPreferences(value, entries), defaults);
    const normalized = normalizeDockPreferences({ version: 1,
        order: { panels: ['panel:scenes', 'unknown', 'panel:scenes', 'tool:game:select'] },
        placement: { 'panel:chat': 'hidden', 'tool:game:measure': 'menu', unknown: 'dock' },
    }, entries);
    assert.deepEqual(normalized.order.panels, ['panel:scenes', 'panel:chat', 'panel:actors']);
    assert.equal(normalized.placement['panel:chat'], 'hidden');
    assert.equal(normalized.placement['tool:game:measure'], 'dock');
    assert.equal('unknown' in normalized.placement, false);
});

test('a role change excludes GM controls and new authorized tools appear in their default position', () => {
    const previous = normalizeDockPreferences({ version: 1, order: { panels: ['panel:scenes', 'panel:actors'] },
        placement: { 'panel:scenes': 'dock' } }, entries);
    const playerEntries = entries.filter(entry => entry.id !== 'panel:scenes');
    const player = normalizeDockPreferences(previous, playerEntries);
    assert.equal(player.order.panels.includes('panel:scenes'), false);
    assert.equal('panel:scenes' in player.placement, false);
    const added = normalizeDockPreferences(previous, [...entries, { id: 'panel:clocks', group: 'panels', defaultPlacement: 'menu' }]);
    assert.equal(added.order.panels.at(-1), 'panel:clocks');
    assert.equal(added.placement['panel:clocks'], 'menu');
});

test('reordering skips unavailable peers without dropping their preferences or moving other groups', () => {
    const original = normalizeDockPreferences(null, entries), snapshot = structuredClone(original);
    const moved = moveDockEntry(original, entries, 'panel:scenes', -1, ['panel:chat', 'panel:scenes']);
    assert.deepEqual(moved.order.panels, ['panel:scenes', 'panel:actors', 'panel:chat']);
    assert.deepEqual(moved.order['tools:game'], original.order['tools:game']);
    assert.deepEqual(original, snapshot);
    assert.deepEqual(moveDockEntry(moved, entries, 'panel:scenes', -1, ['panel:chat', 'panel:scenes']), moved);
    assert.deepEqual(moveDockEntry(original, entries, 'panel:actors', -1, ['panel:chat']), original);
    assert.deepEqual(normalizeDockPreferences(null, entries), snapshot);
});
