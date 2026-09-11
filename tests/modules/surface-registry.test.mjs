import test from 'node:test';
import assert from 'node:assert/strict';
import { SurfaceRegistry } from '../../gravewright/modules/static/gravewright_modules/surface-registry.js';

class Element {
  children = []; hidden = false; className = '';
  ownerDocument = { createElement: () => new Element() };
  classList = { contains: name => this.className.split(' ').includes(name) };
  append(child) { child.parent = this; this.children.push(child); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter(child => child !== this); }
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('registration handles current and future surfaces; disposal revokes the captured API', async () => {
  const registry = new SurfaceRegistry((context,life) => ({check:()=>life.check()}));
  const first = new Element(), second = new Element(), blocks = [];
  const detach = registry.attach(first,'actor.sheet',{actorId:'first'});
  const release = registry.public.register('actor.sheet', block => blocks.push(block));
  registry.attach(second,'actor.sheet',{actorId:'second'});
  await tick();
  assert.equal(blocks.length,2);
  assert.equal(blocks[0].context.actorId,'first');
  detach();
  assert.throws(blocks[0].api.check,{code:'stale_context'});
  blocks[1].api.check();
  release();
  assert.throws(blocks[1].api.check,{code:'stale_context'});
  assert.equal(first.children.length,0);
  assert.equal(second.children.length,0);
  registry.close();
});

test('failed replacement restores native visibility and rejects competing replacements', async () => {
  const errors = [], element = new Element(), native = new Element(), originalHidden = new Element();
  originalHidden.hidden = true;
  element.append(native); element.append(originalHidden);
  const registry = new SurfaceRegistry(()=>({}), error=>errors.push(error));
  registry.attach(element,'actor.sheet',{});
  registry.public.register('actor.sheet',{mode:'replace',mount(){throw Error('broken');}});
  assert.equal(native.hidden,true);
  await tick();
  assert.equal(native.hidden,false);
  assert.equal(originalHidden.hidden,true);
  assert.equal(element.children.length,2);
  assert.equal(errors.length,1);
  assert.throws(()=>registry.public.register('actor.sheet',{mode:'replace',mount(){}}),{code:'conflict'});
  registry.close();
  assert.throws(()=>registry.public.register('actor.sheet',()=>{}),{code:'stale_context'});
});
