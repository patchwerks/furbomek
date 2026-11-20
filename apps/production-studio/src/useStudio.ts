import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import ky, { HTTPError } from 'ky';
import fixture from '../../../packages/production-contracts/fixtures/liquidation.json';
import { effectSchema, reactionPackSchema } from './generated.ts';
import type { Effect } from './generated.ts';
import { initialFraming, sameEffect, previewSchema, savedSchema, stateSchema } from './model.ts';
import type { State, Preview, Page, Write } from './model.ts';

const http = ky.create({ timeout: 18000, retry: 0 });
export function useStudio() {
  const mode = new URLSearchParams(location.search).get('mode') === 'fixture' ? 'fixture' : 'unavailable';
  const state = ref<State | null>(null);
  const page = ref<Page>('effects');
  const draft = ref<Effect>({ capability: 'graphics.pulse.v1', preset: 'neutral', intensity_percent: 50, duration_ms: 1000 });
  const pack = ref(reactionPackSchema.parse(fixture));
  const framing = ref(structuredClone(initialFraming));
  const binding = ref<'liquidation' | 'viewer-reaction' | 'unbound'>('liquidation');
  const preview = ref<Preview | null>(null);
  const message = ref('');
  const error = ref('');
  const busy = ref(false);
  const connected = ref(false);
  const ready = computed(() => mode === 'fixture' && connected.value && state.value?.health === 'fresh' && !busy.value);
  const dirty = computed(() => !state.value || !sameEffect(draft.value, state.value.applied));
  const blocked = computed(() => ['motion.qualified.v1','voice.reserved.v1','face.reserved.v1'].includes(draft.value.capability));
  let generation = 0;
  let timer: ReturnType<typeof setInterval> | undefined;
  const invalidate = () => { preview.value = null; generation += 1; };
  watch([draft, pack], invalidate, { deep: true, flush: 'sync' });
  function accept(next: State, replace = false) {
    if (state.value && (next.epoch !== state.value.epoch || next.revision !== state.value.revision)) {
      invalidate();
      if (!replace) message.value = 'Applied state changed. Your draft is preserved; preview it again before applying.';
    }
    state.value = next; connected.value = true;
    if (replace) draft.value = structuredClone(next.applied);
    if (next.health !== 'fresh') invalidate();
  }
  async function failure(cause: unknown) {
    invalidate();
    if (cause instanceof HTTPError) {
      const data: unknown = await cause.response.json();
      error.value = typeof data === 'object' && data !== null && 'error' in data && typeof data.error === 'string' ? data.error : `Request failed (${cause.response.status})`;
      if (cause.response.status === 409 || cause.response.status >= 500) connected.value = false;
    } else if (cause instanceof Error) { error.value = 'Disconnected or invalid response. Reconnect to refresh state.'; connected.value = false; }
    else throw cause;
  }
  async function refresh(initial = false) {
    if (mode !== 'fixture' || busy.value) return;
    const at = generation;
    try {
      const next = stateSchema.parse(await http.get('/fixture/state').json());
      if (at === generation && !busy.value) accept(next, initial);
    } catch (cause) { await failure(cause); }
  }
  async function act(action: string, extra: Partial<Write> = {}) {
    if (mode !== 'fixture' || busy.value) return;
    const reconnect = action === 'reconnect' || action === 'scenario';
    if (!reconnect && !ready.value) { error.value = 'Fresh fixture state required'; return; }
    const base = { epoch: state.value?.epoch ?? '', revision: state.value?.revision ?? 0 };
    busy.value = true; error.value = ''; message.value = '';
    const at = generation;
    try {
      const payload = await http.post(`/fixture/${action}`, { json: { ...base, ...extra } }).json();
      if (at !== generation) { message.value = 'Draft changed during request. Preview discarded; reconnect to review applied state.'; return; }
      if (action === 'preview' || action === 'dry-run') { preview.value = previewSchema.parse(payload); message.value = 'Validated fixture preview. No dispatch.'; }
      else {
        const next = stateSchema.parse(payload);
        accept(next, ['apply','revert','restore'].includes(action));
        if (action === 'restore' && next.saved) { pack.value = structuredClone(next.saved.pack); framing.value = structuredClone(next.saved.framing); binding.value = next.saved.binding; }
        if (action === 'cancel') invalidate();
        message.value = ({ apply:'Applied to fixture only.', revert:'Reverted to the previous applied fixture state.', save:'Preset saved locally.', restore:'Saved preset restored explicitly.', reconnect:'Reconnected. Draft preserved; review the applied revision.', cancel:'Fixture rehearsal cancelled; nothing was dispatched.', scenario:'Fixture scenario changed.' }[action] ?? 'Updated.');
      }
    } catch (cause) { await failure(cause); }
    finally { busy.value = false; }
  }
  function select(effect: Effect) { draft.value = structuredClone(effect); error.value = ''; }
  function validateDraft() {
    const parsed = effectSchema.safeParse(draft.value);
    if (!parsed.success) { error.value = 'Invalid effect: values must be integers within their displayed ranges.'; invalidate(); return null; }
    return parsed.data;
  }
  async function previewEffect() { const effect = validateDraft(); if (effect && !blocked.value) await act('preview', { effect }); }
  async function apply() { const effect = validateDraft(); if (effect && preview.value?.effect && sameEffect(effect, preview.value.effect)) await act('apply', { effect }); }
  async function dryRun() {
    const parsed = reactionPackSchema.safeParse(pack.value);
    if (!parsed.success) { error.value = 'Invalid reaction: check ranges, cue IDs and required fields.'; invalidate(); return; }
    await act('dry-run', { pack: parsed.data });
  }
  async function save() {
    if (!state.value) return;
    const parsed = savedSchema.safeParse({ effect: state.value.applied, pack: pack.value, framing: framing.value, binding: binding.value });
    if (!parsed.success) { error.value = 'Preset rejected: check cue fields and unique framing rules (TTL 1–600 ms).'; return; }
    await act('save', { saved: parsed.data });
  }
  onMounted(async () => { await refresh(true); timer = setInterval(() => { void refresh(); }, 2000); });
  onUnmounted(() => { clearInterval(timer); generation += 1; });
  return { mode, state, page, draft, pack, framing, binding, preview, message, error, busy, connected, ready, dirty, blocked, select, act, previewEffect, apply, dryRun, save };
}
