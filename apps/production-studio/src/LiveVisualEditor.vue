<script setup lang="ts">
import { computed, ref, toRaw, watch } from 'vue';
import { visualSettingsSchema } from './liveGenerated.ts';
import type { VisualSettings } from './liveGenerated.ts';
const props = withDefaults(defineProps<{ modelValue: VisualSettings; disabled: boolean; canApply?: boolean; unavailableReason?: string; currentReason?: string }>(), { disabled: true, canApply: false });
const emit = defineEmits<{ 'update:modelValue': [value: VisualSettings]; preview: []; apply: [] }>();
const draft = ref<VisualSettings>(structuredClone(toRaw(props.modelValue)));
const blocked = computed(() => props.disabled || Boolean(props.unavailableReason));
const validation = computed(() => visualSettingsSchema.safeParse(draft.value));
const issue = computed(() => {
  if (validation.value.success) return '';
  const first = validation.value.error.issues[0];
  return first ? `${first.path.join('.')}: ${first.message}` : 'Check visual values.';
});
watch(() => props.modelValue, value => { if (JSON.stringify(value) !== JSON.stringify(draft.value)) draft.value = structuredClone(toRaw(value)); });
watch(draft, () => { if (!blocked.value && validation.value.success) emit('update:modelValue', validation.value.data); }, { deep: true, flush: 'sync' });
function action(name: 'preview' | 'apply') { if (blocked.value || !validation.value.success) return;
  if (name === 'preview') emit('preview'); else if (props.canApply) emit('apply'); }
const controls = [
  { key: 'point_pixels', label: 'Point size · pixels', min: .75, max: 3.6, step: .01 },
  { key: 'zoom', label: 'View zoom', min: .7, max: 1.5, step: .01 },
  { key: 'yaw', label: 'Yaw · radians', min: -.55, max: .55, step: .01 },
  { key: 'pitch', label: 'Pitch · radians', min: -.32, max: .32, step: .01 },
  { key: 'pulse_hz', label: 'Pulse · Hz', min: 0, max: 1, step: .01 },
  { key: 'intensity_percent', label: 'Intensity · percent', min: 0, max: 100, step: 1 },
] as const;
</script>
<template>
  <section class="live-editor" aria-label="Visual settings">
    <h2>Visual settings</h2>
    <p class="editor-status" role="status">{{ unavailableReason || (disabled ? 'Visual controls held. Waiting for owner availability.' : currentReason || 'Draft ready for owner preview.') }}</p>
    <fieldset :disabled="blocked">
      <legend>Renderer appearance</legend>
      <div class="editor-fields">
        <label>Look<select v-model="draft.look"><option value="rgb.fixed.v1">RGB · fixed</option><option value="rgb.crimson.v1">RGB · crimson</option><option value="xyz.depth.v1">XYZ · depth</option><option value="xyz.crimson.v1">XYZ · crimson</option></select></label>
        <label v-for="control in controls" :key="control.key">{{ control.label }}<input v-model.number="draft[control.key]" type="number" :min="control.min" :max="control.max" :step="control.step" required><small>{{ control.min }} to {{ control.max }}</small></label>
      </div>
      <div class="editor-actions">
        <label class="editor-check"><input v-model="draft.hud_visible" type="checkbox">Show HUD</label>
        <label class="editor-check"><input v-model="draft.insets_visible" type="checkbox">Show insets</label>
      </div>
    </fieldset>
    <p v-if="issue" role="alert">{{ issue }}</p>
    <div class="editor-actions"><button :disabled="blocked || !!issue" @click="action('preview')">Preview visual settings</button><button class="primary" :disabled="blocked || !!issue || !canApply" @click="action('apply')">Apply visual settings</button></div>
  </section>
</template>
<style scoped src="./liveEditors.css"></style>
