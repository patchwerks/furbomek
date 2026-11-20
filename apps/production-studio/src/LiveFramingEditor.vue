<script setup lang="ts">
import { computed, ref, toRaw, watch } from 'vue';
import { framingPresetSchema, manualSchema } from './liveGenerated.ts';
import type { FramingPreset, Manual } from './liveGenerated.ts';
import { framingIssue } from './liveEditorValidation.ts';
const props = withDefaults(defineProps<{ modelValue: FramingPreset; disabled: boolean; canApply?: boolean; unavailableReason?: string; currentReason?: string }>(), { disabled: true, canApply: false });
const emit = defineEmits<{ 'update:modelValue': [value: FramingPreset]; preview: []; apply: []; save: []; manual: [value: Manual] }>();
const draft = ref(structuredClone(toRaw(props.modelValue)));
const blocked = computed(() => props.disabled || Boolean(props.unavailableReason));
const issue = computed(() => framingIssue(draft.value));
watch(() => props.modelValue, value => { if (JSON.stringify(value) !== JSON.stringify(draft.value)) draft.value = structuredClone(toRaw(value)); });
watch(draft, () => { if (!blocked.value && !issue.value) emit('update:modelValue', framingPresetSchema.parse(draft.value)); }, { deep: true, flush: 'sync' });
const manual = ref<Manual>({ target: props.modelValue.default, duration_ms: 1000 });
const manualIssue = computed(() => !manualSchema.safeParse(manual.value).success || !draft.value.shots.some(shot => shot.id === manual.value.target) || manual.value.duration_ms > draft.value.ttl_ms);
const subjects = computed(() => draft.value.shots.filter(shot => shot.target.kind !== 'fixed'));
const fixedShots = computed(() => draft.value.shots.filter(shot => shot.target.kind === 'fixed'));
function action(name: 'preview' | 'apply' | 'save') { if (blocked.value || issue.value) return;
  if (name === 'preview') emit('preview'); else if (name === 'apply') { if (props.canApply) emit('apply'); } else emit('save'); }
