// Test-only process boundary: run the real proxy on a private Unix socket.
const http = require('node:http');
const originalListen = http.Server.prototype.listen;
http.Server.prototype.listen = function () {
  return originalListen.call(this, process.env.PROXY_TEST_SOCKET, () => {
    process.send({ ready: true });
  });
};
const hostile = 'fixture-secret-token /private/fixture-path provider-body stack-marker';
let calls = 0;
global.fetch = async (url, options) => {
  process.send({ upstream: { url, method: options.method, headers: options.headers, body: options.body } });
  const mode = calls++ === 0 ? process.env.PROXY_TEST_MODE : '';
  if (mode === 'transport') throw new Error(hostile);
  if (mode === 'json') return new Response(hostile, { headers: { 'content-type': 'application/json' } });
  if (mode?.startsWith('status:')) {
    const status = Number(mode.slice(7));
    return { status, headers: new Headers({ 'x-provider-secret': hostile }),
      json() { process.send({ forbiddenRead: true }); throw new Error(hostile); },
      body: { cancel() { process.send({ cancelled: true }); return Promise.resolve(); } } };
  }
  if (mode === 'pending-disconnect') await new Promise(resolve => setTimeout(resolve, 100));
  if (mode === 'early' || mode === 'late' || mode === 'disconnect' || mode === 'pending-disconnect' || mode === 'large-disconnect') {
    let reads = 0;
    return new Response(new ReadableStream({
      async pull(controller) {
        if (mode === 'pending-disconnect') return new Promise(() => {});
        if (mode === 'early') { controller.error(new Error(hostile)); return; }
        if (reads++ === 0) { controller.enqueue(mode === 'large-disconnect' ? Buffer.alloc(2 * 1024 * 1024, 65) : Buffer.from('RIFF-partial')); return; }
        if (mode === 'disconnect' || mode === 'large-disconnect') return new Promise(() => {});
        await new Promise(resolve => setTimeout(resolve, 50));
        controller.error(new Error(hostile));
      },
      cancel() { process.send({ cancelled: true }); },
    }, { highWaterMark: 0 }), { headers: { 'content-type': 'audio/wav', 'x-provider-secret': hostile } });
  }
  if (mode === 'header-failure') return {
    status: 200,
    body: new ReadableStream({
      start(controller) { controller.enqueue(Buffer.from('RIFF')); },
      cancel() { process.send({ cancelled: true }); },
    }),
    headers: { forEach(callback) {
      callback(hostile, 'x-provider-secret');
      callback('invalid\nheader', 'content-type');
    } },
  };
  if (mode === 'large') return new Response(Buffer.alloc(2 * 1024 * 1024, 65), {
    headers: { 'content-type': 'audio/wav' },
  });
  if (mode === 'success206') return new Response(Buffer.from('RIFF-fixture-audio'), {
    status: 206, headers: { 'content-type': 'audio/wav', 'content-length': '18', 'content-range': 'bytes 0-17/18' },
  });
  if (url.endsWith('/stream')) {
    return new Response(Buffer.from('RIFF-fixture-audio'), { status: 200, headers: { 'content-type': 'audio/wav' } });
  }
  return Response.json({ fixture: true, url });
};
if (process.env.PROXY_TEST_MODE === 'unknown-parser') {
  const express = require('express');
  const originalJson = express.json;
  express.json = (...args) => {
    const parser = originalJson(...args);
    let failed = false;
    return (req, res, next) => {
      if (!failed) { failed = true; next(new Error(hostile)); }
      else parser(req, res, next);
    };
  };
}
require('../../tts-proxy.js');
