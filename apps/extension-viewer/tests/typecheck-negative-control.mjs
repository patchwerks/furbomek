/** Runs only against /scratch/source in the credential-free offline compiler worker. */
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

assert.equal(process.cwd(), '/scratch/source', 'negative control requires the disposable worker copy');
const file = 'apps/extension-viewer/app.vue';
const original = readFileSync(file, 'utf8');
const anchor = 'function draw() {';
assert.equal(original.split(anchor).length, 2, 'one draw function must be instrumented');
const checker = './node_modules/.bin/vue-tsc';
const args = ['--noEmit', '-p', 'apps/extension-viewer/tsconfig.json'];
function check(label) {
  const result = spawnSync(checker, args, { encoding: 'utf8', timeout: 120000, maxBuffer: 8 * 1024 * 1024 });
  process.stdout.write(`${label}\n${result.stdout ?? ''}${result.stderr ?? ''}\n`);
  assert.ifError(result.error);
  assert.equal(result.signal, null, 'checker must finish normally');
  return result;
}
try {
  writeFileSync(file, original.replace(anchor, `${anchor} const n = 1; n.foo.bar();`));
  const negative = check('Injected draw error');
  assert.equal(negative.status, 2, 'vue-tsc must reject the deliberate type error');
  const diagnostics = `${negative.stdout}${negative.stderr}`;
  assert.equal(diagnostics.split('error TS').length - 1, 1, 'only the deliberate diagnostic is accepted');
  assert.match(diagnostics, /(?:^|\n)(?:apps\/extension-viewer\/)?app\.vue\(\d+,\d+\): error TS2339: Property 'foo' does not exist on type '(?:1|number)'\./);
} finally {
  writeFileSync(file, original);
  assert.equal(readFileSync(file, 'utf8'), original, 'restore exact source bytes');
}
const restored = check('Restored viewer source');
assert.equal(restored.status, 0, 'the identical checker must accept the restored source');
process.stdout.write('PASS: baseline accepted; draw mutation rejected with app.vue TS2339; restored source accepted.\n');
