import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRunFormatter } from './run-format.js';

const t = (key, params = {}) => key.replace(/\{(\d+)\}/g, (_, index) => params[index]);

function rehearsal() {
    const elements = [{ id: 'gate', kind: 'region', name: 'Gate' }, { id: 'arrival', kind: 'region', name: 'Arrival' },
        { id: 'oak', kind: 'door', name: '' }, { id: 'iron', kind: 'door', name: '' }];
    const sourceIds = { nativeGate: 'gate', nativeArrival: 'arrival', nativeIron: 'iron' };
    return createRunFormatter({ t, elements: () => elements, resolve: id => sourceIds[id] || id,
        fallbackName: id => ({ plain: 'Plain region' })[id], tokenName: id => (id === 'visitor' ? 'Test visitor' : undefined) });
}

test('teleport steps name the token and destination instead of raw identifiers', () => {
    const format = rehearsal();
    assert.equal(format.stepText({ type: 'teleport', tokenId: 'visitor', destinationId: 'nativeArrival', gridX: 26, gridY: 22 }),
        'Teleport token: Test visitor → Arrival (26, 22)');
    assert.equal(format.stepText({ type: 'teleport', tokenId: 'stranger', destinationId: 'plain', gridX: 1, gridY: 2 }),
        'Teleport token: Token → Plain region (1, 2)');
    assert.equal(format.stepText({ type: 'teleport', skipped: 'missing-test-token' }), 'Teleport token: Skipped');
});

test('clock action traces describe the operation and actual bounded progress', () => {
    const format = rehearsal();
    assert.equal(format.stepText({ type: 'clockControl', clockId: 'technical-id', action: 'advance', amount: 3, before: 4, value: 6 }),
        'Control clock: Advance clock · 4 → 6');
    assert.equal(format.stepText({ type: 'clockControl', action: 'reset', before: 6, value: 0 }),
        'Control clock: Reset clock · 6 → 0');
    assert.equal(format.stepText({ type: 'clockControl', action: 'set', missing: true }),
        'Control clock: Set clock value · Missing target');
});

test('region changes read as state and occupancy, keeping bookkeeping in technical details', () => {
    const format = rehearsal();
    const summary = format.describeChange({ id: 'nativeGate', kind: 'zones',
        before: { data: { name: 'Gate', region: { name: 'Gate', state: 'occupied', occupants: ['visitor'] } } },
        after: { data: { name: 'Gate', region: { name: 'Gate', state: 'empty', occupants: [] } } } });
    assert.equal(summary.title, 'Gate');
    assert.deepEqual(summary.facts, ['Occupied → Empty · Left area: Test visitor']);
    assert.deepEqual(summary.details.map(([key]) => key), ['region']);
    const arrival = format.describeChange({ id: 'nativeArrival', kind: 'zones',
        before: { data: { region: { state: 'empty', occupants: [] } } },
        after: { data: { region: { state: 'occupied', occupants: ['visitor'], arrivalGates: ['visitor'] } } } });
    assert.equal(arrival.title, 'Arrival', 'a region without its own behavior is still named from the catalog');
    assert.deepEqual(arrival.facts, ['Empty → Occupied · Entered area: Test visitor']);
});

test('element changes fall back to their native name, then to the kind, and list unknown fields only as details', () => {
    const format = rehearsal();
    const door = format.describeChange({ id: 'nativeIron', kind: 'walls',
        before: { data: { door_state: 'closed', x1: 0, mystery: 1 } }, after: { data: { door_state: 'open', x1: 64, mystery: 2 } } });
    assert.equal(door.title, 'Door 2');
    assert.deepEqual(door.facts, ['Closed → Opened', 'Moved']);
    assert.deepEqual(door.details, [['mystery', '2']]);
    assert.equal(format.describeChange({ id: 'loose', kind: 'zones', before: { data: {} }, after: { data: { name: 'Hall', enabled: false } } }).title, 'Hall');
    assert.equal(format.describeChange({ id: 'loose', kind: 'lights', before: { data: {} }, after: { data: { enabled: true } } }).title, 'Light');
    assert.deepEqual(format.describeChange({ id: 'nativeIron', kind: 'walls', before: { data: {} }, after: null }), { title: 'Door 2', removed: true, facts: [], details: [] });
});

test('variable changes show the new typed value by name', () => {
    const format = rehearsal();
    assert.deepEqual(format.variableChanges({ solved: { type: 'boolean', value: false }, keep: { type: 'number', value: 1 } },
        { solved: { type: 'boolean', value: true }, keep: { type: 'number', value: 1 }, title: { type: 'text', value: 'Open' } }),
    ['Variables · solved = True', 'Variables · title = "Open"']);
});

test('event titles name the owning element and the event', () => {
    const format = rehearsal();
    assert.equal(format.eventTitle({ event: 'refused', doorId: 'nativeIron' }), 'Door 2 · Skipped');
    assert.match(format.eventTitle({ event: 'presence:enter', doorId: 'nativeGate' }), /^Gate · /);
});
