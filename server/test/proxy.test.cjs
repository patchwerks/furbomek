const assert = require('node:assert/strict');
const { fork } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs/promises');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { gzipSync } = require('node:zlib');

async function startProxy(t, mode = '') {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'proxy-test-'));
  const socketPath = path.join(dir, 'http.sock');
  const child = fork(path.join(__dirname, 'fixtures/proxy-process.cjs'), [], {
    env: { PROXY_TEST_SOCKET: socketPath, PROXY_TEST_MODE: mode },
    stdio: ['ignore', 'pipe', 'pipe', 'ipc'],
  });
  const upstream = [];
  let stderr = '';
  let stdout = '';
  const events = [];
  child.stdout.on('data', chunk => { stdout += chunk; });
  child.on('message', message => events.push(message));
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
  return { socketPath, child, upstream, events, stderr: () => stderr, output: () => stdout + stderr };
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

const routes = ['/proxy/elevenlabs/voices', '/proxy/elevenlabs/subscription',
  '/proxy/playht/voices', '/proxy/playht/cloned-voices', '/proxy/playht/stream'];
const safeError = { error: 'Upstream service request failed.' };
function routeOptions(route) {
  return { route, method: route.endsWith('/stream') ? 'POST' : 'GET',
    headers: { authorization: 'fixture-secret-token', 'xi-api-key': 'fixture-secret-token' } };
}
function noLeak(proxy, response) {
  assert.doesNotMatch(JSON.stringify(response) + proxy.output(),
    /fixture-secret-token|private\/fixture-path|provider-body|stack-marker|x-provider-secret/);
  assert.equal(proxy.events.some(event => event.forbiddenRead), false);
}
for (const route of routes) {
  for (const mode of ['transport', 'status:400', 'status:401', 'status:429', 'status:503',
    'status:0', 'status:199', 'status:302', 'status:600', 'status:NaN', 'status:200.5']) {
    test(`${route} safely handles ${mode}`, { timeout: 6000 }, async t => {
      const proxy = await startProxy(t, mode);
      const response = await request(proxy, routeOptions(route));
      const status = Number(mode.slice(7));
      assert.equal(response.status, Number.isInteger(status) && status >= 400 && status <= 599 ? status : 502);
      assert.deepEqual(JSON.parse(response.body), safeError);
      noLeak(proxy, response);
      await remainsResponsive(proxy);
    });
  }
  if (!route.endsWith('/stream')) test(`${route} rejects invalid upstream JSON`, { timeout: 6000 }, async t => {
    const proxy = await startProxy(t, 'json');
    const response = await request(proxy, routeOptions(route));
    assert.equal(response.status, 502);
    assert.deepEqual(JSON.parse(response.body), safeError);
    noLeak(proxy, response);
    await remainsResponsive(proxy);
  });
}

test('early audio failure returns fixed JSON without upstream headers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'early');
  const response = await request(proxy, routeOptions('/proxy/playht/stream'));
  assert.equal(response.status, 502);
  assert.deepEqual(JSON.parse(response.body), safeError);
  noLeak(proxy, response);
  await remainsResponsive(proxy);
});

test('late audio failure terminates incomplete bytes without JSON and recovers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'late');
  const result = await new Promise((resolve, reject) => {
    const req = http.request({ socketPath: proxy.socketPath, path: '/proxy/playht/stream', method: 'POST', agent: false }, res => {
      let body = '';
      res.on('data', chunk => { body += chunk; });
      res.on('end', () => reject(new Error('Incomplete stream ended successfully')));
      res.on('error', () => resolve({ body, complete: res.complete }));
    });
    req.on('error', reject);
    req.setTimeout(3000, () => req.destroy(new Error('Request timeout')));
    req.end();
  });
  assert.equal(result.body, 'RIFF-partial');
  assert.equal(result.complete, false);
  noLeak(proxy, result);
  await remainsResponsive(proxy);
});

