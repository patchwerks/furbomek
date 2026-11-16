/* Standalone native-module checks, only in the disposable network-none browser worker. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const playwright = require(process.env.FURBOMEK_PLAYWRIGHT);
const browserName = process.env.VIEWER_BROWSER;
assert.ok(['chromium', 'firefox'].includes(browserName));
const evidence = process.env.VIEWER_EVIDENCE;
assert.ok(evidence, 'VIEWER_EVIDENCE is required');
const root = path.resolve(__dirname, '../../..');
const routes = new Map([
  ['/tools/presentation-pack/browser.mjs', fs.readFileSync(path.join(root, 'tools/presentation-pack/browser.mjs'))],
  ['/tools/presentation-pack/metadata.mjs', fs.readFileSync(path.join(root, 'tools/presentation-pack/metadata.mjs'))],
  ['/packages/extension-preview/index.mjs', fs.readFileSync(path.join(root, 'packages/extension-preview/index.mjs'))],
]);
const fixture = [...fs.readFileSync(path.join(root, 'packages/extension-preview/examples/neutral.json'))];
const html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Metadata validation qualification</title><link rel="icon" href="data:,"></head><body></body></html>';
const requests = [];
const blocked = [];
const errors = [];
const server = http.createServer((req, res) => {
  if (req.method !== 'GET' || (req.url !== '/' && !routes.has(req.url))) {
    blocked.push('unexpected local route'); res.writeHead(404).end(); return;
  }
  requests.push(req.url);
  res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; connect-src 'none'; img-src data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Type', req.url === '/' ? 'text/html; charset=utf-8' : 'text/javascript; charset=utf-8');
  res.end(req.url === '/' ? html : routes.get(req.url));
});
let browser;
let browserVersion = null;
let cases = [];
let status = 'failed';
(async () => {
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await playwright[browserName].launch({ headless: true });
    browserVersion = browser.version();
    assert.match(browserVersion, browserName === 'chromium' ? /^156\./ : /^157\./);
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => {
      const url = route.request().url();
      if (url === origin + '/' || [...routes.keys()].some(key => url === origin + key)) return route.continue();
      blocked.push('unexpected browser request'); return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', () => errors.push('page error'));
    await page.goto(origin + '/', { waitUntil: 'load' });
    cases = await page.evaluate(async fixtureBytes => {
      const { validateBrowserMetadata: validate } = await import('/tools/presentation-pack/browser.mjs');
      const { samplePack } = await import('/packages/extension-preview/index.mjs');
      const check = (condition, message) => { if (!condition) throw new Error(message); };
      const encode = value => new TextEncoder().encode(JSON.stringify(value));
      const pack = new Uint8Array(fixtureBytes);
      const hash = 'ed4996eaaca3a8b1a73e63336a903090244555e80911bd74648f840697ee85c7';
      const companion = { metadataVersion: 1, packId: 'starter-neutral', packVersion: '0.1.0', previewContractVersion: 1,
        author: 'Public Author', license: 'MIT', packSha256: hash };
      const meta = encode(companion);
      const passed = [];
      const rejects = async (packInput, metaInput, pattern) => {
        try { await validate(packInput, metaInput); }
        catch (error) { check(pattern.test(error.message), 'unexpected rejection'); return; }
        throw new Error('accepted invalid pair');
      };
      check(globalThis.isSecureContext && !!globalThis.crypto.subtle, 'native secure Web Crypto unavailable');
      const result = await validate(pack, meta);
      check(result.packSha256 === hash, 'known-answer digest');
      check([result, result.pack, result.pack.events, result.metadata].every(Object.isFrozen), 'immutable result');
      check(samplePack(result.pack, 0).expression === 'neutral', 'core brand retained');
      passed.push('native-sha256-known-answer-and-branded-frozen-result');
      await rejects(new Uint8Array([...pack, 32]), meta, /digest/);
      await rejects(pack, encode({ ...companion, packSha256: '0'.repeat(64) }), /digest/);
      passed.push('exact-byte-tamper');
      await rejects(pack, encode({ ...companion, packId: 'other' }), /packId/);
      await rejects(pack, encode({ ...companion, packVersion: '1.0.0' }), /packVersion/);
      passed.push('identity-mismatch');
      await rejects(pack, new Uint8Array([255]), /UTF-8/);
      await rejects(new Uint8Array([255]), meta, /UTF-8/);
      await rejects(pack, new TextEncoder().encode('\ufeff' + JSON.stringify(companion)), /BOM/);
      await rejects(pack, new TextEncoder().encode(JSON.stringify(companion).replace('"metadataVersion":1', '"metadataVersion":1,"metadata\\u0056ersion":1')), /duplicate/);
      await rejects(pack, encode({ ...companion, author: {} }), /nesting/);
      await rejects(pack, encode({ ...companion, url: 'https://invalid.example' }), /unknown/);
      passed.push('strict-malformed-input');
      await rejects(pack, encode({ ...companion, metadataVersion: 2 }), /version/);
      await rejects(pack, encode({ ...companion, previewContractVersion: 2 }), /version/);
      await rejects(encode({ ...JSON.parse(new TextDecoder().decode(pack)), schemaVersion: 2 }), meta, /version/);
      passed.push('unsupported-versions');
      await rejects(new Uint8Array(1048577), meta, /1 MiB/);
      await rejects(pack, new Uint8Array(16385), /16 KiB/);
      passed.push('bounded-input');
      const packBacking = new Uint8Array(pack.length + 4).fill(255); packBacking.set(pack, 2);
      const metaBacking = new Uint8Array(meta.length + 6).fill(255); metaBacking.set(meta, 3);
      check((await validate(packBacking.subarray(2, -2), metaBacking.subarray(3, -3))).packSha256 === hash, 'offset view');
      passed.push('offset-views');
      // Hold the actual native digest behind a promise so mutation occurs while it is in flight.
      const subtle = globalThis.crypto.subtle;
      const nativeDigest = subtle.digest.bind(subtle);
      let release;
      Object.defineProperty(subtle, 'digest', { configurable: true, value(algorithm, bytes) {
        return new Promise(resolve => { release = () => resolve(nativeDigest(algorithm, bytes)); });
      } });
      try {
        const pending = validate(packBacking.subarray(2, -2), metaBacking.subarray(3, -3));
        check(typeof release === 'function', 'digest invoked synchronously');
        packBacking.fill(0); metaBacking.fill(0);
        release();
        const snapshot = await pending;
        check(snapshot.packSha256 === hash && snapshot.metadata.author === 'Public Author', 'snapshot race');
      } finally { delete subtle.digest; }
      passed.push('caller-mutation-in-flight');
      Object.defineProperty(subtle, 'digest', { configurable: true, value: async () => { throw new Error('private detail'); } });
      try { await rejects(pack, meta, /^Browser metadata validation requires Web Crypto SHA-256 in a secure context$/); }
      finally { delete subtle.digest; }
      passed.push('native-digest-rejection-fails-closed');
      const inert = '<script>globalThis.compromised=true</script>';
      check((await validate(pack, encode({ ...companion, author: inert }))).metadata.author === inert, 'inert text');
      check(globalThis.compromised === undefined, 'input execution');
      passed.push('input-remains-data');
      return passed;
    }, fixture);
    assert.equal(cases.length, 10);
    assert.deepEqual(blocked, []);
    assert.deepEqual(errors, []);
    assert.deepEqual([...new Set(requests)].sort(), ['/', ...routes.keys()].sort());
    status = 'passed';
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
    const output = JSON.stringify({ status, browser: browserName, browserVersion, cases, blocked, errors }, null, 2);
    assert.ok(Buffer.byteLength(output) <= 16384, 'bounded evidence');
    fs.writeFileSync(path.join(evidence, 'browser-metadata-results.json'), output);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
