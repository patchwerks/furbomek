// Test import, render and validation failures without a Nitro build or sockets.
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {Server} from 'node:net';
import {test} from 'node:test';

const scenarios = [
  ['import failure', "throw new Error('fixture import failure');", /fixture import failure/],
  ['accessor failure', 'export const useNitroApp = undefined;', /Nitro app accessor/],
  ['fetch failure', "export function useNitroApp() { return {localFetch() {throw new Error('fixture fetch failure')}}; }", /fixture fetch failure/],
  ['bad status', "export function useNitroApp() { return {localFetch: async () => new Response('no', {status: 503})}; }", /503/],
  ['bad shell', "export function useNitroApp() { return {localFetch: async () => new Response('no root')}; }", /expected SPA shell/],
  ['valid shell', `export function useNitroApp() { return {localFetch: async () => new Response('<div id="__nuxt"></div>')}; }`, null],
];

for (const [name, body, expectedError] of scenarios) {
  test(name, async () => {
    const directory = await mkdtemp(path.join(tmpdir(), 'render-spa-test-'));
    const listen = Server.prototype.listen;
    const argv = process.argv;
    const write = process.stdout.write;
    let html = '';
    try {
      await mkdir(path.join(directory, 'server/chunks'), {recursive: true});
      // The marker also lets discovery locate the deliberate import-error fixture.
      await writeFile(path.join(directory, 'server/chunks/nitro.mjs'), `
        import {Server} from 'node:net';
        // function useNitroApp(
        const server = new Server();
        server.listen(0);
        if (server.listening) throw new Error('fixture unexpectedly opened listener');
        ${body}
      `);
      process.argv = [argv[0], argv[1], directory];
      process.stdout.write = chunk => { html += chunk; return true; };
      const render = import(new URL(`./render-spa.mjs?case=${encodeURIComponent(name)}`, import.meta.url));
      if (expectedError) await assert.rejects(render, expectedError);
      else {
        await render;
        assert.equal(html, '<div id="__nuxt"></div>');
      }
      assert.equal(Server.prototype.listen, listen, 'original listener must always be restored');
    } finally {
      process.argv = argv;
      process.stdout.write = write;
      Server.prototype.listen = listen;
      await rm(directory, {recursive: true, force: true});
    }
  });
}
