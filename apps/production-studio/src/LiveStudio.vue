<script setup lang="ts">
import { ref } from 'vue';
import LiveFramingEditor from './LiveFramingEditor.vue';
import LiveVisualEditor from './LiveVisualEditor.vue';
import './liveEditors.css';
import type { Effect } from './generated.ts';
import EffectFields from './EffectFields.vue';
import { useLiveStudio } from './useLiveStudio.ts';
const studio = useLiveStudio();
const { state, result, effect, visual, framing, error, message, busy, connected, authenticated, ready, authorReady, canApplyEffect } = studio;
const token = ref('');
const theme = ref(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
async function login() { const credential = token.value; token.value = ''; await studio.login(credential); }
function chooseEffect(event: Event) {
  if (!(event.target instanceof HTMLSelectElement)) return;
  const choices: readonly Effect[] = [
    { capability: 'graphics.pulse.v1', preset: 'rgb', intensity_percent: 50, duration_ms: 1000 },
    { capability: 'hud.redacted.v1', template: 'neutral', duration_ms: 1000 },
    { capability: 'sfx.preset.v1', preset: 'acknowledge', gain_percent: 30, duration_ms: 1000 },
  ];
  const capability = event.target.value;
  const choice = choices.find(value => value.capability === capability);
  if (choice) effect.value = structuredClone(choice);
}
</script>
<template>
  <div class="app-shell" :data-theme="theme">
    <a class="skip" href="#main">Skip to editor</a>
    <header><div class="brand">Furb-o-Mek <span>Production studio</span></div><button @click="theme = theme === 'dark' ? 'light' : 'dark'">{{ theme === 'dark' ? 'Light' : 'Dark' }} theme</button></header>
    <main id="main">
      <div class="title-row"><h1>Owner effects</h1><span class="status">Live API mode</span></div>
      <p class="scope">Private effect authoring with controller observations and operation receipts.</p>
      <p v-if="state?.origin === 'injected-test-fixture'" class="notice">Injected test fixture controller; renderer, OBS, camera and robot are disconnected.</p>
      <form v-if="!authenticated" class="document" @submit.prevent="login">
        <h2>Local owner session</h2><p>Use the bootstrap credential supplied for this local server. It is sent once in a header and is not saved in browser storage or the URL.</p>
        <label>Local bootstrap credential<input v-model="token" type="password" autocomplete="off" maxlength="128" required :disabled="busy"></label>
        <button :disabled="busy || token.length < 32">Authenticate</button>
      </form>
      <div v-else class="connection"><strong>{{ connected ? state?.health === 'fresh' ? 'Controller connected' : 'Controller held' : 'Disconnected' }}</strong><button :disabled="busy" @click="studio.refresh(true)">Reconnect</button></div>
      <div class="feedback" aria-live="polite"><p v-if="error" class="error" role="alert">{{ error }}</p><p v-else>{{ busy ? 'Awaiting controller receipt…' : message }}</p></div>
      <dl v-if="state" class="provenance"><div><dt>Observed revision</dt><dd data-testid="revision">{{ state.revision }}</dd></div><div><dt>Origin</dt><dd>{{ state.origin }}</dd></div><div><dt>Health</dt><dd>{{ connected ? state.health : 'unconfirmed' }}</dd></div><div><dt>Epoch</dt><dd>{{ state.epoch }}</dd></div></dl>
      <section v-if="authenticated" class="document" aria-label="Owner effect editor">
        <h2>Bounded effect draft</h2><p>Preview checks bounded parameters. Controller responses show observed applied state; optical preview is unavailable.</p>
        <label>Effect capability<select :value="effect.capability" :disabled="!authorReady" @change="chooseEffect"><option value="graphics.pulse.v1">Graphics pulse</option><option value="hud.redacted.v1">Redacted HUD</option><option value="sfx.preset.v1">Curated sound</option></select></label>
        <EffectFields v-model="effect" :disabled="!authorReady" />
        <div class="actions"><button :disabled="!authorReady" @click="studio.effectAction('preview')">Preview effect</button><button :disabled="!canApplyEffect" @click="studio.effectAction('apply')">Apply effect</button><button :disabled="!ready || !state?.previous" @click="studio.simple('revert')">Revert applied</button><button :disabled="!authorReady || !state?.applied" @click="studio.save">Save preset</button><button :disabled="!authorReady" @click="studio.simple('cancel')">Cancel</button></div>
      </section>
      <template v-if="authenticated">
        <LiveVisualEditor v-model="visual" :disabled="!authorReady" :can-apply="ready && !!state?.visual_available" :current-reason="ready && state?.visual_available ? 'Observed controller ready.' : 'HOLD: authoring and preview only; visual apply unavailable.'" @preview="studio.visualAction('visual-preview')" @apply="studio.visualAction('visual-apply')" />
        <LiveFramingEditor v-model="framing" :disabled="!authorReady" :can-apply="ready && !!state?.framing_available" :current-reason="ready && state?.framing_available ? 'Observed controller ready.' : 'HOLD: authoring and preview only; framing apply unavailable.'" @preview="studio.framingAction('framing-preview')" @apply="studio.framingAction('framing-apply')" @save="studio.framingAction('framing-save')" @manual="studio.manual" />
      </template>
      <section v-if="state" class="document"><h2>Observed applied state</h2><p v-if="!connected">Connection lost. The last response below is historical; current application is unconfirmed.</p><pre>{{ JSON.stringify(state.applied, null, 2) }}</pre><h3>Observed visual settings</h3><pre>{{ JSON.stringify(state.visual, null, 2) }}</pre><h3>Observed framing</h3><pre>{{ JSON.stringify(state.framing, null, 2) }}</pre><h3>Controller receipt</h3><pre>{{ JSON.stringify(result ?? state.receipt, null, 2) }}</pre></section>
    </main>
    <footer>Furb-o-Mek · Private owner session · Actual deployment acceptance remains separate</footer>
  </div>
</template>
