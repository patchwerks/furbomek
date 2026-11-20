import { randomUUID } from 'node:crypto';
import { readFile, writeFile, rename } from 'node:fs/promises';
import { stateSchema, sameEffect } from '../src/model.ts';
import type { State, Write } from '../src/model.ts';
import type { Effect, ReactionPack } from '../src/generated.ts';
import { FixtureError, validatePack } from './semantic.ts';

export function available(effect: Effect): boolean {
  switch (effect.capability) {
    case 'hud.redacted.v1': case 'graphics.pulse.v1': case 'sfx.preset.v1': return true;
    case 'motion.qualified.v1': case 'voice.reserved.v1': case 'face.reserved.v1': return false;
  }
}
function resource(effect: Effect): 'hud' | 'graphics' | 'sfx' {
  switch (effect.capability) {
    case 'hud.redacted.v1': return 'hud';
    case 'graphics.pulse.v1': return 'graphics';
    case 'sfx.preset.v1': return 'sfx';
    case 'motion.qualified.v1': case 'voice.reserved.v1': case 'face.reserved.v1': throw new FixtureError(422, 'Capability unavailable; no authority to apply.');
  }
}
export function timeline(pack: ReactionPack) {
  const ends = new Map<string, number>();
  const rows: {id: string; start_ms: number; end_ms: number; status: 'would_apply'|'skipped'|'would_cancel_pack'|'cancelled'; reason: string}[] = [];
  let pending = [...pack.cues];
  while (pending.length) {
    const ready = pending.filter(c => c.after.every(id => ends.has(id)));
    if (!ready.length) throw new FixtureError(422, 'Dependency cycle');
    for (const cue of ready) {
      const start = Math.max(0, ...cue.after.map(id => ends.get(id) ?? 0));
      const end = start + cue.effect.duration_ms;
      ends.set(cue.id, end);
      const permitted = available(cue.effect);
      rows.push({ id: cue.id, start_ms: start, end_ms: end, status: permitted ? 'would_apply' : cue.on_unavailable === 'cancel_pack' ? 'would_cancel_pack' : 'skipped', reason: permitted ? 'Synthetic fixture only; no dispatch' : 'Unavailable: no qualified motion or reserved adapter' });
    }
    pending = pending.filter(c => !ready.includes(c));
  }
  const cutoffs = rows.filter(row => row.status === 'would_cancel_pack').map(row => row.start_ms);
  if (cutoffs.length) {
    const cutoff = Math.min(...cutoffs);
    for (const row of rows) {
      if (row.status !== 'would_cancel_pack' && row.end_ms > cutoff) {
        row.status = 'cancelled';
        row.reason = `Pack would cancel at ${cutoff} ms; planned window will not complete`;
      }
    }
  }
  return rows;
}
export async function openStore(file: string) {
  let state: State = { mode: 'fixture', origin: 'synthetic-local', owner: 'fixture-owner', epoch: randomUUID(), revision: 0, health: 'fresh', applied: { capability: 'graphics.pulse.v1', preset: 'neutral', intensity_percent: 50, duration_ms: 1000 }, previous: null, saved: null, receipt: null, run: 'idle' };
  try {
    const previous = stateSchema.parse(JSON.parse(await readFile(file, 'utf8')));
    state = { ...previous, epoch: randomUUID(), health: 'stale', run: 'idle' };
  } catch (error) {
    if (!(error instanceof Error && 'code' in error && error.code === 'ENOENT')) throw error;
  }
  let disconnected = false;
  const persist = async () => { await writeFile(`${file}.new`, JSON.stringify(state), { mode: 0o600 }); await rename(`${file}.new`, file); };
  await persist();
  const check = (body: Write) => {
    if (disconnected || state.health !== 'fresh') throw new FixtureError(409, 'State is stale. Reconnect before writing.');
    if (body.epoch !== state.epoch || body.revision !== state.revision) throw new FixtureError(409, 'Revision changed. Reconnect and review your draft.');
  };
  const apply = (effect: Effect) => {
    const target = resource(effect);
    const previous = state.revision;
    state = { ...state, previous: state.applied, applied: effect, revision: previous + 1, run: 'idle', receipt: { schema_version: 1, status: 'applied', cue_id: 'studio', capability: effect.capability, resource: target, owner: 'fixture-owner', previous_revision: previous, revision: previous + 1, effective: effect, available: true } };
  };
  let queue: Promise<unknown> = Promise.resolve();
  async function mutate(action: string, body: Write) {
    if (action === 'reconnect') { disconnected = false; state = { ...state, health: 'fresh' }; await persist(); return state; }
    if (action === 'scenario') { disconnected = body.scenario === 'disconnect'; state = { ...state, health: body.scenario === 'fresh' ? 'fresh' : 'stale' }; await persist(); return state; }
    check(body);
    switch (action) {
      case 'preview':
        if (!body.effect || !available(body.effect)) throw new FixtureError(422, 'Capability unavailable; preview refused.');
        return { mode: 'fixture', dispatch: false, effect: body.effect };
      case 'apply':
        if (!body.effect) throw new FixtureError(422, 'Missing effect');
        apply(body.effect); break;
      case 'revert':
        if (!state.previous) throw new FixtureError(409, 'No previous applied state');
        apply(state.previous); break;
      case 'save':
        if (!body.saved || !available(body.saved.effect)) throw new FixtureError(422, 'Unavailable effect cannot be saved');
        await validatePack(body.saved.pack);
        if (!sameEffect(body.saved.effect, state.applied)) throw new FixtureError(409, 'Save requires the exact applied effect');
        state = { ...state, saved: body.saved }; break;
      case 'restore':
        if (!state.saved) throw new FixtureError(409, 'No saved preset');
        apply(state.saved.effect); break;
      case 'dry-run': {
        if (!body.pack) throw new FixtureError(422, 'Missing reaction');
        await validatePack(body.pack);
        state = { ...state, run: 'previewed' }; await persist();
        const rows = timeline(body.pack);
        return { mode: 'fixture', dispatch: false, timeline: rows, horizon_ms: Math.max(...rows.map(r => r.end_ms)) };
      }
      case 'cancel': state = { ...state, run: 'cancelled' }; break;
      default: throw new FixtureError(404, 'Unknown fixture action');
    }
    await persist();
    return state;
  }
  return {
    read() { if (disconnected) throw new FixtureError(503, 'Fixture network disconnected'); return state; },
    mutate(action: string, body: Write) {
      const operation = queue.then(() => mutate(action, body));
      queue = operation.then(() => undefined, () => undefined);
      return operation;
    }
  };
}
