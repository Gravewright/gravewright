import test from 'node:test';
import assert from 'node:assert/strict';
import { combination, conflicts, validCombination, reserved } from './shortcuts-model.js';

test('recording and dispatch agree on modifiers, while composition and navigation stay native', () => {
    assert.equal(combination({key:'q', ctrlKey:true, shiftKey:true}), 'Control+Shift+Q');
    assert.equal(combination({key:'F2', altKey:true}), 'Alt+F2');
    assert.equal(combination({key:'!', code:'Digit1', shiftKey:true}), 'Shift+1');
    assert.equal(combination({key:'ç', altKey:true}), 'Alt+Ç');
    assert.ok(validCombination('Alt+Ç'));
    for (const key of ['Escape','Enter','Tab','ArrowUp','Control','Dead']) assert.equal(combination({key}), null);
    assert.equal(combination({key:'q', isComposing:true}), null);
    assert.ok(validCombination('Control+Shift+Q'));
    assert.ok(!validCombination('Shift+Control+Q'));
    assert.ok(!validCombination('Control+Q Escape'));
    for (const key of ['Control+Z','Meta+Shift+V','Control+R','F5','Alt+F4']) assert.ok(reserved(key), key);
    assert.ok(!reserved('Control+K'));
    assert.ok(!reserved('Shift+Q'));
});

test('conflicts account for active tool layers, global windows and disabled bindings', () => {
    const entries=[{id:'wall',scope:'walls',defaultKey:'W'}, {id:'light',scope:'lighting',defaultKey:'L'},
        {id:'chat',defaultKey:'C'}, {id:'search',defaultKey:'Control+K Meta+K'}];
    assert.equal(conflicts(entries,'wall','L',{}), undefined);
    assert.equal(conflicts(entries,'wall','C',{}).id, 'chat');
    assert.equal(conflicts(entries,'chat','W',{}).id, 'wall');
    assert.equal(conflicts(entries,'wall','Meta+K',{}).id, 'search');
    assert.equal(conflicts(entries,'wall','C',{chat:''}), undefined);
    assert.equal(conflicts(entries,'wall','Q',{chat:'Q'}).id, 'chat');
});
