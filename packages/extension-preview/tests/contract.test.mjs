import test from 'node:test';
import assert from 'node:assert/strict';
import { parsePack, samplePack } from '../index.mjs';
const encode = value => new TextEncoder().encode(typeof value === 'string' ? value : JSON.stringify(value));
const event = (seq, atMs, kind = 'presentation.expression', value = 'neutral') => ({ seq, atMs, kind, value });
const fixture = () => ({ schemaVersion: 1, previewContractVersion: 1, packId: 'example-pack', packVersion: '1.0.0', capabilities: ['presentation.expression', 'presentation.reaction'], durationMs: 4000, events: [event(1, 0), event(2, 1000, 'presentation.reaction', 'acknowledge'), event(3, 3000)] });
const parse = obj => parsePack(encode(obj));
const reject = obj => assert.throws(() => parse(obj));

test('valid byte view, declaration subset, and exact output fields', () => {
  const bytes = encode(fixture());
  const padded = new Uint8Array(bytes.length + 2); padded.set(bytes, 1);
  const pack = parsePack(padded.subarray(1, -1));
  assert.deepEqual(samplePack(pack, 0), {positionMs: 0, expression: 'neutral', reaction: null, reactionProgress: 0});
  const only = fixture(); only.capabilities = ['presentation.expression']; only.events = [event(1, 0)];
  assert.equal(parse(only).packId, 'example-pack');
});

test('byte gate rejects wrong types, BOM, invalid UTF-8, archives, and over-limit inputs', () => {
  for (const bad of [null, '{}', {}, [], new ArrayBuffer(2), new Uint16Array(2)]) assert.throws(() => parsePack(bad));
  for (const bad of [new Uint8Array([0xff]), new Uint8Array([0xc0, 0xaf]), new Uint8Array([0xe2, 0x82]), encode('\ufeff' + JSON.stringify(fixture())), new Uint8Array([0x50, 0x4b, 3, 4]), new Uint8Array([0x1f, 0x8b, 8]), new Uint8Array(1048577)]) assert.throws(() => parsePack(bad));
  const json = JSON.stringify(fixture());
  assert.equal(parse(json + ' '.repeat(1048576 - encode(json).length)).packId, 'example-pack');
  reject(json + ' '.repeat(1048577 - encode(json).length));
});

for (const [label, mutate] of [
  ['schema version', p => p.schemaVersion = 2], ['preview version', p => p.previewContractVersion = '1'],
  ['unknown root', p => p.url = 'https://example.invalid/code.js'], ['missing root', p => delete p.packId],
  ['empty caps', p => p.capabilities = []], ['duplicate caps', p => p.capabilities.push('presentation.expression')],
  ['unknown cap', p => p.capabilities.push('robot.move')], ['expression required', p => p.capabilities = ['presentation.reaction']],
  ['undeclared kind', p => {p.capabilities = ['presentation.expression'];}],
  ['no events', p => p.events = []], ['unknown event field', p => p.events[0].path = '../secret'],
  ['unknown kind', p => p.events[1].kind = 'robot.move'], ['unknown expression', p => p.events[0].value = 'happy'],
  ['unknown reaction', p => p.events[1].value = 'wave'], ['missing event field', p => delete p.events[0].seq],
  ['duplicate seq', p => p.events[1].seq = 1], ['skipped seq', p => p.events[1].seq = 3],
  ['backward time', p => p.events[2].atMs = 1], ['at end', p => p.events[2].atMs = 4000],
  ['negative time', p => p.events[0].atMs = -1], ['fraction time', p => p.events[1].atMs = 1.5],
  ['unsafe time', p => p.events[1].atMs = Number.MAX_SAFE_INTEGER + 1], ['fraction seq', p => p.events[1].seq = 2.5],
  ['zero duration', p => p.durationMs = 0], ['long duration', p => p.durationMs = 30001], ['fraction duration', p => p.durationMs = 4000.5],
  ['first time', p => p.events[0].atMs = 1], ['first expression', p => p.events[0].value = 'curious'],
  ['reaction at zero', p => p.events[1].atMs = 0], ['curious at zero', p => p.events[1] = event(2, 0, 'presentation.expression', 'curious')],
]) test('rejects ' + label, () => { const p = fixture(); mutate(p); reject(p); });

for (const value of ['../pack', '/pack', 'Pack', 'pack_name', 'a'.repeat(65), '', 'https://example.invalid', 'a\u0000b']) test('rejects packId ' + JSON.stringify(value), () => {const p = fixture(); p.packId = value; reject(p);});
for (const value of ['01.0.0', '1.01.0', '1.0.01', '1.0', '1.0.0-beta', '1.0.0+build', 'v1.0.0', '1.0.0\n', '1'.repeat(33) + '.0.0']) test('rejects version ' + JSON.stringify(value), () => {const p = fixture(); p.packVersion = value; reject(p);});

