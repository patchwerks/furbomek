<script setup lang="ts">
import { computed, ref } from 'vue';
import inventory from '../../../tools/kinect2/effects/inventory.json';
import EffectFields from './EffectFields.vue';
import CueEditor from './CueEditor.vue';
import FramingEditor from './FramingEditor.vue';
import { sameEffect } from './model.ts';
import { useStudio } from './useStudio.ts';
import type { Effect } from './generated.ts';
const studio = useStudio();
const { mode, state, page, draft, pack, framing, binding, preview, message, error, busy, connected, ready, dirty, blocked } = studio;
const theme = ref(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
const category = ref('renderer');
const inventoryOpen = ref(innerWidth > 800);
const selectedInventory = ref('rgb-video');
const entries = computed(() => inventory.entries.filter(e => category.value === 'hardware' ? ['sensor','capture','sdk'].includes(e.origin) : e.origin === category.value));
const entry = computed(() => inventory.entries.find(e => e.id === selectedInventory.value));
const defaults: Effect[] = [
  { capability:'graphics.pulse.v1', preset:'rgb', intensity_percent:50, duration_ms:1000 },
  { capability:'hud.redacted.v1', template:'liquidation', duration_ms:1000 },
  { capability:'sfx.preset.v1', preset:'liquidation', gain_percent:30, duration_ms:1000 },
  { capability:'motion.qualified.v1', action:'active', duration_ms:200, qualification:'operator_present_supported_bench' },
  { capability:'voice.reserved.v1', preset:'reserved', duration_ms:1000 },
  { capability:'face.reserved.v1', preset:'reserved', duration_ms:1000 },
];
function selectCapability(event: Event) {
  if (!(event.target instanceof HTMLSelectElement)) return;
  const id = event.target.value;
  const effect = defaults.find(e => e.capability === id);
  if (effect) studio.select(effect);
}
function selectEntry(id: string) { selectedInventory.value = id; }
const applyReady = computed(() => ready.value && !blocked.value && !!preview.value?.effect && sameEffect(preview.value.effect, draft.value));
</script>
<template>
  <div class="app-shell" :data-theme="theme">
    <a class="skip" href="#main">Skip to editor</a>
    <header>
      <div class="brand">Furb-o-Mek <span>Production studio</span></div>
      <button @click="theme = theme === 'dark' ? 'light' : 'dark'">{{ theme === 'dark' ? 'Light' : 'Dark' }} theme</button>
    </header>
    <main id="main">
      <div class="title-row"><h1>Effects & reactions</h1><span class="status">{{ mode === 'fixture' ? 'Fixture mode' : 'Live API unavailable' }}</span></div>
      <p v-if="mode !== 'fixture'" class="notice">No live adapter is configured. Controls are unavailable. Start the documented loopback fixture server to review synthetic authoring.</p>
      <template v-else>
        <p class="scope">Private synthetic workspace. No camera, OBS, robot, provider or public stream is connected.</p>
        <div class="connection">
          <span><strong>{{ connected ? state?.health === 'fresh' ? 'Fixture connected' : 'Stale state' : state ? 'Disconnected' : 'Connecting…' }}</strong> · {{ state?.origin ?? 'Awaiting fixture' }}</span>
          <button :disabled="busy" @click="studio.act('reconnect')">Reconnect</button>
        </div>
        <dl v-if="state" class="provenance">
          <div><dt>Applied revision</dt><dd data-testid="revision">{{ state.revision }}</dd></div>
          <div><dt>Owner</dt><dd>{{ state.owner }}</dd></div>
          <div><dt>Session</dt><dd>{{ state.epoch.slice(0, 8) }}</dd></div>
          <div><dt>Draft</dt><dd>{{ dirty ? 'Unsaved changes' : 'Matches applied' }}</dd></div>
        </dl>
        <nav aria-label="Studio sections">
          <button :aria-current="page === 'effects' ? 'page' : undefined" @click="page = 'effects'">Effects</button>
          <button :aria-current="page === 'reactions' ? 'page' : undefined" @click="page = 'reactions'">Reactions</button>
          <button :aria-current="page === 'framing' ? 'page' : undefined" @click="page = 'framing'">Framing</button>
        </nav>
        <div class="feedback" aria-live="polite"><p v-if="error" class="error" role="alert">{{ error }}</p><p v-else>{{ busy ? 'Validating local request…' : message || 'Select an effect and preview its bounded parameters.' }}</p></div>
        <div v-if="page === 'effects'" class="workspace">
          <aside>
            <details :open="inventoryOpen">
              <summary>Capability inventory</summary>
              <label>Category<select v-model="category"><option value="hardware">Hardware & capture</option><option value="derived">Derived inference</option><option value="renderer">Renderer</option></select></label>
              <div class="inventory">
                <button v-for="item in entries" :key="item.id" :aria-pressed="selectedInventory === item.id" @click="selectEntry(item.id)"><span>{{ item.label }}</span><small>{{ item.mac.state }} · {{ item.origin }}</small></button>
              </div>
            </details>
          </aside>
          <section class="editor" aria-label="Effect editor">
            <h2>{{ entry?.label ?? 'Effect parameters' }}</h2>
            <p class="muted">{{ entry?.limits }}</p>
            <p class="readiness"><strong>Live unavailable.</strong> {{ entry?.mac.reason }} Implementation inventory does not grant runtime readiness.</p>
            <figure class="preview-frame">
              <div v-if="ready && preview?.effect?.capability === 'graphics.pulse.v1' && preview.effect.preset === 'rgb'" class="rgb-fixture" aria-label="Synthetic fixed RGB preview"><span>R</span><span>G</span><span>B</span></div>
              <div v-else class="preview-empty"><strong>{{ !ready ? 'Preview unavailable' : preview?.effect ? 'Parameters validated' : 'Fixed RGB preview' }}</strong><span>{{ preview?.effect && preview.effect.capability === 'graphics.pulse.v1' && preview.effect.preset !== 'rgb' ? 'Renderer unavailable; no visual output claimed.' : 'Select graphics · rgb, then Preview.' }}</span></div>
              <figcaption>Synthetic RGB test pattern · fixed full-frame · no optical source</figcaption>
            </figure>
            <h3>Fixture effect authoring</h3>
            <label>Effect capability<select :value="draft.capability" :disabled="busy" @change="selectCapability"><option v-for="choice in defaults" :key="choice.capability" :value="choice.capability">{{ choice.capability }}</option></select></label>
            <p v-if="blocked" class="notice">Unavailable · {{ draft.capability === 'motion.qualified.v1' ? 'No qualified operator-present motion authority.' : 'Reserved adapter is not implemented.' }} Preview and apply are blocked.</p>
            <EffectFields v-model="draft" :disabled="busy || blocked || !ready" />
            <div class="actions"><button :disabled="!ready || blocked" @click="studio.previewEffect">Preview</button><button class="primary" :disabled="!applyReady" @click="studio.apply">Apply to fixture</button><button :disabled="!ready || !state?.previous" @click="studio.act('revert')">Revert applied</button></div>
            <details class="applied"><summary>Exact applied state · revision {{ state?.revision ?? 'unavailable' }}</summary><pre>{{ JSON.stringify(state?.applied, null, 2) }}</pre><p>Synthetic receipt. No renderer or actuator acknowledgment.</p></details>
          </section>
        </div>
        <section v-else-if="page === 'reactions'" class="document">
          <div class="fields"><label>Preset ID<input v-model="pack.pack_id" :disabled="busy" maxlength="64"></label><label>Event binding<select v-model="binding" :disabled="busy"><option value="liquidation">Liquidation · synthetic</option><option value="viewer-reaction">Viewer reaction · synthetic</option><option value="unbound">Unbound</option></select></label></div>
          <CueEditor v-model="pack" :disabled="!ready" />
          <div class="actions"><button class="primary" :disabled="!ready" @click="studio.dryRun">Validate dry-run</button><button :disabled="!ready || !preview?.timeline" @click="studio.act('cancel')">Cancel rehearsal</button></div>
          <section v-if="preview?.timeline" aria-label="Dry-run timeline"><h2>Dry-run timeline</h2><p>Planned horizon {{ preview.horizon_ms }} ms · readiness forecast · no dispatch</p><ol class="timeline"><li v-for="row in preview.timeline" :key="row.id"><strong>{{ row.id }} · {{ row.start_ms }}–{{ row.end_ms }} ms</strong><span>{{ row.status === 'would_apply' ? 'Would apply' : row.status === 'skipped' ? 'Skipped' : row.status === 'cancelled' ? 'Cancelled' : 'Would cancel pack' }} · {{ row.reason }}</span></li></ol></section>
        </section>
        <section v-else class="document"><FramingEditor v-model="framing" :disabled="!ready" /></section>
        <section class="save-strip" aria-label="Saved preset"><div><h3>Local preset</h3><p>Save the applied effect, reaction and framing draft together. Restore is always explicit.</p></div><div class="actions"><button :disabled="!ready || dirty" @click="studio.save">Save preset</button><button :disabled="!ready || !state?.saved" @click="studio.act('restore')">Restore saved</button></div></section>
        <details class="scenarios"><summary>Fixture failure scenarios</summary><div class="actions"><button :disabled="busy || !state" @click="studio.act('scenario', { scenario:'stale' })">Simulate stale state</button><button :disabled="busy || !state" @click="studio.act('scenario', { scenario:'disconnect' })">Simulate disconnect</button></div><p>These controls affect this fixture process only. Reconnect restores its synthetic readiness.</p></details>
      </template>
    </main>
    <footer>Furb-o-Mek · Private authoring · Contracts v1 · Live acceptance remains separate</footer>
  </div>
</template>
