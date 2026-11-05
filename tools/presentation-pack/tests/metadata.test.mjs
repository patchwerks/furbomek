import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, writeFile, symlink, mkdir, rm, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { parseMetadata, createMetadata, matchMetadata, MAX_METADATA_BYTES } from '../metadata.mjs';
import { readPack, readMetadata, readBoundedFile } from '../files.mjs';
import { parsePack } from '../../../packages/extension-preview/index.mjs';
const cli = fileURLToPath(new URL('../cli.mjs', import.meta.url));
const example = fileURLToPath(new URL('../../../packages/extension-preview/examples/neutral.json', import.meta.url));
const encode = value => Buffer.from(JSON.stringify(value));
const fixture = { metadataVersion: 1, packId: 'example', packVersion: '1.0.0', previewContractVersion: 1,
  author: 'Example Author', license: 'MIT', packSha256: 'a'.repeat(64) };
const run = args => spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', timeout: 5000, env: { PATH: process.env.PATH } });
async function temporary(fn) {
  const dir = await mkdtemp(join(tmpdir(), 'pack-metadata-'));
  try { await fn(dir); } finally { await rm(dir, { recursive: true, force: true }); }
}

test('flat metadata accepts both explicit licenses and printable Unicode author', () => {
  for (const license of ['MIT', 'CC0-1.0']) {
    const value = parseMetadata(encode({ ...fixture, license, author: 'Zoë 山' }));
    assert.equal(value.license, license); assert.ok(Object.isFrozen(value));
  }
});
for (const [label, change] of [
  ['unknown key', { path: '/tmp/data' }], ['nested field', { author: {} }], ['array', { author: [] }],
  ['null', { author: null }], ['boolean', { metadataVersion: true }], ['string version', { metadataVersion: '1' }],
  ['future version', { metadataVersion: 2 }], ['future protocol', { previewContractVersion: 2 }],
  ['wrong id', { packId: 'Bad' }], ['id newline', { packId: 'example\n' }], ['bad semver', { packVersion: '01.0.0' }],
  ['hash uppercase', { packSha256: 'A'.repeat(64) }], ['hash newline', { packSha256: 'a'.repeat(64) + '\n' }],
  ['empty author', { author: '' }], ['long author', { author: 'a'.repeat(81) }], ['surrounding space', { author: ' X' }],
  ['control', { author: 'A\x1bB' }], ['bidi', { author: 'A\u202eB' }], ['surrogate', { author: '\ud800' }],
  ['line separator', { author: 'A\u2028B' }], ['unapproved license', { license: 'Apache-2.0' }],
]) test(`rejects ${label}`, () => assert.throws(() => parseMetadata(encode({ ...fixture, ...change }))));

test('strict JSON rejects duplicate decoded keys and malformed encodings/grammar', () => {
  const valid = JSON.stringify(fixture);
  for (const text of [valid.replace('"metadataVersion":1', '"metadataVersion":1,"metadata\\u0056ersion":1'),
    valid.replace('"author":"Example Author"', '"author":"Example Author","author":"Second"'),
    valid + '{}', valid.replace(/}$/, ',}'), valid.slice(0, -1), '[]', '{}', '\ufeff' + valid,
    valid.replace(':1,', ':01,'), valid.replace(':1,', ':1e999,'), valid.replace('"MIT"', '"MIT\n"')]) {
    assert.throws(() => parseMetadata(Buffer.from(text)));
  }
  assert.throws(() => parseMetadata(Buffer.from([0xff])));
  assert.throws(() => parseMetadata(Buffer.alloc(MAX_METADATA_BYTES + 1, 32)));
  assert.throws(() => parseMetadata('text'));
  const exact = Buffer.concat([Buffer.from(valid), Buffer.alloc(MAX_METADATA_BYTES - Buffer.byteLength(valid), 32)]);
  assert.equal(parseMetadata(exact).author, fixture.author);
});

