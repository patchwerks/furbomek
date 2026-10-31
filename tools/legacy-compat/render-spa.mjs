// Render the built SPA in process, without opening a listener.
import assert from 'node:assert/strict';
import {Server} from 'node:net';
import {readdir, readFile} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const output = path.resolve(process.argv[2] || '.output');
async function files(directory) {
  const entries = await readdir(directory, {withFileTypes: true});
  const nested = await Promise.all(entries.map(entry => {
    const filename = path.join(directory, entry.name);
    return entry.isDirectory() ? files(filename) : [filename];
  }));
  return nested.flat();
}
const candidates = [];
for (const filename of await files(path.join(output, 'server/chunks'))) {
  if (!filename.endsWith('.mjs')) continue;
  const source = await readFile(filename, 'utf8');
  if (!/function useNitroApp\(|(?:const|let) useNitroApp\s*=/.test(source)) continue;
  const exported = source.match(/\buseNitroApp as ([A-Za-z_$][\w$]*)/);
  candidates.push({filename, name: exported?.[1] || 'useNitroApp'});
}
assert.equal(candidates.length, 1, 'expected exactly one built Nitro app runtime');
const {filename, name} = candidates[0];
// Prevent the node-server preset's import-time bind in this test process.
// The external worker still denies all TCP/IP independently.
const originalListen = Server.prototype.listen;
const interceptedServers = [];
Server.prototype.listen = function () {
  interceptedServers.push(this);
  return this;
};
try {
  const runtime = await import(pathToFileURL(filename));
  assert.equal(typeof runtime[name], 'function', 'Nitro app accessor must be exported');
  const response = await runtime[name]().localFetch('/');
  assert.equal(response.status, 200);
  const html = await response.text();
  assert(html.includes('id="__nuxt"'), 'expected SPA shell');
  assert(interceptedServers.every(server => !server.listening), 'no server may listen');
  process.stdout.write(html);
} finally {
  Server.prototype.listen = originalListen;
}
