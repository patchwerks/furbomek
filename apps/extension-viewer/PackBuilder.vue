<script setup lang="ts">
import { onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import { compileDraft, draftFromPack, newDraft } from './builder.mjs';
import type { CompiledDraft } from './builder.mjs';
import type { ParsedPack } from '../../packages/extension-preview/index.mjs';
const props = defineProps<{ initialPack: ParsedPack | null }>();
const emit = defineEmits<{ change: [pack: ParsedPack | null] }>();
const draft = ref(props.initialPack ? draftFromPack(props.initialPack) : newDraft());
const error = ref('');
const compiled = shallowRef<CompiledDraft | null>(null);
const urls = new Map<string, ReturnType<typeof setTimeout>>();
watch(draft, () => {
  compiled.value = null;
  error.value = '';
  try { compiled.value = compileDraft(draft.value); }
  catch (reason) { error.value = reason instanceof Error ? reason.message : 'Could not validate draft.'; }
  emit('change', compiled.value?.pack ?? null);
}, { deep: true, immediate: true, flush: 'sync' });
function start(preset: string) { draft.value = newDraft(preset); }
function addCue() {
  if (draft.value.cues.length < 64) draft.value.cues.push({ atMs: '1000', value: 'curious' });
}
function download() {
  if (!compiled.value) return;
  // Export precisely the bytes that passed the shared parser, never the raw draft.
  const url = URL.createObjectURL(new Blob([compiled.value.bytes], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `${compiled.value.pack.packId}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  urls.set(url, setTimeout(() => { URL.revokeObjectURL(url); urls.delete(url); }, 1000));
}
onBeforeUnmount(() => { for (const [url, timer] of urls) { clearTimeout(timer); URL.revokeObjectURL(url); } });
</script>

<template>
  <section class="inspector-section builder" aria-labelledby="builder-title">
    <h2 id="builder-title">Build a presentation pack</h2>
    <p class="helper">Local draft only. Every edit pauses and resets the preview. Start new with a preset, or edit the pack you opened.</p>
    <div class="builder-actions" aria-label="Starter presets">
      <button v-for="preset in ['neutral', 'curious', 'acknowledge']" :key="preset" class="btn btn-outline-secondary" :data-testid="`preset-${preset}`" @click="start(preset)">New {{ preset }}</button>
      <button class="btn btn-outline-secondary" data-testid="edit-current" :disabled="!initialPack" @click="initialPack && (draft = draftFromPack(initialPack))">Restore loaded pack</button>
    </div>
    <div class="builder-fields">
      <div><label class="form-label" for="pack-id">Pack ID</label><input id="pack-id" v-model="draft.packId" class="form-control" data-testid="pack-id" maxlength="64" aria-describedby="pack-id-help builder-error"><p id="pack-id-help" class="helper">Start with a lowercase letter; use letters, numbers and hyphens.</p></div>
      <div><label class="form-label" for="pack-version">Version</label><input id="pack-version" v-model="draft.packVersion" class="form-control" data-testid="pack-version" maxlength="32" aria-describedby="version-help builder-error"><p id="version-help" class="helper">Three numbers, such as 0.1.0.</p></div>
      <div><label class="form-label" for="pack-duration">Duration (ms)</label><input id="pack-duration" v-model="draft.durationMs" class="form-control" data-testid="pack-duration" type="text" inputmode="numeric" maxlength="8" aria-describedby="duration-help builder-error"><p id="duration-help" class="helper">1 to 30000 ms; all cues must occur before the end.</p></div>
    </div>
    <h3 class="cue-heading">Cues <span class="helper">{{ draft.cues.length }} / 64</span></h3>
    <p class="helper">Export orders cues by time and preserves row order for ties. Sequence and capabilities are derived automatically.</p>
    <ol class="cue-list">
      <li v-for="(cue, index) in draft.cues" :key="index" class="cue-row" :data-testid="`cue-${index}`">
        <div><label class="form-label" :for="`cue-time-${index}`">Cue {{ index + 1 }} time (ms)</label><input :id="`cue-time-${index}`" v-model="cue.atMs" class="form-control" type="text" inputmode="numeric" maxlength="8" :disabled="index === 0" aria-describedby="builder-error"></div>
        <div><label class="form-label" :for="`cue-value-${index}`">Cue {{ index + 1 }} value</label><select :id="`cue-value-${index}`" v-model="cue.value" class="form-select" :disabled="index === 0"><option value="neutral">Neutral expression</option><option value="curious">Curious expression</option><option value="acknowledge">Acknowledge reaction</option></select></div>
        <span v-if="index === 0" class="helper">Locked reset</span>
        <button v-else class="btn btn-outline-secondary" :aria-label="`Remove cue ${index + 1}`" @click="draft.cues.splice(index, 1)">Remove</button>
      </li>
    </ol>
    <button class="btn btn-outline-secondary" data-testid="add-cue" :disabled="draft.cues.length >= 64" @click="addCue">Add cue</button>
    <p id="builder-error" class="error-message" role="alert" data-testid="builder-error">{{ error }}</p>
    <p v-if="!error" class="helper" role="status">Valid draft. Ready to preview and export.</p>
    <button class="btn btn-primary" data-testid="export-pack" :disabled="!compiled" @click="download">Export JSON</button>
  </section>
</template>
