import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { webcrypto } from 'node:crypto';
import { createContext, SourceTextModule } from 'node:vm';
import { validateBrowserMetadata } from '../browser.mjs';
import { samplePack } from '../../../packages/extension-preview/index.mjs';

const packBytes = new Uint8Array(await readFile(new URL('../../../packages/extension-preview/examples/neutral.json', import.meta.url)));
const knownHash = 'ed4996eaaca3a8b1a73e63336a903090244555e80911bd74648f840697ee85c7';
const companion = { metadataVersion: 1, packId: 'starter-neutral', packVersion: '0.1.0', previewContractVersion: 1,
  author: 'Public Author', license: 'MIT', packSha256: knownHash };
const encode = value => new TextEncoder().encode(JSON.stringify(value));
const metadataBytes = encode(companion);
const unsupported = /^Error: Browser metadata validation requires Web Crypto SHA-256 in a secure context$/;
const urls = [new URL('../browser.mjs', import.meta.url), new URL('../metadata.mjs', import.meta.url),
  new URL('../../../packages/extension-preview/index.mjs', import.meta.url)];
const sources = new Map(await Promise.all(urls.map(async url => [url.href, await readFile(url, 'utf8')])));

async function isolated(crypto, isSecureContext = true) {
  const context = createContext({ Uint8Array, TextDecoder, crypto, isSecureContext });
  const modules = new Map();
  for (const [identifier, source] of sources) modules.set(identifier, new SourceTextModule(source, { context, identifier }));
  const root = modules.get(urls[0].href);
  await root.link((specifier, parent) => {
    const dependency = modules.get(new URL(specifier, parent.identifier).href);
    assert.ok(dependency, 'only the fixed browser-safe dependency graph is permitted');
    return dependency;
  });
  await root.evaluate();
  return root.namespace.validateBrowserMetadata;
}

test('native Web Crypto known answer, frozen result and core brand survive validation', async () => {
  const validate = await isolated(webcrypto);
  assert.equal((await validate(packBytes, metadataBytes)).packSha256, knownHash);
  const result = await validateBrowserMetadata(packBytes, metadataBytes);
  for (const value of [result, result.pack, result.pack.events, result.metadata]) assert.ok(Object.isFrozen(value));
  assert.equal(result.packSha256, knownHash);
  assert.equal(samplePack(result.pack, 0).expression, 'neutral');
});

test('rejects mismatched identity, digest and same-JSON byte changes', async () => {
  for (const change of [{ packId: 'another' }, { packVersion: '1.0.0' }, { packSha256: '0'.repeat(64) }]) {
    await assert.rejects(validateBrowserMetadata(packBytes, encode({ ...companion, ...change })), /does not match/);
  }
  const changed = new Uint8Array([...packBytes, 32]);
  await assert.rejects(validateBrowserMetadata(changed, metadataBytes), /digest/);
});

test('strict parsing rejects invalid data before calling crypto', async () => {
  let calls = 0;
  const validate = await isolated({ subtle: { digest() { calls++; throw new Error('must not run'); } } });
  const text = new TextDecoder().decode(metadataBytes);
  for (const bad of [new Uint8Array([255]), new TextEncoder().encode('\ufeff' + text),
    new TextEncoder().encode(text.replace('"metadataVersion":1', '"metadataVersion":1,"metadata\\u0056ersion":1')),
    encode({ ...companion, author: {} }), encode({ ...companion, url: 'https://invalid.example' }),
    encode({ ...companion, metadataVersion: 2 }), encode({ ...companion, previewContractVersion: 2 }),
    new Uint8Array(16385)]) await assert.rejects(validate(packBytes, bad));
  for (const bad of [new Uint8Array([255]), new TextEncoder().encode('\ufeff{}'),
    encode({ ...JSON.parse(new TextDecoder().decode(packBytes)), schemaVersion: 2 }),
    new Uint8Array(1048577)]) await assert.rejects(validate(bad, metadataBytes));
  for (const bad of [null, {}, 'bytes', new ArrayBuffer(8)]) {
    await assert.rejects(validate(bad, metadataBytes));
    await assert.rejects(validate(packBytes, bad));
  }
  assert.equal(calls, 0);
});

test('offset views and asynchronous caller mutation use only synchronous snapshots', async () => {
  let release;
  let captured;
  const validate = await isolated({ subtle: { digest(algorithm, bytes) {
    captured = bytes;
    return new Promise(resolve => { release = () => resolve(webcrypto.subtle.digest(algorithm, bytes)); });
  } } });
  const packBacking = new Uint8Array(packBytes.length + 10).fill(255);
  packBacking.set(packBytes, 5);
  const metaBacking = new Uint8Array(metadataBytes.length + 6).fill(255);
  metaBacking.set(metadataBytes, 3);
  const pending = validate(packBacking.subarray(5, -5), metaBacking.subarray(3, -3));
  assert.notEqual(captured.buffer, packBacking.buffer);
  packBacking.fill(0); metaBacking.fill(0);
  release();
  const result = await pending;
  assert.equal(result.packSha256, knownHash);
  assert.equal(result.metadata.author, 'Public Author');
});

test('shared buffers are rejected rather than claiming an atomic cross-thread snapshot', async () => {
  await assert.rejects(validateBrowserMetadata(new Uint8Array(new SharedArrayBuffer(packBytes.length)), metadataBytes), /Shared/);
  await assert.rejects(validateBrowserMetadata(packBytes, new Uint8Array(new SharedArrayBuffer(metadataBytes.length))), /Shared/);
});

test('absent, insecure and rejecting Web Crypto fail closed with fixed diagnostics', async () => {
  for (const [crypto, secure] of [[undefined, true], [{}, true], [webcrypto, false],
    [{ subtle: { digest: async () => { throw new Error('private provider detail'); } } }, true]]) {
    const validate = await isolated(crypto, secure);
    await assert.rejects(validate(packBytes, metadataBytes), unsupported);
  }
});

test('browser dependency graph contains no Node imports, network or input execution', async () => {
  await isolated(webcrypto); // Linker rejects every import outside the three fixed modules.
  for (const source of sources.values()) {
    assert.doesNotMatch(source, /node:|\brequire\s*\(|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\beval\s*\(|\bFunction\s*\(/);
  }
  const hostile = encode({ ...companion, author: '<script>globalThis.compromised=true</script>' });
  assert.equal((await validateBrowserMetadata(packBytes, hostile)).metadata.author, JSON.parse(new TextDecoder().decode(hostile)).author);
  assert.equal(globalThis.compromised, undefined);
});
