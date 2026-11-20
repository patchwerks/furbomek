import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import ky, { HTTPError } from 'ky';
import { z } from 'zod';
import { ownerStateSchema, ownerResultSchema, ownerActionSchema, visualSettingsSchema } from './liveGenerated.ts';
import type { OwnerState, OwnerAction, OwnerResult, FramingPreset, Manual } from './liveGenerated.ts';
import { createFramingDraft } from './liveDefaults.ts';
import type { Effect } from './generated.ts';

const http = ky.create({ timeout: 12000, retry: 0, credentials: 'same-origin', headers: { 'X-Owner-Request': '1' } });
const sessionSchema = z.object({ csrf: z.string().min(32).max(128) }).strict();
const errorSchema = z.object({ error: z.string().max(100) }).strict();

export function useLiveStudio() {
  const state = ref<OwnerState | null>(null);
  const result = ref<OwnerResult | null>(null);
  const effect = ref<Effect>({ capability: 'graphics.pulse.v1', preset: 'rgb', intensity_percent: 50, duration_ms: 1000 });
  const visual = ref(visualSettingsSchema.parse({}));
  const framing = ref<FramingPreset>(createFramingDraft());
  const error = ref('');
  const message = ref('Authenticate with the local owner bootstrap credential.');
  const busy = ref(false);
  const connected = ref(false);
  const authenticated = ref(false);
  const authorReady = computed(() => authenticated.value && connected.value && !busy.value);
  const ready = computed(() => authorReady.value && state.value?.health === 'fresh');
  const previewed = ref<string | null>(null);
  const canApplyEffect = computed(() => ready.value && !!previewed.value && result.value?.reason === 'previewed' && result.value.preview !== null);
  let csrf = '';
  let generation = 0;
  let timer: ReturnType<typeof setInterval> | undefined;
  const invalidate = () => { generation += 1; previewed.value = null; };
  watch([effect, visual, framing], invalidate, { deep: true, flush: 'sync' });
  function accept(next: OwnerState) {
    if (next.epoch !== state.value?.epoch || next.revision !== state.value?.revision || next.health !== 'fresh') invalidate();
    state.value = next;
    connected.value = true;
  }
  async function failure(cause: unknown) {
    invalidate();
    connected.value = false;
    if (cause instanceof HTTPError) {
      if (cause.response.status === 401) { csrf = ''; authenticated.value = false; }
      let payload: unknown;
      try { payload = await cause.response.json(); }
      catch (invalid) { if (!(invalid instanceof Error)) throw invalid; error.value = 'Invalid server response; reconnect.'; return; }
      const rejection = ownerResultSchema.safeParse(payload);
      if (rejection.success) { accept(rejection.data.state); result.value = rejection.data; error.value = `Rejected: ${rejection.data.reason}`; }
      else { const parsed = errorSchema.safeParse(payload); error.value = parsed.success ? `Rejected: ${parsed.data.error}` : 'Invalid server response; reconnect.'; }
    } else if (cause instanceof Error) error.value = 'Disconnected or invalid response. Applied state is unconfirmed; reconnect.';
    else throw cause;
  }
  async function refresh(reconnect = false) {
    if (!authenticated.value || busy.value) return;
    const at = generation;
    try {
      const next = ownerStateSchema.parse(await http.get('/api/production/status').json());
      if (at === generation && !busy.value) { accept(next); if (reconnect) { error.value = ''; message.value = 'Reconnected. Drafts preserved; review observed state.'; } }
    } catch (cause) { await failure(cause); }
  }
  async function login(token: string) {
    if (busy.value) return;
    busy.value = true; error.value = ''; invalidate();
    try {
      const session = sessionSchema.parse(await http.post('/api/production/session', { json: {}, headers: { Authorization: `Bearer ${token}` } }).json());
      csrf = session.csrf; authenticated.value = true;
      accept(ownerStateSchema.parse(await http.get('/api/production/status').json()));
      message.value = 'Authenticated. Review observed state before applying a draft.';
    } catch (cause) { await failure(cause); }
    finally { busy.value = false; }
  }
  async function act(request: OwnerAction) {
    if (!authorReady.value) { error.value = 'Authenticated controller connection required.'; return; }
    busy.value = true; error.value = ''; result.value = null;
    const at = generation;
    try {
      const validated = ownerActionSchema.parse(request);
      const reply = ownerResultSchema.parse(await http.post('/api/production/action', { json: validated, headers: { 'X-CSRF-Token': csrf } }).json());
      if (at !== generation) { invalidate(); connected.value = false; message.value = 'Draft changed during request. Reconnect to observe the result.'; return; }
      accept(reply.state); result.value = reply;
      if (reply.outcome === 'rejected') { invalidate(); error.value = `Rejected: ${reply.reason}`; return; }
      if (reply.reason === 'previewed') previewed.value = JSON.stringify(request);
      else invalidate();
      message.value = `Controller receipt: ${reply.reason}.`;
    } catch (cause) { await failure(cause); }
    finally { busy.value = false; }
  }
  function parseAction(value: unknown): OwnerAction | null {
    const parsed = ownerActionSchema.safeParse(value);
    if (!parsed.success) { invalidate(); error.value = 'Invalid draft. Check the displayed bounds and required fields.'; return null; }
    return parsed.data;
  }
  function base() { return { epoch: state.value?.epoch ?? '', revision: state.value?.revision ?? 0 }; }
  async function effectAction(action: 'preview' | 'apply') {
    if (action === 'apply' && !ready.value) { error.value = 'Apply held: fresh controller authority required.'; return; }
    const request = parseAction({ ...base(), action, effect: effect.value });
    if (!request) return;
    if (action === 'apply' && previewed.value !== JSON.stringify({ ...request, action: 'preview' })) { error.value = 'Preview this exact draft and revision first.'; return; }
    await act(request);
  }
  async function visualAction(action: 'visual-preview' | 'visual-apply') {
    if (action === 'visual-apply' && (!ready.value || !state.value?.visual_available)) { error.value = 'Visual controls held by controller.'; return; }
    const request = parseAction({ ...base(), action, visual: visual.value, duration_ms: 1000 });
    if (!request) return;
    if (action === 'visual-apply' && previewed.value !== JSON.stringify({ ...request, action: 'visual-preview' })) { error.value = 'Preview this exact visual draft first.'; return; }
    await act(request);
  }
  async function framingAction(action: 'framing-preview' | 'framing-apply' | 'framing-save') {
    if (!framing.value) return;
    if (action === 'framing-apply' && (!ready.value || !state.value?.framing_available)) { error.value = 'Framing controls held by controller.'; return; }
    const request = parseAction({ ...base(), action, framing: framing.value });
    if (!request) return;
    if (action === 'framing-apply' && previewed.value !== JSON.stringify({ ...request, action: 'framing-preview' })) { error.value = 'Preview this exact framing draft first.'; return; }
    await act(request);
  }
  async function manual(value: Manual) { if (!ready.value || !state.value?.framing_available) { error.value = 'Manual framing held: fresh authority required.'; return; } const request = parseAction({ ...base(), action: 'framing-manual', manual: value }); if (request) await act(request); }
  async function simple(action: 'revert' | 'cancel') { if (action === 'revert' && !ready.value) { error.value = 'Revert held: fresh authority required.'; return; } await act({ ...base(), action }); }
  async function save() {
    if (!state.value?.applied) return;
    const request = parseAction({ ...base(), action: 'save', saved: { effect: state.value.applied, framing: framing.value } });
    if (request) await act(request);
  }
  onMounted(() => { timer = setInterval(() => { void refresh(); }, 2000); });
  onUnmounted(() => { clearInterval(timer); csrf = ''; generation += 1; });
  return { state, result, effect, visual, framing, error, message, busy, connected, authenticated, ready, authorReady, previewed, canApplyEffect, login, refresh, effectAction, visualAction, framingAction, manual, simple, save };
}
