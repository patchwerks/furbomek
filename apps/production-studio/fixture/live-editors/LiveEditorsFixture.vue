<script setup lang="ts">
import { ref } from 'vue';
import LiveFramingEditor from '../../src/LiveFramingEditor.vue';
import LiveVisualEditor from '../../src/LiveVisualEditor.vue';
import { createFramingDraft, createVisualDraft } from '../../src/liveDefaults.ts';
import type { Manual } from '../../src/liveGenerated.ts';
const framing = ref(createFramingDraft());
const visual = ref(createVisualDraft());
const held = ref(false);
const dispatchHeld = ref(false);
const dark = ref(false);
const output = ref('No events emitted.');
const count = ref(0);
function record(action: string, value: unknown) { count.value++; output.value = JSON.stringify({ action, value, count: count.value }); }
function manual(value: Manual) { record('manual', value); }
</script>
<template>
  <div class="app-shell" :data-theme="dark ? 'dark' : 'light'">
    <header><span class="brand">Furb-o-Mek</span><button @click="dark = !dark">Toggle theme</button></header>
    <main>
      <h1>Owner editor fixture</h1><p>Synthetic local component test. No controller, camera or live output is connected.</p>
      <button @click="held = !held">{{ held ? 'Release fixture hold' : 'Hold fixture controls' }}</button>
      <button @click="dispatchHeld = !dispatchHeld">{{ dispatchHeld ? 'Release dispatch hold' : 'Hold fixture dispatch' }}</button>
      <details><summary>Last emitted event</summary><output aria-label="Emitted event" style="display:block;overflow-wrap:anywhere">{{ output }}</output></details>
      <LiveVisualEditor v-model="visual" :disabled="held" :can-apply="!held && !dispatchHeld" :unavailable-reason="held ? 'Renderer unavailable in held fixture.' : ''" :current-reason="dispatchHeld ? 'HOLD: renderer unavailable; authoring remains available.' : 'Synthetic renderer available for payload inspection.'" @preview="record('visual-preview', visual)" @apply="record('visual-apply', visual)" />
      <LiveFramingEditor v-model="framing" :disabled="held" :can-apply="!held && !dispatchHeld" :unavailable-reason="held ? 'Tracking unavailable in held fixture.' : ''" :current-reason="dispatchHeld ? 'HOLD: framing dispatch unavailable; authoring remains available.' : 'Synthetic fixed fallback selected.'" @preview="record('framing-preview', framing)" @apply="record('framing-apply', framing)" @save="record('framing-save', framing)" @manual="manual" />
    </main>
  </div>
</template>
