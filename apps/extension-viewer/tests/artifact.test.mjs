import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, lstat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const app = fileURLToPath(new URL('../', import.meta.url));

test('standalone static artifact has a restrictive browser capability policy', async () => {
  const html = await readFile(path.join(app, '.output/public/index.html'), 'utf8');
  assert.match(html, /Content-Security-Policy/);
  for (const directive of ["connect-src 'self'", "object-src 'none'", "form-action 'none'", "media-src 'none'"]) assert.ok(html.includes(directive), directive);
  assert.doesNotMatch(html, /<(?:script|iframe)[^>]+src=["']https?:/i);
});

test('viewer source ships no borrowed model, texture, photograph, or executable dependency hook', async () => {
  const manifest = JSON.parse(await readFile(path.join(app, 'package.json'), 'utf8'));
  assert.equal(manifest.scripts, undefined);
  assert.deepEqual(manifest.dependencies, { three: '0.187.0' });
  const excluded = new Set(['node_modules', '.nuxt', '.output', 'tests']);
  async function inspect(dir) {
    for (const name of await readdir(dir)) {
      if (excluded.has(name)) continue;
      const file = path.join(dir, name);
      const stat = await lstat(file);
      assert.equal(stat.isSymbolicLink(), false);
      if (stat.isDirectory()) await inspect(file);
      else assert.ok(path.relative(app, file) === 'public/THREE-LICENSE.txt' || ['.vue', '.mjs', '.cjs', '.ts', '.json', '.css', '.md'].includes(path.extname(name)), `unreviewed asset ${name}`);
    }
  }
  await inspect(app);
});

test('static build excludes legacy credentials, microphone UI, and root public assets', async () => {
  const output = path.join(app, '.output/public');
  async function files(dir) {
    const result = [];
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      result.push(...(entry.isDirectory() ? await files(file) : [file]));
    }
    return result;
  }
  const built = await files(output);
  const legacy = path.resolve(app, '../../public');
  const legacyFiles = await files(legacy);
  for (const file of legacyFiles) {
    assert.equal(built.includes(path.join(output, path.relative(legacy, file))), false, `root public leaked: ${file}`);
  }
  for (const file of built.filter(file => /\.(js|html)$/.test(file))) {
    const source = await readFile(file, 'utf8');
    assert.doesNotMatch(source, /dangerouslyAllowBrowser|api\.elevenlabs\.io|api\.openai\.com|api\.play\.ht|tts-proxy|src\/settings\.ts|src\/chat\/openai-assistant/);
  }
});
