import test from 'node:test';
import assert from 'node:assert/strict';
import { createTranslator } from '../../gravewright/modules/static/gravewright_modules/i18n.js';
import { BrowserBridge } from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';

globalThis.window = new EventTarget();
const locale = id => { window.gravewrightLocale = {id, messages:{Save:'Salvar'}}; };

test('module catalogs are shared across mounts, isolated from other modules and disposed with activation', async () => {
  locale('pt-BR');
  const life = new Lifetime(), mount = new Lifetime(), bridge = new BrowserBridge('table');
  const api = bridge.api({moduleId:'example.one'}, life);
  const same = bridge.api({moduleId:'example.one'}, mount);
  const other = bridge.api({moduleId:'example.two'}, mount);
  api.i18n.register({en:{title:'English title',welcome:'Hello, {name}: {0}'},'pt-BR':{title:'Título',welcome:'Olá, {name}: {0}'}});
  assert.equal(same.i18n.t('title'), 'Título');
  assert.equal(same.i18n.t('welcome',{name:'$& <script>',0:7}), 'Olá, $& <script>: 7');
  assert.equal(other.i18n.t('title'), 'title');
  assert.equal(other.i18n.has('title'), false);
  assert.equal(createTranslator().t('Save'), 'Salvar');
  assert.equal(same.i18n.t('welcome'), 'Olá, {name}: {0}');
  await life.close();
  assert.equal(same.i18n.t('title'), 'title');
  assert.throws(() => api.i18n.t('title'), {code:'stale_context'});
  await mount.close();
});

test('locale/base/English fallback, missing keys and number formatting work without a language service', () => {
  const api = createTranslator('example.fallback');
  const dispose = api.register({en:{title:'Title',only:'English'},pt:{title:'Título'}});
  locale('pt-BR');
  assert.equal(api.t('title'), 'Título');
  assert.equal(api.t('only'), 'English');
  assert.equal(api.t('absent'), 'absent');
  assert.equal(api.number(1234.5), '1.234,5');
  locale('en');
  assert.equal(api.t('title'), 'Title');
  dispose(); dispose();
});

test('invalid catalogs and altered named/numbered placeholders are rejected atomically', () => {
  const api = createTranslator('example.validation');
  for (const data of [null, [], {pt:{a:'A'}}, {en:{a:7}}, {en:{a:'Hi {0}'},es:{a:'Hola {1}'}}, {en:{a:'Hi {name}'},es:{a:'Hola'}}, {en:{a:'A'},es:{extra:'B'}}, {en:{a:'A'},'../es':{a:'A'}}]) {
    assert.throws(() => api.register(data), {code:'invalid_data'});
    assert.equal(api.has('a'), false);
  }
});

test('locale listeners are cleaned up when their context closes', async () => {
  const life = new Lifetime(), api = createTranslator('example.events',life), received = [];
  api.onChange(id => received.push(id));
  locale('es');window.dispatchEvent(new Event('gravewright:locale'));
  assert.deepEqual(received,['es']);
  await life.close();
  locale('pt-BR');window.dispatchEvent(new Event('gravewright:locale'));
  assert.deepEqual(received,['es']);
});

test('native consumers follow provider catalogs, including late registration and disposal', async () => {
  locale('pt-BR');
  const life=new Lifetime(),provider=createTranslator('example.inventory',life),native=createTranslator('example.inventory'),unrelated=createTranslator('example.unrelated');
  const labels=[],stop=native.onChange(()=>labels.push(native.t('types.component')));
  const dispose=provider.register({en:{'types.component':'Component'},'pt-BR':{'types.component':'Componente'}});
  assert.deepEqual(labels,['Componente']);
  const other=unrelated.register({en:{'types.component':'Unrelated'}});
  assert.deepEqual(labels,['Componente']);
  dispose();dispose();assert.deepEqual(labels,['Componente','types.component']);
  provider.register({en:{'types.component':'Module component'}});
  assert.equal(labels.at(-1),'Module component');
  stop();await life.close();other();
  assert.equal(labels.at(-1),'Module component');
});
