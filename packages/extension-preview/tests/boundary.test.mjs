import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdtemp, rm, symlink, mkdir, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import { loadPackFile } from '../load-file.mjs';
import { samplePack } from '../index.mjs';
const fixtureURL = new URL('../fixtures/reaction.json', import.meta.url);

test('canonical fixture loads from explicit regular file', async () => {
  const p = await loadPackFile(fixtureURL.pathname);
  assert.equal(p.durationMs,4000);
  assert.equal(samplePack(p,1000).reaction,'acknowledge');
  assert.equal(samplePack(p,3000).expression,'neutral');
});

test('loader rejects symlink, directory, FIFO, archive, malformed and oversized file', {timeout:5000}, async () => {
  const dir = await mkdtemp(join(tmpdir(),'preview-'));
  try {
    const regular = join(dir,'pack.json'); await writeFile(regular, await readFile(fixtureURL));
    const link = join(dir,'link.json'); await symlink(regular,link);
    const directory = join(dir,'directory'); await mkdir(directory);
    const fifo = join(dir,'fifo'); execFileSync('mkfifo',[fifo]);
    for (const path of [link,directory,fifo,join(dir,'missing')]) await assert.rejects(loadPackFile(path));
    for (const path of ['',null,{},'x\0y']) await assert.rejects(loadPackFile(path));
    for (const content of [Buffer.alloc(1048577,32),Buffer.from([0x50,0x4b,3,4]),Buffer.from('{')]) {await writeFile(regular,content); await assert.rejects(loadPackFile(regular));}
    assert.deepEqual((await readdir(dir)).sort(), ['directory','fifo','link.json','pack.json']);
  } finally {await rm(dir,{recursive:true,force:true});}
});

test('pure module works in constrained JS context without host imports or ambient access', async () => {
  // This audits attempted access for exercised parse/sample paths, not an OS sandbox.
  // The test runner itself must run only inside the credential-free CI worker.
  const source = await readFile(new URL('../index.mjs',import.meta.url),'utf8');
  const fixtureText = await readFile(fixtureURL,'utf8');
  const attempts = [];
  const denied = ['process','require','fetch','XMLHttpRequest','WebSocket','Worker','setTimeout','setInterval','setImmediate','localStorage','sessionStorage','document','window','navigator','Deno','Bun'];
  const globals = {TextDecoder};
  for (const name of denied) Object.defineProperty(globals,name,{get(){attempts.push(name); throw new Error('denied ambient '+name);}});
  const context = vm.createContext(globals,{codeGeneration:{strings:false,wasm:false}});
  const module = new vm.SourceTextModule(source,{context,importModuleDynamically(specifier){attempts.push(specifier); throw new Error('dynamic imports forbidden');}});
  await module.link(specifier => {attempts.push(specifier); throw new Error('imports forbidden');});
  await module.evaluate({timeout:1000});
  context.api = module.namespace;
  context.byteValues = [...new TextEncoder().encode(fixtureText)];
  const result = vm.runInContext('const p = api.parsePack(new Uint8Array(byteValues)); JSON.stringify(api.samplePack(p, 1300.5))',context,{timeout:1000});
  const state = JSON.parse(result);
  assert.equal(state.reaction,'acknowledge'); assert.equal(state.reactionProgress,300.5/600);
  assert.deepEqual(attempts,[]);
  assert.deepEqual(module.dependencySpecifiers,[]);
});

test('over-limit input is rejected before UTF-8 decoder construction', async () => {
  const source = await readFile(new URL('../index.mjs',import.meta.url),'utf8');
  let decoderCalls = 0;
  const context = vm.createContext({TextDecoder: class {constructor(){decoderCalls++; throw new Error('decoder must not run');}}});
  const module = new vm.SourceTextModule(source,{context});
  await module.link(() => {throw new Error('imports forbidden');}); await module.evaluate({timeout:1000});
  context.api = module.namespace;
  assert.throws(() => vm.runInContext('api.parsePack(new Uint8Array(1048577))',context,{timeout:1000}));
  assert.equal(decoderCalls,0);
});
