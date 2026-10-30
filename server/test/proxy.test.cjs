const assert = require('node:assert/strict');
const { fork } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs/promises');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { gzipSync } = require('node:zlib');

async function startProxy(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'proxy-test-'));
  const socketPath = path.join(dir, 'http.sock');
  const child = fork(path.join(__dirname, 'fixtures/proxy-process.cjs'), [], {
    env: { PROXY_TEST_SOCKET: socketPath },
    stdio: ['ignore', 'pipe', 'pipe', 'ipc'],
  });
  const upstream = [];
  let stderr = '';
  child.stdout.resume();
  child.stderr.on('data', chunk => { stderr += chunk; });
  child.on('message', message => { if (message.upstream) upstream.push(message.upstream); });
  t.after(async () => {
    if (child.exitCode === null && child.signalCode === null) {
      const exited = once(child, 'exit');
      child.kill();
      await exited;
    }
    await fs.rm(dir, { recursive: true, force: true });
  });
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Proxy startup timeout')), 3000);
    child.once('message', message => { clearTimeout(timeout); message.ready ? resolve() : reject(new Error('Not ready')); });
    child.once('exit', code => { clearTimeout(timeout); reject(new Error(`Proxy exited ${code}: ${stderr}`)); });
  });
  return { socketPath, child, upstream, stderr: () => stderr };
}

function request(proxy, { method = 'GET', route = '/proxy/playht/voices', body, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ socketPath: proxy.socketPath, path: route, method, headers, agent: false }, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString() }));
      res.on('error', reject);
    });
    req.setTimeout(3000, () => req.destroy(new Error('Request timeout')));
    req.on('error', reject);
    req.end(body);
  });
}

async function remainsResponsive(proxy) {
  // Wait for late decompressor errors, then exercise another request in the same process.
  await new Promise(resolve => setTimeout(resolve, 100));
  assert.equal(proxy.child.exitCode, null, proxy.stderr());
  assert.equal(proxy.child.signalCode, null, proxy.stderr());
  assert.equal((await request(proxy)).status, 200);
}

test('real proxy forwards JSON and streams provider bytes', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  const payload = { text: 'fixture text', voice: 'fixture voice' };
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', body: JSON.stringify(payload), headers: {
    'content-type': 'application/json', authorization: 'fixture-key', 'x-user-id': 'fixture-user',
  } });
  assert.equal(response.status, 200);
  assert.equal(response.headers['content-type'], 'audio/wav');
  assert.equal(response.body, 'RIFF-fixture-audio');
  const sent = proxy.upstream.find(event => event.method === 'POST');
  assert.deepEqual(JSON.parse(sent.body), payload);
  assert.equal(sent.headers.Authorization, 'fixture-key');
  assert.equal(sent.headers['X-USER-ID'], 'fixture-user');
});

test('valid gzip JSON keeps the existing supported request behavior', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  const payload = { text: 'compressed fixture' };
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', body: gzipSync(JSON.stringify(payload)), headers: {
    'content-type': 'application/json', 'content-encoding': 'gzip',
  } });
  assert.equal(response.status, 200);
  assert.deepEqual(JSON.parse(proxy.upstream[0].body), payload);
});

test('malformed JSON is rejected before upstream and the process recovers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', body: '{broken', headers: { 'content-type': 'application/json' } });
  assert.equal(response.status, 400);
  assert.equal(proxy.upstream.length, 0);
  await remainsResponsive(proxy);
});

test('oversized JSON is rejected before upstream and the process recovers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', body: JSON.stringify({ text: 'x'.repeat(110 * 1024) }), headers: { 'content-type': 'application/json' } });
  assert.equal(response.status, 413);
  assert.equal(proxy.upstream.length, 0);
  await remainsResponsive(proxy);
});

test('trailing bytes after a completed gzip frame cannot terminate the proxy', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  // A padding byte ends the gzip member before a later input chunk reaches zlib.
  // See the upstream body-parser regression for GHSA-27r3-jxmh-p828.
  const body = Buffer.concat([gzipSync('{"text":"fixture"}'), Buffer.from([0]), Buffer.alloc(100 * 1024, 0x58)]);
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', body, headers: {
    'content-type': 'application/json', 'content-encoding': 'gzip', 'content-length': body.length,
  } });
  assert.equal(response.status, 200);
  assert.equal(response.body, 'RIFF-fixture-audio');
  assert.equal(proxy.upstream.length, 1);
  await remainsResponsive(proxy);
});

test('all fixed metadata routes retain provider forwarding', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  for (const [route, target] of [
    ['/proxy/elevenlabs/voices', 'https://api.elevenlabs.io/v1/voices'],
    ['/proxy/elevenlabs/subscription', 'https://api.elevenlabs.io/v1/user/subscription'],
    ['/proxy/playht/voices', 'https://api.play.ht/api/v2/voices'],
    ['/proxy/playht/cloned-voices', 'https://api.play.ht/api/v2/cloned-voices'],
  ]) {
    const response = await request(proxy, { route });
    assert.equal(response.status, 200);
    assert.equal(JSON.parse(response.body).url, target);
  }
});
