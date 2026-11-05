import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { compileDraft, draftFromPack, newDraft } from '../builder.mjs';
import { parsePack, samplePack } from '../../../packages/extension-preview/index.mjs';

test('all starter drafts export exact parseable bytes and branded preview packs', () => {
  for (const preset of ['neutral', 'curious', 'acknowledge']) {
    const result = compileDraft(newDraft(preset));
    assert.equal(parsePack(result.bytes).packId, `${preset}-pack`);
    assert.equal(samplePack(result.pack, 0).expression, 'neutral');
    assert.equal(result.pack.events.length, preset === 'neutral' ? 1 : 2);
    assert.deepEqual(result.pack.capabilities, preset === 'acknowledge' ? ['presentation.expression', 'presentation.reaction'] : ['presentation.expression']);
    assert.deepEqual(compileDraft(draftFromPack(result.pack)).bytes, result.bytes);
  }
});
test('starter timing and capabilities match the three accepted examples', async () => {
  for (const preset of ['neutral', 'curious', 'acknowledge']) {
    const example = JSON.parse(await readFile(new URL(`../../../packages/extension-preview/examples/${preset}.json`, import.meta.url), 'utf8'));
    const authored = JSON.parse(new TextDecoder().decode(compileDraft(newDraft(preset)).bytes));
    assert.deepEqual({ ...authored, packId: example.packId }, example);
  }
});
test('serialization orders time stably, regenerates sequence and derives capabilities', () => {
  const draft = newDraft();
  draft.durationMs = '4000';
  draft.cues.push({ atMs: '2000', value: 'neutral' }, { atMs: '1000', value: 'curious' }, { atMs: '1000', value: 'acknowledge' });
  const { pack } = compileDraft(draft);
  assert.deepEqual(pack.events.map(event => [event.seq, event.atMs, event.value]), [[1, 0, 'neutral'], [2, 1000, 'curious'], [3, 1000, 'acknowledge'], [4, 2000, 'neutral']]);
  assert.equal(draft.cues[1].atMs, '2000', 'compilation does not mutate edit order');
  draft.cues.splice(3, 1);
  assert.deepEqual(compileDraft(draft).pack.capabilities, ['presentation.expression']);
});
test('invalid drafts cannot produce exports; shared parser retains contract bounds', () => {
  for (const [field, value] of [['packId', '../escape'], ['packVersion', '01.0.0'], ['durationMs', ''], ['durationMs', '0'], ['durationMs', '30001'], ['durationMs', '1.5']]) {
    const draft = newDraft(); draft[field] = value;
    assert.throws(() => compileDraft(draft));
  }
  for (const cue of [{ atMs: '', value: 'curious' }, { atMs: '0', value: 'curious' }, { atMs: '4000', value: 'neutral' }, { atMs: '1', value: 'motion' }]) {
    const draft = newDraft(); draft.cues.push(cue); assert.throws(() => compileDraft(draft));
  }
  for (const reset of [{ atMs: '1', value: 'neutral' }, { atMs: '0', value: 'curious' }]) {
    const draft = newDraft(); draft.cues[0] = reset; assert.throws(() => compileDraft(draft));
  }
  const draft = newDraft();
  while (draft.cues.length < 64) draft.cues.push({ atMs: '1', value: 'neutral' });
  assert.equal(compileDraft(draft).pack.events.length, 64);
  draft.cues.push({ atMs: '1', value: 'neutral' });
  assert.throws(() => compileDraft(draft));
});
