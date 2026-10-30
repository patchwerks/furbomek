const assert = require('node:assert/strict');
const { test } = require('node:test');
const express = require('express');
const proxyaddr = require('proxy-addr');

const forwarded = '198.51.100.42';

// Exercise the installed dependency and Express getters without opening a listener.
// These deliberately configured apps are fixtures, not the runtime proxy's policy.
function request(app, remoteAddress) {
  return Object.assign(Object.create(app.request), {
    app,
    headers: { 'x-forwarded-for': forwarded },
    connection: { remoteAddress },
  });
}

for (const subnet of ['::ffff:10.0.0.0/8', '::/1', ['::ffff:10.0.0.0/8', '192.168.0.0/16'], ['::/1', '192.168.0.0/16']]) {
  test(`IPv6 trust subnet ${subnet} does not trust arbitrary IPv4 peers`, () => {
    const app = express();
    app.set('trust proxy', subnet);
    const trust = proxyaddr.compile(subnet);
    for (const remoteAddress of ['203.0.113.7', '192.0.2.8', '::ffff:203.0.113.7']) {
      const req = request(app, remoteAddress);
      assert.deepEqual(
        { trusted: trust(remoteAddress), address: proxyaddr(req, trust), ip: req.ip, ips: req.ips },
        { trusted: false, address: remoteAddress, ip: remoteAddress, ips: [] },
      );
    }
  });
}

for (const subnet of ['10.0.0.0/8', '::ffff:10.0.0.0/104']) {
  test(`intended trust subnet ${subnet} preserves allowed and rejected peers`, () => {
    const app = express();
    app.set('trust proxy', subnet);
    const trust = proxyaddr.compile(subnet);
    for (const remoteAddress of ['10.1.2.3', '::ffff:10.1.2.3']) {
      const req = request(app, remoteAddress);
      assert.equal(trust(remoteAddress), true);
      assert.equal(proxyaddr(req, trust), forwarded);
      assert.equal(req.ip, forwarded);
      assert.deepEqual(req.ips, [forwarded]);
    }
    for (const remoteAddress of ['203.0.113.7', '::ffff:203.0.113.7']) {
      const req = request(app, remoteAddress);
      assert.deepEqual(
        { trusted: trust(remoteAddress), address: proxyaddr(req, trust), ip: req.ip, ips: req.ips },
        { trusted: false, address: remoteAddress, ip: remoteAddress, ips: [] },
      );
    }
  });
}

test('Express default policy ignores forwarded IP claims', () => {
  const app = express();
  const req = request(app, '203.0.113.7');
  assert.equal(app.get('trust proxy'), false);
  assert.equal(req.ip, '203.0.113.7');
  assert.deepEqual(req.ips, []);
});
