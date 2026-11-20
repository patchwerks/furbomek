<script setup lang="ts">
import type { Effect } from './generated.ts';
const effect = defineModel<Effect>({ required: true });
defineProps<{ disabled?: boolean }>();
</script>
<template>
  <fieldset :disabled="disabled" class="fields">
    <legend class="sr-only">Effect parameters</legend>
    <label v-if="effect.capability === 'graphics.pulse.v1'">Look
      <select v-model="effect.preset"><option>neutral</option><option>liquidation</option><option>rgb</option><option>xyz</option></select>
    </label>
    <label v-if="effect.capability === 'hud.redacted.v1'">Text template
      <select v-model="effect.template"><option>liquidation</option><option>neutral</option></select>
    </label>
    <label v-if="effect.capability === 'sfx.preset.v1'">Sound preset
      <select v-model="effect.preset"><option>liquidation</option><option>acknowledge</option></select>
    </label>
    <label v-if="effect.capability === 'graphics.pulse.v1'">Intensity · 0–100%
      <input v-model.number="effect.intensity_percent" type="number" min="0" max="100" step="1">
    </label>
    <label v-if="effect.capability === 'sfx.preset.v1'">Gain · 0–100%
      <input v-model.number="effect.gain_percent" type="number" min="0" max="100" step="1">
    </label>
    <label>Duration · 1–{{ effect.capability === 'motion.qualified.v1' ? '1000' : '30000' }} ms
      <input v-model.number="effect.duration_ms" type="number" min="1" :max="effect.capability === 'motion.qualified.v1' ? 1000 : 30000" step="1">
    </label>
    <p v-if="effect.capability === 'motion.qualified.v1'">{{ effect.action }} · conditional on operator-present supported-bench qualification.</p>
  </fieldset>
</template>
