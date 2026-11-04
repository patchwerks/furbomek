import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, lstat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { parsePack, samplePack } from '../../../packages/extension-preview/index.mjs';
import { loadPackFile } from '../../../packages/extension-preview/load-file.mjs';

const root = new URL('../../../', import.meta.url);
const examples = new URL('packages/extension-preview/examples/', root);
const guideURL = new URL('docs/contributing/presentation-packs.md', root);
const names = ['acknowledge.json', 'curious.json', 'neutral.json'];
const neutral = (positionMs) => ({ positionMs, expression: 'neutral', reaction: null, reactionProgress: 0 });
async function pack(name) { return loadPackFile(fileURLToPath(new URL(name + '.json', examples))); }

test('starter inventory is exactly three bounded regular JSON files with declared identities', async () => {
  assert.deepEqual((await readdir(examples)).sort(), names);
  for (const name of names) {
    const path = new URL(name, examples);
    const stat = await lstat(path);
    assert.ok(stat.isFile() && !stat.isSymbolicLink(), name);
    assert.ok(stat.size > 0 && stat.size <= 1024 * 1024, name);
    const parsed = parsePack(await readFile(path));
    assert.equal(parsed.packId, `starter-${name.slice(0, -5)}`);
    assert.equal(parsed.packVersion, '0.1.0');
    assert.deepEqual(parsed.capabilities, name === 'acknowledge.json'
      ? ['presentation.expression', 'presentation.reaction'] : ['presentation.expression']);
    assert.deepEqual(await loadPackFile(fileURLToPath(path)), parsed);
  }
});

test('neutral starter remains clear across its complete duration', async () => {
  const p = await pack('neutral');
  assert.equal(p.durationMs, 1200);
  for (const at of [0, 1, 600, 1199, 1200, 2000]) {
    assert.deepEqual(samplePack(p, at), neutral(Math.min(at, 1200)));
  }
});

test('curious starter cue, expiry, reset, backwards seek and end match the guide', async () => {
  const p = await pack('curious');
  assert.equal(p.durationMs, 2000);
  const expected = (at) => ({ ...neutral(Math.min(at, 2000)), expression: at >= 400 && at < 1400 ? 'curious' : 'neutral' });
  for (const at of [0, 399, 400, 900, 1399, 1400, 2000, 2100, 900, 0, 400]) {
    assert.deepEqual(samplePack(p, at), expected(at));
    assert.deepEqual(samplePack(p, at), samplePack(p, at));
  }
});

test('acknowledge starter cue, progress, expiry, reset, backwards seek and end match the guide', async () => {
  const p = await pack('acknowledge');
  assert.equal(p.durationMs, 1600);
  for (const at of [0, 299, 300, 600, 899, 900, 1600, 1700, 600, 0, 300]) {
    const active = at >= 300 && at < 900;
    assert.deepEqual(samplePack(p, at), { ...neutral(Math.min(at, 1600)),
      reaction: active ? 'acknowledge' : null, reactionProgress: active ? (at - 300) / 600 : 0 });
  }
});

test('every guide JSON block is a complete strict pack matching a supplied example', async () => {
  const guide = await readFile(guideURL, 'utf8');
  const blocks = [...guide.matchAll(/^```json\r?\n([\s\S]*?)^```\s*$/gm)];
  assert.ok(blocks.length > 0);
  const supplied = await Promise.all(names.map(async (name) => parsePack(await readFile(new URL(name, examples)))));
  for (const [, json] of blocks) {
    const parsed = parsePack(new TextEncoder().encode(json));
    const same = supplied.find((candidate) => candidate.packId === parsed.packId);
    assert.ok(same, `unknown guide example ${parsed.packId}`);
    assert.deepEqual(parsed, same);
  }
});

test('guide commands remain direct, copyable and nonrecursive', async () => {
  const guide = await readFile(guideURL, 'utf8');
  const commands = new Map([...guide.matchAll(/<!-- (starter-[a-z-]+) -->\s*```sh\n([\s\S]*?)\n```/g)].map((m) => [m[1], m[2]]));
  assert.equal(commands.size, 3);
  assert.equal(commands.get('starter-check'), 'node --test docs/contributing/tests/presentation-packs.test.mjs');
  assert.equal(commands.get('starter-full-suite'), 'node --experimental-vm-modules --test packages/extension-preview/tests/*.test.mjs docs/contributing/tests/*.test.mjs');
  assert.equal(commands.get('starter-validate-file'), 'node --input-type=module -e \'import { loadPackFile } from "./packages/extension-preview/load-file.mjs"; const pack = await loadPackFile(process.argv[1]); console.log(`Valid pack: ${pack.packId}`);\' -- \'packages/extension-preview/examples/neutral.json\'');
});

test('guide relative links resolve to nonsymlink files or directories within the checkout', async () => {
  const guide = await readFile(guideURL, 'utf8');
  const rootPath = fileURLToPath(root);
  for (const [, target] of guide.matchAll(/\[[^\]\n]+\]\(([^)\s]+)\)/g)) {
    if (/^(?:https?:|#)/.test(target)) continue;
    assert.ok(!/^[a-z]+:|^\//i.test(target), target);
    const path = resolve(dirname(fileURLToPath(guideURL)), decodeURIComponent(target.split('#')[0]));
    assert.ok(path.startsWith(rootPath), target);
    const stat = await lstat(path);
    assert.ok((stat.isFile() || stat.isDirectory()) && !stat.isSymbolicLink(), target);
  }
});
