import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

function page(entry) {
  let time = Date.parse('2026-10-30T12:00:00.000Z');
  const timers = new Map(), listeners = new Map(), assetListeners = new Map();
  let next = 0;
  const nodes = Object.fromEntries(['avatar','title','caption','status','mode','character'].map(id => [id, {hidden:true, dataset:{}, textContent:''}]));
  Object.assign(nodes.character, {complete:true, naturalWidth:100, addEventListener:(name, fn) => assetListeners.set(name, fn)});
  const context = {
    document:{querySelector: selector => nodes[selector.slice(1)]}, TextEncoder,
    Date: class extends Date { constructor(...args) { super(...(args.length ? args : [time])); } static now() { return time; } },
    setInterval: fn => { timers.set(++next, fn); return next; },
    clearInterval: id => timers.delete(id),
    setTimeout: fn => { timers.set(++next, fn); return next; },
    clearTimeout: id => timers.delete(id),
    addEventListener: (name, fn) => listeners.set(name, [...(listeners.get(name) || []), fn])
  };
  context.window = context;
  vm.createContext(context);
  for (const file of ['adapter.js','view.js',entry]) {
    vm.runInContext(readFileSync(new URL('../'+file, import.meta.url), 'utf8'), context, {filename:file});
  }
  return {context, nodes, timers, assetListeners, advance: ms => { time += ms; }, hide: () => listeners.get('pagehide').forEach(fn => fn())};
}

test('ordinary file entrypoint keeps its instance private and stays offline', () => {
  const p = page('boot.js');
  assert.equal(p.nodes.avatar.hidden, false);
  assert.equal(p.nodes.caption.textContent, 'Activity unavailable');
  assert.equal(p.nodes.mode.textContent, 'STATIC FALLBACK');
  assert.equal(Object.hasOwn(p.context, 'FurbomekAvatar'), false);
  assert.deepEqual(Object.keys(p.context.FurbomekView), ['createView']);
  p.advance(30000); for (const fn of p.timers.values()) fn();
  assert.equal(p.nodes.status.textContent, 'offline');
  p.hide(); assert.equal(p.timers.size, 0); assert.equal(p.nodes.avatar.hidden, true);
});

test('private fixture instance shows cancellation then expires without losing provenance', () => {
  const p = page('fixture.js');
  assert.equal(p.nodes.status.textContent, 'thinking');
  assert.equal(Object.hasOwn(p.context, 'FurbomekAvatar'), false);
  const count = p.timers.size;
  p.assetListeners.get('load')(); // Already-complete asset must not start a second fixture.
  assert.equal(p.timers.size, count);
  p.advance(1500); p.timers.get(1)(); // Fixture timeout is scheduled by the ready callback first.
  assert.equal(p.nodes.status.textContent, 'interrupted');
  p.advance(2500); p.timers.get(2)();
  assert.equal(p.nodes.caption.textContent, 'Activity unavailable');
  assert.equal(p.nodes.mode.textContent, 'FIXTURE · NOT LIVE');
  p.hide(); assert.equal(p.timers.size, 0);
});

test('hostile-text fixture uses the same private view and textContent sink', () => {
  const p = page('tests/hostile.js');
  assert.equal(p.nodes.caption.textContent, '<img src=x onerror=alert(1)>');
  assert.equal(Object.hasOwn(p.nodes.caption, 'innerHTML'), false);
  assert.equal(Object.hasOwn(p.context, 'FurbomekAvatar'), false);
  p.assetListeners.get('error')();
  assert.equal(p.nodes.avatar.hidden, true);
  assert.equal(p.nodes.caption.textContent, 'Activity unavailable');
});
