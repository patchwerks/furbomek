import { parsePack } from '../../packages/extension-preview/index.mjs';

export function newDraft(preset = 'neutral') {
  if (!['neutral', 'curious', 'acknowledge'].includes(preset)) throw new TypeError('Unknown starter preset.');
  const durationMs = { neutral: '1200', curious: '2000', acknowledge: '1600' }[preset];
  const atMs = preset === 'curious' ? '400' : '300';
  return {
    packId: `${preset}-pack`, packVersion: '0.1.0', durationMs,
    cues: [{ atMs: '0', value: 'neutral' }, ...(preset === 'neutral' ? [] : [{ atMs, value: preset }])],
  };
}
export function draftFromPack(pack) {
  return { packId: pack.packId, packVersion: pack.packVersion, durationMs: String(pack.durationMs),
    cues: pack.events.map(event => ({ atMs: String(event.atMs), value: event.value })) };
}
function integer(value, label) {
  if (!/^\d+$/.test(value)) throw new TypeError(`${label} must be a whole number of milliseconds.`);
  return Number(value);
}
export function compileDraft(draft) {
  if (draft.cues.length < 1 || draft.cues.length > 64) throw new TypeError('Use 1 to 64 cues, including the locked reset.');
  if (draft.cues[0].atMs !== '0' || draft.cues[0].value !== 'neutral') throw new TypeError('The first cue must remain the neutral reset at 0 ms.');
  const events = draft.cues.map((cue, index) => {
    if (!['neutral', 'curious', 'acknowledge'].includes(cue.value)) throw new TypeError(`Cue ${index + 1} has an unsupported value.`);
    return { atMs: integer(cue.atMs, `Cue ${index + 1} time`), kind: cue.value === 'acknowledge' ? 'presentation.reaction' : 'presentation.expression', value: cue.value, index };
  }).sort((a, b) => a.atMs - b.atMs || a.index - b.index)
    .map((event, i) => ({ seq: i + 1, atMs: event.atMs, kind: event.kind, value: event.value }));
  const data = { schemaVersion: 1, packId: draft.packId, packVersion: draft.packVersion, previewContractVersion: 1,
    capabilities: ['presentation.expression', ...(events.some(event => event.kind === 'presentation.reaction') ? ['presentation.reaction'] : [])],
    durationMs: integer(draft.durationMs, 'Duration'), events };
  const bytes = new TextEncoder().encode(`${JSON.stringify(data, null, 2)}\n`);
  return { bytes, pack: parsePack(bytes) };
}
