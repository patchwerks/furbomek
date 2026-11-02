<script setup>
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
import { MAX_PACK_BYTES, parsePack, samplePack } from '../../packages/extension-preview/index.mjs';
import exampleText from '../../packages/extension-preview/fixtures/reaction.json?raw';
import { createProxy } from './proxy.mjs';

const neutral = Object.freeze({ positionMs: 0, expression: 'neutral', reaction: null, reactionProgress: 0 });
const pack = shallowRef(parsePack(new TextEncoder().encode(exampleText)));
const filename = ref('Bundled reaction example');
const sample = shallowRef(neutral);
const playing = ref(false);
const importing = ref(false);
const importError = ref('');
const rendererError = ref('');
const ready = ref(false);
const reducedMotion = ref(false);
const stage = ref(null);
const canvas = ref(null);
const fileInput = ref(null);
const position = ref(0);
const duration = computed(() => pack.value?.durationMs ?? 0);
let proxy, observer, media;
let frame = 0;
let anchor = 0;
let nonce = 0;
let alive = true;

function draw() { proxy?.render(sample.value, reducedMotion.value); }
function pause() {
  playing.value = false;
  if (frame) cancelAnimationFrame(frame);
  frame = 0;
}
function reset() {
  pause();
  position.value = 0;
  sample.value = neutral;
  draw();
}
function seek(value) {
  pause();
  if (!pack.value) return;
  position.value = Math.max(0, Math.min(Number(value), duration.value));
  sample.value = samplePack(pack.value, position.value);
  draw();
}
function seekInput(event) { seek(event.target.value); }
function tick(now) {
  frame = 0;
  if (!alive || !playing.value || !pack.value || !ready.value) return;
  const next = now - anchor;
  if (next >= duration.value) { reset(); return; }
  position.value = next;
  sample.value = samplePack(pack.value, next);
  draw();
  frame = requestAnimationFrame(tick);
}
function togglePlay() {
  if (playing.value) { pause(); return; }
  if (!ready.value || !pack.value || importing.value || document.hidden) return;
  if (position.value >= duration.value) reset();
  anchor = performance.now() - position.value;
  playing.value = true;
  frame = requestAnimationFrame(tick);
}
function clearPack() {
  reset();
  pack.value = null;
  filename.value = '';
  importError.value = '';
}
async function importFile(event) {
  const token = ++nonce;
  clearPack();
  importing.value = false;
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  importing.value = true;
  try {
    if (file.size > MAX_PACK_BYTES) throw new TypeError('Pack exceeds the 1 MiB limit.');
    const buffer = await file.slice(0, MAX_PACK_BYTES + 1).arrayBuffer();
    if (!alive || token !== nonce) return;
    if (buffer.byteLength > MAX_PACK_BYTES) throw new TypeError('Pack exceeds the 1 MiB limit.');
    const parsed = parsePack(new Uint8Array(buffer));
    pack.value = parsed;
    filename.value = file.name;
  } catch (error) {
    if (alive && token === nonce) importError.value = error instanceof Error ? error.message : 'Could not read this pack.';
  } finally {
    if (alive && token === nonce) importing.value = false;
  }
}
function loadExample() {
  ++nonce;
  clearPack();
  importing.value = false;
  pack.value = parsePack(new TextEncoder().encode(exampleText));
  filename.value = 'Bundled reaction example';
}
function failRenderer(message) {
  ready.value = false;
  reset();
  proxy?.dispose();
  proxy = undefined;
  // Removing the failed canvas avoids presenting its last frame as current state.
  rendererError.value = message;
}
function visibilityChanged() { if (document.hidden) pause(); }
function motionChanged() {
  reducedMotion.value = media.matches;
  draw();
}
onMounted(() => {
  media = window.matchMedia('(prefers-reduced-motion: reduce)');
  motionChanged();
  media.addEventListener('change', motionChanged);
  document.addEventListener('visibilitychange', visibilityChanged);
  try {
    if (!canvas.value.getContext('webgl2')) throw new Error('WebGL2 unavailable');
    proxy = createProxy(canvas.value, () => failRenderer('The WebGL2 context was lost. Reload this page to restore the preview.'));
    observer = new ResizeObserver(() => {
      if (!proxy || !stage.value) return;
      const { width, height } = stage.value.getBoundingClientRect();
      proxy.resize(width, height);
      draw();
    });
    observer.observe(stage.value);
    ready.value = true;
  } catch {
    failRenderer('WebGL2 is unavailable. This browser cannot render the procedural preview.');
  }
});
onBeforeUnmount(() => {
  alive = false;
  ++nonce;
  pause();
  observer?.disconnect();
  media?.removeEventListener('change', motionChanged);
  document.removeEventListener('visibilitychange', visibilityChanged);
  proxy?.dispose();
  proxy = undefined;
});
</script>