for (const mode of ['disconnect', 'large-disconnect']) test(`${mode} cancels provider reader and process recovers`, { timeout: 10000 }, async t => {
  const proxy = await startProxy(t, mode);
  await new Promise((resolve, reject) => {
    const req = http.request({ socketPath: proxy.socketPath, path: '/proxy/playht/stream', method: 'POST', agent: false }, res => {
      res.once('data', () => { res.destroy(); resolve(); });
      res.on('error', () => {});
    });
    req.on('error', reject);
    req.setTimeout(3000, () => req.destroy(new Error('Request timeout')));
    req.end();
  });
  await remainsResponsive(proxy);
  assert.ok(proxy.events.some(event => event.cancelled));
  noLeak(proxy, {});
});

test('successful audio retains partial status and content headers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'success206');
  const response = await request(proxy, routeOptions('/proxy/playht/stream'));
  assert.equal(response.status, 206);
  assert.equal(response.body, 'RIFF-fixture-audio');
  assert.equal(response.headers['content-length'], '18');
  assert.equal(response.headers['content-range'], 'bytes 0-17/18');
});

for (const [headers, body, status, error] of [
  [{ 'content-type': 'application/json' }, '{"fixture-secret-token":', 400, 'Invalid JSON request body.'],
  [{ 'content-type': 'application/json' }, JSON.stringify({ text: 'fixture-secret-token'.repeat(10000) }), 413, 'Request body is too large.'],
  [{ 'content-type': 'application/json', 'content-encoding': 'fixture-secret-token' }, '{}', 415, 'Unsupported request encoding.'],
  [{ 'content-type': 'application/json; charset=fixture-secret-token' }, '{}', 415, 'Unsupported request charset.'],
]) test(`parser returns fixed ${status} ${error}`, { timeout: 6000 }, async t => {
  const proxy = await startProxy(t);
  const response = await request(proxy, { method: 'POST', route: '/proxy/playht/stream', headers, body });
  assert.equal(response.status, status);
  assert.deepEqual(JSON.parse(response.body), { error });
  assert.equal(proxy.upstream.length, 0);
  noLeak(proxy, response);
  await remainsResponsive(proxy);
});


test('disconnect during pending fetch cancels body before a read can hang', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'pending-disconnect');
  const req = http.request({ socketPath: proxy.socketPath, path: '/proxy/playht/stream', method: 'POST', agent: false });
  req.on('error', () => {});
  req.end();
  // Observe the fixture entering fetch before disconnecting, without relying on a
  // scheduling delay to establish that the request reached the real route.
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('No upstream request')), 1000);
    const check = message => {
      if (message.upstream) { clearTimeout(timer); proxy.child.off('message', check); resolve(); }
    };
    proxy.child.on('message', check);
  });
  req.destroy();
  await new Promise(resolve => setTimeout(resolve, 200));
  assert.ok(proxy.events.some(event => event.cancelled));
  await remainsResponsive(proxy);
  noLeak(proxy, {});
});

test('unknown middleware failures return generic 500 without default stack pages', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'unknown-parser');
  const response = await request(proxy);
  assert.equal(response.status, 500);
  assert.deepEqual(JSON.parse(response.body), { error: 'Internal server error.' });
  noLeak(proxy, response);
  await remainsResponsive(proxy);
});


test('header setup failure clears already staged provider headers', { timeout: 6000 }, async t => {
  const proxy = await startProxy(t, 'header-failure');
  const response = await request(proxy, routeOptions('/proxy/playht/stream'));
  assert.equal(response.status, 502);
  assert.deepEqual(JSON.parse(response.body), safeError);
  noLeak(proxy, response);
  await remainsResponsive(proxy);
  assert.ok(proxy.events.some(event => event.cancelled));
});

test('large audio chunks survive backpressure and preserve all bytes', { timeout: 10000 }, async t => {
  const proxy = await startProxy(t, 'large');
  const response = await request(proxy, routeOptions('/proxy/playht/stream'));
  assert.equal(response.status, 200);
  assert.equal(response.body, 'A'.repeat(2 * 1024 * 1024));
  await remainsResponsive(proxy);
});