test('same bytes feed unchanged core parser and digest; whitespace tampering invalidates companion', async () => temporary(async dir => {
  const path = join(dir, 'pack.json'); const original = await readFile(example);
  await writeFile(path, original); const loaded = await readPack(path);
  assert.deepEqual(loaded.bytes, new Uint8Array(original));
  assert.deepEqual(loaded.pack, parsePack(original));
  assert.equal(loaded.packSha256, createHash('sha256').update(original).digest('hex'));
  const metadata = createMetadata(loaded, 'Test Author', 'CC0-1.0');
  assert.equal(matchMetadata(metadata, loaded), metadata);
  for (const [key, value] of [['packId', 'another'], ['packVersion', '2.0.0'], ['previewContractVersion', 2]]) {
    assert.throws(() => matchMetadata({ ...metadata, [key]: value }, loaded));
  }
  await writeFile(path, Buffer.concat([original, Buffer.from('\n')]));
  const changed = await readPack(path); assert.deepEqual(changed.pack, loaded.pack);
  assert.throws(() => matchMetadata(metadata, changed), /digest/);
}));

test('regular file, symlink, missing, directory, FIFO, and size boundaries', async () => temporary(async dir => {
  const path = join(dir, 'file'); await writeFile(path, 'abc');
  assert.deepEqual(await readBoundedFile(path, 3), new Uint8Array(Buffer.from('abc')));
  await assert.rejects(readBoundedFile(path, 2), /byte limit/);
  await symlink(path, join(dir, 'link'));
  for (const input of [dir, join(dir, 'link'), join(dir, 'missing'), '', 'nul\0name']) await assert.rejects(readPack(input));
  for (const budget of [0, -1, Infinity, 1048577]) await assert.rejects(readBoundedFile(path, budget));
  const fifo = join(dir, 'fifo');
  const made = spawnSync('mkfifo', [fifo], { timeout: 1000 });
  assert.equal(made.status, 0); await assert.rejects(readPack(fifo), /regular file/);
  await writeFile(path, Buffer.alloc(1048577)); await assert.rejects(readPack(path), /byte limit/);
  await writeFile(path, Buffer.alloc(MAX_METADATA_BYTES + 1)); await assert.rejects(readMetadata(path), /byte limit/);
  await writeFile(path, '{'); await assert.rejects(readPack(path));
}));

test('CLI templates, validates matched/absent, rejects tampering and never writes output files', async () => temporary(async dir => {
  const path = join(dir, 'pack.json'); const meta = join(dir, 'metadata.json');
  await writeFile(path, await readFile(example));
  const before = await readdir(dir);
  const generated = run(['template', path, '--author', 'Test Author', '--license', 'MIT']);
  assert.equal(generated.status, 0, generated.stderr); assert.equal(generated.stderr, '');
  assert.equal(parseMetadata(Buffer.from(generated.stdout)).author, 'Test Author');
  assert.deepEqual(await readdir(dir), before);
  await writeFile(meta, generated.stdout);
  for (const args of [['validate', path, '--json'], ['validate', path, '--metadata', meta, '--json']]) {
    const result = run(args); assert.equal(result.status, 0, result.stderr); assert.equal(result.stderr, '');
    assert.equal(JSON.parse(result.stdout).metadata, args.includes('--metadata') ? 'matched' : 'absent');
  }
  const plain = run(['validate', path]); assert.equal(plain.status, 0); assert.match(plain.stdout, /metadata absent/);
  await writeFile(path, Buffer.concat([await readFile(path), Buffer.from(' ')]));
  const invalid = run(['validate', path, '--metadata', meta, '--json']);
  assert.equal(invalid.status, 1); assert.equal(JSON.parse(invalid.stdout).ok, false); assert.equal(invalid.stderr, '');
  assert.deepEqual((await readdir(dir)).sort(), ['metadata.json', 'pack.json']);
}));