<template>
  <main class="viewer-shell">
    <header class="viewer-header">
      <a class="brand" href="#main-stage">Furb-o-Mek</a>
      <h1>Presentation preview</h1>
      <span class="local-label">Local JSON only</span>
    </header>
    <div class="workbench">
      <section id="main-stage" class="preview-column" aria-labelledby="preview-title">
        <div class="section-heading"><h2 id="preview-title">Procedural proxy</h2><span>No physical simulation</span></div>
        <div ref="stage" class="stage">
          <canvas v-if="!rendererError" ref="canvas" data-testid="viewer-canvas" role="img" aria-label="Original gray six-legged procedural character. Static legs; presentation-only head tilt and whole-model acknowledgment." />
          <div v-if="rendererError" class="stage-error" role="alert" data-testid="renderer-error"><h3>Preview unavailable</h3><p>{{ rendererError }}</p></div>
        </div>
        <div class="transport">
          <div class="transport-buttons">
            <button class="btn btn-primary" data-testid="play-pause" :disabled="!ready || !pack || importing" @click="togglePlay">{{ playing ? 'Pause' : 'Play' }}</button>
            <button class="btn btn-outline-secondary" data-testid="reset" :disabled="!pack" @click="reset">Reset</button>
            <span class="playback-state" data-testid="playback-state">{{ playing ? 'playing' : 'paused' }}</span>
            <output class="clock"><span data-testid="position-ms">{{ Math.floor(position) }}</span> / {{ duration }} ms</output>
          </div>
          <label class="form-label" for="timeline">Timeline</label>
          <input id="timeline" class="form-range" type="range" data-testid="timeline" min="0" :max="duration || 1" step="1" :value="position" :disabled="!pack" :aria-valuetext="`${Math.floor(position)} milliseconds`" @input="seekInput">
          <p class="motion-note">{{ reducedMotion ? 'Reduced motion: transforms are disabled; time and event state remain available.' : 'Curious tilts the head. Acknowledge gently pitches and lifts the whole proxy.' }}</p>
        </div>
      </section>
      <aside class="inspector" aria-label="Pack inspector">
        <section class="inspector-section">
          <h2>Preview pack</h2>
          <p class="helper">Load one presentation pack to inspect its expressions and reactions.</p>
          <label class="form-label" for="import-file">Import local JSON <span class="helper">(max 1 MiB)</span></label>
          <input id="import-file" ref="fileInput" class="form-control" type="file" accept=".json,application/json" data-testid="import-file" @change="importFile">
          <button class="btn btn-link example-button" data-testid="load-example" @click="loadExample">Use bundled example</button>
          <p v-if="importing" role="status">Reading local file…</p>
          <p v-if="importError" class="error-message" role="alert" data-testid="import-error">{{ importError }}</p>
          <div v-if="pack" class="pack-details">
            <strong data-testid="pack-name">{{ filename }}</strong>
            <span>{{ pack.packId }} · {{ pack.packVersion }}</span>
            <span>Contract {{ pack.previewContractVersion }} · {{ pack.events.length }} events · {{ duration }} ms</span>
          </div>
          <p v-else-if="!importing" class="helper">No pack loaded. Choose a valid JSON file or the bundled example.</p>
        </section>
        <section class="inspector-section" aria-labelledby="state-title">
          <h2 id="state-title">Sampled state</h2>
          <dl class="state-grid"><dt>Expression</dt><dd data-testid="expression">{{ sample.expression }}</dd><dt>Reaction</dt><dd data-testid="reaction">{{ sample.reaction ?? 'none' }}</dd></dl>
        </section>
        <section class="inspector-section events-section" aria-labelledby="events-title">
          <h2 id="events-title">Events</h2>
          <ol v-if="pack" class="event-list" data-testid="event-list">
            <li v-for="event in pack.events" :key="event.seq"><button @click="seek(event.atMs)" :aria-label="`Seek to ${event.value} at ${event.atMs} milliseconds`"><span class="event-time">{{ event.atMs }} ms</span><span>{{ event.value }}<small>{{ event.kind === 'presentation.expression' ? 'Expression' : 'Reaction' }}</small></span></button></li>
          </ol>
          <p v-else class="helper">Events appear after a valid import.</p>
        </section>
      </aside>
    </div>
    <footer class="viewer-footer">Original six-leg geometry · No gait or physical simulation · No live connections · <a href="./THREE-LICENSE.txt">Three.js MIT notice</a></footer>
  </main>
</template>
