<script setup lang="ts">
import type { ReactionPack, Effect } from './generated.ts';
import EffectFields from './EffectFields.vue';
const pack = defineModel<ReactionPack>({ required: true });
defineProps<{ disabled: boolean }>();
const choices = [
  { capability: 'hud.redacted.v1', template: 'liquidation', duration_ms: 1000 },
  { capability: 'graphics.pulse.v1', preset: 'liquidation', intensity_percent: 50, duration_ms: 1000 },
  { capability: 'sfx.preset.v1', preset: 'liquidation', gain_percent: 30, duration_ms: 1000 },
] satisfies Effect[];
function choose(index: number, event: Event) {
  if (!(event.target instanceof HTMLSelectElement)) return;
  const effect = choices.find(e => e.capability === (event.target instanceof HTMLSelectElement ? event.target.value : ''));
  const cue = pack.value.cues[index];
  if (effect && cue) cue.effect = structuredClone(effect);
}
function sequence(index: number, event: Event) {
  if (!(event.target instanceof HTMLSelectElement)) return;
  const cue = pack.value.cues[index];
  if (cue) cue.after = event.target.value ? [event.target.value] : [];
}
function add() {
  const prior = pack.value.cues.at(-1);
  let suffix = 1;
  while (pack.value.cues.some(c => c.id === `cue-${suffix}`)) suffix += 1;
  pack.value.cues.push({ id: `cue-${suffix}`, after: prior ? [prior.id] : [], effect: { capability:'graphics.pulse.v1', preset:'neutral', intensity_percent:50, duration_ms:1000 }, condition:'always', ttl_ms:1000, on_unavailable:'skip', on_fault:'cancel_pack' });
}
function remove(id: string) { pack.value.cues = pack.value.cues.filter(c => c.id !== id); for (const cue of pack.value.cues) cue.after = cue.after.filter(p => p !== id); }
</script>
<template>
  <div class="section-head"><h2>Reaction cues</h2><button :disabled="disabled || pack.cues.length >= 16" @click="add">Add segment</button></div>
  <p class="muted">Completion dependencies define sequence. Independent cues run in parallel; shared resources must be ordered.</p>
  <ol class="cue-list">
    <li v-for="(cue, index) in pack.cues" :key="cue.id">
      <div class="section-head"><h3>{{ index + 1 }}. {{ cue.id }}</h3><button :disabled="disabled || pack.cues.length === 1" :aria-label="`Remove ${cue.id}`" @click="remove(cue.id)">Remove</button></div>
      <p v-if="cue.effect.capability === 'motion.qualified.v1'" class="notice">Unavailable · conditional movement retained from the saved fixture. It is skipped, never submitted.</p>
      <div class="fields">
        <label>Capability
          <select :value="cue.effect.capability" :disabled="disabled || cue.effect.capability === 'motion.qualified.v1'" @change="choose(index, $event)">
            <option v-for="choice in choices" :key="choice.capability">{{ choice.capability }}</option>
            <option disabled value="motion.qualified.v1">motion.qualified.v1 · unavailable</option>
            <option disabled value="voice.reserved.v1">voice.reserved.v1 · unavailable</option>
            <option disabled value="face.reserved.v1">face.reserved.v1 · unavailable</option>
          </select>
        </label>
        <label>Starts after
          <select :value="cue.after[0] ?? ''" :disabled="disabled" @change="sequence(index, $event)">
            <option value="">Parallel group · start</option>
            <option v-for="prior in pack.cues.slice(0, index)" :key="prior.id" :value="prior.id">{{ prior.id }} completes</option>
          </select>
        </label>
        <label>TTL · 1–30000 ms<input v-model.number="cue.ttl_ms" :disabled="disabled" type="number" min="1" max="30000"></label>
        <label>If unavailable<select v-model="cue.on_unavailable" :disabled="disabled"><option value="skip">Skip cue</option><option value="cancel_pack">Cancel pack</option></select></label>
      </div>
      <EffectFields v-model="cue.effect" :disabled="disabled || cue.effect.capability === 'motion.qualified.v1'" />
      <p class="muted">Condition: {{ cue.condition }} · Fault: cancel pack</p>
    </li>
  </ol>
</template>
