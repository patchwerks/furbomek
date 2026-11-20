<script setup lang="ts">
import type { Framing } from './model.ts';
const framing = defineModel<Framing>({ required: true });
defineProps<{ disabled: boolean }>();
function move(index: number, step: number) {
  const target = index + step;
  const rule = framing.value.rules[index];
  if (rule && target >= 0 && target < framing.value.rules.length) {
    framing.value.rules.splice(index, 1); framing.value.rules.splice(target, 0, rule);
  }
}
function add() { const rule = (['subject','fixed','hold'] as const).find(r => !framing.value.rules.includes(r)); if (rule) framing.value.rules.push(rule); }
</script>
<template>
  <h2>Saved framing rules</h2>
  <p class="notice">Local draft only. Live framing adapter unavailable. Fixed RGB stays full-frame; these rules do not operate a camera.</p>
  <div class="fields">
    <label>Exact subject anchor<input v-model="framing.subject_id" :disabled="disabled" maxlength="64" pattern="[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}"></label>
    <label>Track TTL · 1–600 ms<input v-model.number="framing.ttl_ms" :disabled="disabled" type="number" min="1" max="600"></label>
  </div>
  <p class="muted">Rules are evaluated in this order. A subject rule requires this stable ID; it never substitutes a surface or another person.</p>
  <ol class="rules">
    <li v-for="(rule, index) in framing.rules" :key="index">
      <label :for="`rule-${index}`">Rule {{ index + 1 }}</label>
      <select :id="`rule-${index}`" v-model="framing.rules[index]" :disabled="disabled"><option value="subject">Subject anchor</option><option value="fixed">Fixed full-frame</option><option value="hold">Hold last crop</option></select>
      <button :disabled="disabled || index === 0" :aria-label="`Move rule ${index + 1} up`" @click="move(index, -1)">Up</button>
      <button :disabled="disabled || index === framing.rules.length - 1" :aria-label="`Move rule ${index + 1} down`" @click="move(index, 1)">Down</button>
      <button :disabled="disabled || framing.rules.length === 1" :aria-label="`Remove rule ${index + 1}`" @click="framing.rules.splice(index, 1)">Remove</button>
    </li>
  </ol>
  <button :disabled="disabled || framing.rules.length >= 3" @click="add">Add fallback rule</button>
</template>
