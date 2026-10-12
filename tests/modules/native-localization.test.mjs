import test from 'node:test';
import assert from 'node:assert/strict';

test('native map labels read installed flat catalogs before the first locale event', async () => {
  globalThis.window = new EventTarget();
  const language = {id:'pt-BR',messages:{Length:'Comprimento','Welcome {0}':'Olá {0}'}};
  globalThis.document = {getElementById: () => ({textContent:JSON.stringify(language)})};
  const {text,formatNumber} = await import('../../gravewright/maps/frontend/shared/config/i18n/text.js');
  assert.equal(text('Length'), 'Comprimento');
  assert.equal(text(' Length '), ' Comprimento ');
  assert.equal(text('Welcome {0}', '$&'), 'Olá $&');
  assert.equal(formatNumber(1234.5), '1.234,5');
  window.dispatchEvent(new CustomEvent('gravewright:locale',{detail:{id:'es',messages:{Length:'Longitud'}}}));
  assert.equal(text('Length'), 'Longitud');
  window.dispatchEvent(new CustomEvent('gravewright:locale',{detail:{id:'en',messages:{text:{Length:'Length'}}}}));
  assert.equal(text('Length'), 'Length');
});
