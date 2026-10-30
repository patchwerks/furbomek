// Test-only process boundary: run the real proxy on a private Unix socket.
const http = require('node:http');
const originalListen = http.Server.prototype.listen;
http.Server.prototype.listen = function () {
  return originalListen.call(this, process.env.PROXY_TEST_SOCKET, () => {
    process.send({ ready: true });
  });
};
global.fetch = async (url, options) => {
  process.send({ upstream: { url, method: options.method, headers: options.headers, body: options.body } });
  if (url.endsWith('/stream')) {
    return new Response(Buffer.from('RIFF-fixture-audio'), { status: 200, headers: { 'content-type': 'audio/wav' } });
  }
  return Response.json({ fixture: true, url });
};
require('../../tts-proxy.js');