test('CLI usage and file failures have stable distinct exits and terminal-safe output', async () => temporary(async dir => {
  for (const args of [[], ['other', example], ['validate'], ['template', example],
    ['validate', example, '--unknown'], ['validate', example, '--json', '--json'],
    ['validate', example, '--metadata'], ['template', example, '--author', 'X', '--license', 'MIT', 'extra']]) {
    const result = run(args); assert.equal(result.status, 2); assert.match(result.stderr, /Usage/);
  }
  const usage = run(['validate', '--json']); assert.equal(usage.status, 2); assert.equal(JSON.parse(usage.stdout).error, 'usage');
  const template = run(['template', example, '--author', 'X', '--license', 'bad']); assert.equal(template.status, 1); assert.equal(template.stdout, '');
  const hostile = join(dir, '\x1b[31m\n\u202efile');
  for (const json of [false, true]) {
    const result = run(['validate', hostile, ...(json ? ['--json'] : [])]);
    assert.equal(result.status, 1); assert.doesNotMatch(result.stdout + result.stderr, /[\x1b\u202e]/);
    if (json) assert.equal(JSON.parse(result.stdout).ok, false);
  }
  await writeFile(hostile, await readFile(example));
  const success = run(['validate', hostile]); assert.equal(success.status, 0); assert.doesNotMatch(success.stdout, /[\x1b\u202e]/);
}));

test('descriptor race checks fail closed and close handles; unsupported flags never open', async () => {
  const { SourceTextModule, SyntheticModule, createContext } = await import('node:vm');
  const source = await readFile(new URL('../files.mjs', import.meta.url), 'utf8');
  const base = { dev: 1n, ino: 2n, size: 3n, mtimeNs: 4n, ctimeNs: 5n, isFile: () => true };
  for (const scenario of ['unsupported', 'open-identity', 'read-time', 'path-replaced', 'short-read', 'growth', 'ok']) {
    let stats = 0; let paths = 0; let reads = 0; let opens = 0; let closes = 0;
    const context = createContext({ Uint8Array, TypeError, Error, Number, BigInt });
    const fs = {
      lstat: async () => ({ ...base, ...(scenario === 'path-replaced' && paths++ > 0 ? { ino: 9n } : {}) }),
      open: async () => {
        opens++;
        return {
          stat: async () => ({ ...base, ...(scenario === 'open-identity' ? { ino: 9n } : {}),
            ...(scenario === 'read-time' && stats++ > 0 ? { mtimeNs: 9n } : {}) }),
          read: async buffer => {
            reads++;
            if (reads > 1) return { bytesRead: 0 };
            const count = scenario === 'short-read' ? 2 : scenario === 'growth' ? 4 : 3;
            buffer.set(new Uint8Array(count).fill(97)); return { bytesRead: count };
          },
          close: async () => { closes++; },
        };
      },
    };
    const modules = {
      'node:fs': { constants: { O_RDONLY: 0, O_NOFOLLOW: scenario === 'unsupported' ? 0 : 1, O_NONBLOCK: 2 } },
      'node:fs/promises': fs, 'node:crypto': { createHash },
      '../../packages/extension-preview/index.mjs': { MAX_PACK_BYTES: 1048576, parsePack },
      './metadata.mjs': { MAX_METADATA_BYTES, parseMetadata },
    };
    const module = new SourceTextModule(source, { context });
    await module.link(async name => {
      const values = modules[name]; assert.ok(values, 'only fixed expected imports');
      return new SyntheticModule(Object.keys(values), function () {
        for (const [key, value] of Object.entries(values)) this.setExport(key, value);
      }, { context });
    });
    await module.evaluate();
    if (scenario === 'ok') assert.deepEqual(await module.namespace.readBoundedFile('explicit', 3), new Uint8Array([97, 97, 97]));
    else await assert.rejects(module.namespace.readBoundedFile('explicit', 3));
    assert.equal(opens, scenario === 'unsupported' ? 0 : 1);
    assert.equal(closes, opens);
    assert.ok(reads <= 2);
  }
});