function hold() { if (!blocked.value && props.canApply && !issue.value && !manualIssue.value) emit('manual', manualSchema.parse(manual.value)); }
function unique(prefix: string, ids: readonly string[]): string { let n = 1; while (ids.includes(`${prefix}-${n}`)) n++; return `${prefix}-${n}`; }
function addShot() {
  if (blocked.value || draft.value.shots.length >= 32) return;
  draft.value.shots.push({ id: unique('shot', draft.value.shots.map(shot => shot.id)), target: { kind: 'fixed', roi: { x: 0, y: 0, width: 1, height: 1 } } });
}
function targetKind(index: number, event: Event) {
  if (blocked.value || !(event.target instanceof HTMLSelectElement)) return;
  const shot = draft.value.shots[index]; if (!shot) return;
  const kind = event.target.value;
  if (kind === 'fixed') shot.target = { kind, roi: { x: 0, y: 0, width: 1, height: 1 } };
  else if (kind === 'person' || kind === 'object') shot.target = { kind, id: shot.id };
}
function setSubject(index: number, event: Event) {
  if (blocked.value || !(event.target instanceof HTMLSelectElement)) return;
  const selected = event.target.value;
  const shot = draft.value.shots.find(item => item.id === selected);
  const rule = draft.value.rules[index];
  if (rule && shot && shot.target.kind !== 'fixed') rule.trigger.subject = { ...shot.target };
}
function subjectShot(rule: FramingPreset['rules'][number]): string {
  return subjects.value.find(shot => shot.target.kind !== 'fixed' && shot.target.id === rule.trigger.subject.id && shot.target.kind === rule.trigger.subject.kind)?.id ?? '';
}
function addRule() {
  const subject = subjects.value[0];
  if (blocked.value || !subject || subject.target.kind === 'fixed' || draft.value.rules.length >= 32) return;
  draft.value.rules.push({ id: unique('rule', draft.value.rules.map(rule => rule.id)), target: subject.id, priority: 50, dwell_ms: 500, release_ms: 1000, trigger: { kind: 'observation', source: draft.value.tracking_source, subject: { ...subject.target }, event: 'attention', confidence: .8, max_age_ms: 1000 } });
}
function move(index: number, direction: number) {
  if (blocked.value) return;
  const next = index + direction; const rules = [...draft.value.rules];
  const rule = rules[index];
  if (rule && next >= 0 && next < rules.length) { rules.splice(index, 1); rules.splice(next, 0, rule); draft.value.rules = rules; }
}
const timing = [
  { key: 'hold_ms', label: 'Hold last shot · ms', min: 0, max: 600000 },
  { key: 'minimum_shot_ms', label: 'Minimum shot · ms', min: 100, max: 600000 },
  { key: 'lock_age_ms', label: 'Tracking freshness · ms', min: 1, max: 600 },
  { key: 'output_ttl_ms', label: 'Output TTL · ms', min: 1, max: 600 },
  { key: 'sample_gap_ms', label: 'Maximum sample gap · ms', min: 1, max: 10000 },
  { key: 'ttl_ms', label: 'Preset TTL · ms', min: 1, max: 600000 },
] as const;
const transitionFields = [
  { key: 'duration_ms', label: 'Transition duration · ms', min: 100, max: 10000, step: 1 },
  { key: 'pan_units_per_second', label: 'Pan rate · units/s', min: .001, max: 1, step: .001 },
  { key: 'zoom', label: 'Framing zoom', min: 1, max: 4, step: .01 },
  { key: 'zoom_per_second', label: 'Zoom rate · units/s', min: .001, max: 1, step: .001 },
] as const;
const roiFields = ['x', 'y', 'width', 'height'] as const;
</script>
<template>
  <section class="live-editor" aria-label="Framing settings">
    <h2>Framing settings</h2>
    <p class="editor-status" role="status">{{ unavailableReason || (disabled ? 'Framing controls held. Waiting for owner availability.' : currentReason || 'Draft ready for owner preview.') }}</p>
    <fieldset :disabled="blocked">
      <legend>Preset and fallback</legend>
      <div class="editor-fields">
        <label>Preset ID<input v-model="draft.id" maxlength="64" required></label>
        <label>Tracking source<input v-model="draft.tracking_source" maxlength="64" required></label>
        <label>Default shot<select v-model="draft.default"><option v-for="shot in draft.shots" :key="shot.id" :value="shot.id">{{ shot.id }}</option></select></label>
        <label>Fixed fallback<select v-model="draft.fallback"><option v-for="shot in fixedShots" :key="shot.id" :value="shot.id">{{ shot.id }}</option></select></label>
      </div>
    </fieldset>
    <fieldset :disabled="blocked">
      <legend>Shots</legend>
      <p class="editor-note">Fixed crops use normalized camera coordinates. Tracked subjects require an exact owner-approved identity.</p>
      <ol class="editor-list">
        <li v-for="(shot, index) in draft.shots" :key="index">
          <h3>Shot {{ index + 1 }}</h3>
          <div class="editor-fields">
            <label>Shot ID<input v-model="shot.id" maxlength="64" required></label>
            <label>Target kind<select :value="shot.target.kind" @change="targetKind(index, $event)"><option value="fixed">Fixed crop</option><option value="person">Person</option><option value="object">Object</option></select></label>
            <label v-if="shot.target.kind !== 'fixed'">Subject ID<input v-model="shot.target.id" maxlength="64" required></label>
            <template v-else><label v-for="key in roiFields" :key="key">Crop {{ key }}<input v-model.number="shot.target.roi[key]" type="number" :min="key === 'x' || key === 'y' ? 0 : .001" max="1" step=".001" required></label></template>
          </div>
          <div class="editor-actions"><button :disabled="draft.shots.length <= 1" :aria-label="`Remove shot ${index + 1}`" @click="draft.shots.splice(index, 1)">Remove shot</button></div>
        </li>
      </ol>
      <div class="editor-actions"><button :disabled="draft.shots.length >= 32" @click="addShot">Add shot</button></div>
    </fieldset>
    <fieldset :disabled="blocked">
      <legend>Automatic rules</legend>
      <p class="editor-note">Higher priority wins. Equal priorities use this order. Detection and events require an approved tracked subject.</p>
      <p v-if="!draft.rules.length">No automatic rules. Add a person or object shot to create one.</p>
      <ol class="editor-list">
        <li v-for="(rule, index) in draft.rules" :key="index">
          <h3>Rule {{ index + 1 }}</h3>
          <div class="editor-fields">
            <label>Rule ID<input v-model="rule.id" maxlength="64" required></label>
            <label>Target shot<select v-model="rule.target"><option v-for="shot in draft.shots" :key="shot.id" :value="shot.id">{{ shot.id }}</option></select></label>
            <label>Trigger<select v-model="rule.trigger.kind"><option value="observation">Detection</option><option value="event">Event</option></select></label>
            <label v-if="rule.trigger.kind === 'event'">Event type<select v-model="rule.trigger.event"><option value="attention">Attention</option><option value="activity">Activity</option><option value="reaction">Reaction</option></select></label>
            <label>Signal source<input v-model="rule.trigger.source" maxlength="64" required></label>
            <label>Trigger subject<select :value="subjectShot(rule)" @change="setSubject(index, $event)"><option value="" disabled>Choose approved subject</option><option v-for="shot in subjects" :key="shot.id" :value="shot.id">{{ shot.id }}</option></select></label>
            <label>Priority · 1–100<input v-model.number="rule.priority" type="number" min="1" max="100" step="1" required></label>
            <label>Confidence · 0–1<input v-model.number="rule.trigger.confidence" type="number" min="0" max="1" step=".01" required></label>
            <label>Signal freshness · ms<input v-model.number="rule.trigger.max_age_ms" type="number" min="1" max="10000" step="1" required></label>
            <label>Dwell · ms<input v-model.number="rule.dwell_ms" type="number" min="0" max="600000" step="1" required></label>
            <label>Release · ms<input v-model.number="rule.release_ms" type="number" min="0" max="600000" step="1" required></label>
          </div>
          <div class="editor-actions"><button :disabled="index === 0" :aria-label="`Move rule ${index + 1} up`" @click="move(index, -1)">Up</button><button :disabled="index === draft.rules.length - 1" :aria-label="`Move rule ${index + 1} down`" @click="move(index, 1)">Down</button><button :aria-label="`Remove rule ${index + 1}`" @click="draft.rules.splice(index, 1)">Remove rule</button></div>
        </li>
      </ol>
      <div class="editor-actions"><button :disabled="!subjects.length || draft.rules.length >= 32" @click="addRule">Add rule</button></div>
    </fieldset>
    <fieldset :disabled="blocked">
      <legend>Tracking and transitions</legend>
      <div class="editor-fields">
        <label>Tracking confidence · 0–1<input v-model.number="draft.lock_confidence" type="number" min="0" max="1" step=".01" required></label>
        <label v-for="field in timing" :key="field.key">{{ field.label }}<input v-model.number="draft[field.key]" type="number" :min="field.min" :max="field.max" step="1" required><small>{{ field.min }} to {{ field.max }}</small></label>
        <label v-for="field in transitionFields" :key="field.key">{{ field.label }}<input v-model.number="draft.transition[field.key]" type="number" :min="field.min" :max="field.max" :step="field.step" required><small>{{ field.min }} to {{ field.max }}</small></label>
      </div>
    </fieldset>
    <p v-if="issue" role="alert">{{ issue }}</p>
    <div class="editor-actions"><button :disabled="blocked || !!issue" @click="action('preview')">Preview framing</button><button class="primary" :disabled="blocked || !!issue || !canApply" @click="action('apply')">Apply framing</button><button :disabled="blocked || !!issue" @click="action('save')">Save framing preset</button></div>
    <fieldset :disabled="blocked">
      <legend>Manual hold</legend>
      <p class="editor-note">Requests use the applied preset. Duration cannot exceed the draft preset TTL; the owner controller verifies the applied limits.</p>
      <div class="editor-fields"><label>Hold shot<select v-model="manual.target"><option v-for="shot in draft.shots" :key="shot.id" :value="shot.id">{{ shot.id }}</option></select></label><label>Hold duration · ms<input v-model.number="manual.duration_ms" type="number" min="1" :max="draft.ttl_ms" step="1" required></label></div>
      <p v-if="manualIssue" role="alert">Choose an existing shot and a duration from 1 to {{ draft.ttl_ms }} ms.</p>
      <div class="editor-actions"><button :disabled="blocked || !canApply || !!issue || manualIssue" @click="hold">Request manual hold</button></div>
    </fieldset>
  </section>
</template>
<style scoped src="./liveEditors.css"></style>