test('strict JSON grammar, decoded duplicate keys, prototype keys, depth and scalar roots', () => {
  const json = JSON.stringify(fixture());
  for (const raw of [json.replace('"schemaVersion":1', '"schemaVersion":1,"schemaVersion":1'), json.replace('"schemaVersion":1', '"schemaVersion":1,"schema\\u0056ersion":1'), json.replace('"seq":1', '"seq":1,"s\\u0065q":1'), json.replace('"schemaVersion":1', '"__proto__":{},"schemaVersion":1'), json.replace('"schemaVersion":1', '"constructor":{},"schemaVersion":1'), json.replace('"durationMs":4000', '"durationMs":NaN'), json.replace('"durationMs":4000', '"durationMs":Infinity'), json.replace('"durationMs":4000', '"durationMs":01'), json + '{}', json.slice(0, -1) + ',}', 'null', '[]', 'true', '"text"', '['.repeat(10) + '0' + ']'.repeat(10), json.replace('"packId":"example-pack"', '"packId":' + '['.repeat(9) + '0' + ']'.repeat(9))]) reject(raw);
  assert.equal({}.polluted, undefined);
});

test('inclusive duration/count/id/version limits and neutral-only reset ties', () => {
  const p = fixture(); p.durationMs = 30000; p.packId = 'a'.repeat(64); p.packVersion = '1'.repeat(28) + '.0.0';
  p.events = Array.from({length: 64}, (_, i) => event(i + 1, i === 63 ? 29999 : i));
  assert.equal(parse(p).events.length, 64); p.events.push(event(65, 29999)); reject(p);
  const tiny = fixture(); tiny.durationMs = 1; tiny.events = [event(1, 0), event(2, 0)]; assert.equal(parse(tiny).durationMs, 1);
});

test('parse results deep freeze; branding rejects clones/forgeries and mutation', () => {
  const input = fixture(); const bytes = encode(input); const p = parsePack(bytes); bytes.fill(0);
  for (const object of [p, p.capabilities, p.events, ...p.events]) assert.ok(Object.isFrozen(object));
  assert.throws(() => p.events[0].value = 'curious'); assert.throws(() => p.events.push(event(4, 3999)));
  assert.throws(() => p.capabilities.push('robot.move'));
  for (const fake of [input, structuredClone(p), {...p}, Object.freeze(input), Object.create(p), null]) assert.throws(() => samplePack(fake, 1));
  const a = samplePack(p, 1000), b = samplePack(p, 1000); assert.notEqual(a, b); assert.ok(Object.isFrozen(a)); assert.throws(() => a.expression = 'curious');
});

test('sampler elapsed contract, reset and end clamp', () => {
  const p = parse(fixture());
  for (const time of [-1, NaN, Infinity, -Infinity, '1', null, undefined, {}, 1n]) assert.throws(() => samplePack(p, time));
  for (const time of [4000, 4000.5, Number.MAX_VALUE]) assert.deepEqual(samplePack(p, time), {positionMs:4000,expression:'neutral',reaction:null,reactionProgress:0});
  assert.deepEqual(samplePack(p, 0.5), {positionMs:0.5,expression:'neutral',reaction:null,reactionProgress:0});
  assert.equal(samplePack(p, 999.99).reaction, null);
  assert.equal(samplePack(p, 1000).reactionProgress, 0);
  assert.equal(samplePack(p, 1300).reactionProgress, 0.5);
  assert.equal(samplePack(p, 1599.5).reaction, 'acknowledge');
  assert.equal(samplePack(p, 1600).reaction, null); assert.equal(samplePack(p, 1600).reactionProgress, 0);
});

test('independent latest cues, exact expiry, equal-time seq, and query-order convergence', () => {
  const p = fixture(); p.events = [event(1,0),event(2,100,'presentation.expression','curious'),event(3,200,'presentation.reaction','acknowledge'),event(4,500,'presentation.reaction','acknowledge'),event(5,900,'presentation.expression','curious'),event(6,1900),event(7,1900,'presentation.expression','curious'),event(8,3000,'presentation.expression','curious')];
  const pack = parse(p);
  assert.deepEqual(samplePack(pack,800), {positionMs:800,expression:'curious',reaction:'acknowledge',reactionProgress:0.5});
  assert.equal(samplePack(pack,1100).reaction, null); assert.equal(samplePack(pack,1100).expression,'curious');
  assert.equal(samplePack(pack,1899.5).expression,'curious'); assert.equal(samplePack(pack,1900).expression,'curious');
  assert.equal(samplePack(pack,2899.5).expression,'curious'); assert.equal(samplePack(pack,2900).expression,'neutral');
  assert.equal(samplePack(pack,3999.5).expression,'curious'); assert.equal(samplePack(pack,4000).expression,'neutral');
  const times = [0,0.25,100,200,500,800,899.5,900,1099.5,1100,1900,2900,3999.5,4000];
  const expected = new Map(times.map(t => [t,samplePack(pack,t)]));
  for (const t of [...times].reverse().concat(times)) assert.deepEqual(samplePack(pack,t), expected.get(t));
  const neutral = fixture(); neutral.events = [event(1,0),event(2,100,'presentation.expression','curious'),event(3,101)];
  assert.equal(samplePack(parse(neutral),101).expression,'neutral');
});


test('identifier and version reject every trailing line terminator', () => {
  for (const suffix of ['\n', '\r', '\r\n', '\u2028', '\u2029']) {
    for (const [field, valid] of [['packId', 'example-pack'], ['packVersion', '1.0.0']]) {
      const p = fixture(); p[field] = valid + suffix;
      assert.throws(() => parse(p), `${field} accepted suffix ${JSON.stringify(suffix)}`);
    }
  }
});
