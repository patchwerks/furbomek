// Exercise the actual compiled component setup without a DOM, providers or devices.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const ts = require('typescript');
const {parse, compileScript} = require('@vue/compiler-sfc');

const root = path.resolve(__dirname, '../..');
fs.mkdirSync(path.join(root, '.nuxt'), {recursive: true});
const fixtureDir = fs.mkdtempSync(path.join(root, '.nuxt/compat-settings-'));
const options = {compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext}};
const source = fs.readFileSync(path.join(root, 'src/settings.vue'), 'utf8');
const {descriptor} = parse(source);
// Nuxt supplies these auto-imports. Vue's compiler performs the real prop transform.
const compiled = "import {ref, watch} from 'vue';\n" +
  compileScript(descriptor, {id: 'compat-settings'}).content
    .replace('~/src/settings.js', './settings-fixture.mjs');
fs.writeFileSync(path.join(fixtureDir, 'component.mjs'), ts.transpileModule(compiled, options).outputText);
fs.writeFileSync(path.join(fixtureDir, 'settings-fixture.mjs'), ts.transpileModule(
  fs.readFileSync(path.join(root, 'src/settings.ts'), 'utf8'), options,
).outputText);

(async () => {
  const {reactive, nextTick, effectScope, watch} = await import('vue');
  const {default: component} = await import(pathToFileURL(path.join(fixtureDir, 'component.mjs')));
  const {defaultSettings} = await import(pathToFileURL(path.join(fixtureDir, 'settings-fixture.mjs')));
  const props = reactive({modelValue: structuredClone(defaultSettings)});
  let emissions = 0;
  const defaultsBefore = JSON.stringify(defaultSettings);
  const replacements = [];
  const stopParentWatch = watch(() => props.modelValue, (value, previous) => {
    replacements.push({value, previous});
  });
  const scope = effectScope();
  try {
    const state = scope.run(() => component.setup(props, {
      expose() {},
      emit(name, value) {
        assert.equal(name, 'update:modelValue');
        assert(++emissions < 10, 'settings feedback must remain bounded');
        // Reproduce the parent's v-model echo.
        props.modelValue = value;
      },
    }));
    state.model.value.elevenlabs.stability = 0.6;
    await nextTick();
    assert.equal(emissions, 1);
    const firstParent = props.modelValue;
    assert.notEqual(state.model.value, firstParent);
    assert.notEqual(state.model.value.elevenlabs, firstParent.elevenlabs);
    state.model.value.elevenlabs.stability = 0.7;
    assert.equal(firstParent.elevenlabs.stability, 0.6, 'local edit must preserve previous parent state');
    await nextTick();
    assert.equal(emissions, 2);
    assert.notEqual(props.modelValue, firstParent);
    assert.equal(replacements.length, 2, 'each local edit must replace the parent');
    // Same comparison used by app.vue settingsHaveChanged/provider watchers.
    assert.equal(replacements[1].previous.elevenlabs.stability, 0.6);
    assert.equal(replacements[1].value.elevenlabs.stability, 0.7);

    const childBeforeParentEdit = state.model.value;
    props.modelValue.elevenlabs.tier = 'fixture-tier';
    assert.equal(childBeforeParentEdit.elevenlabs.tier, '', 'parent edit must not leak synchronously');
    await nextTick();
    assert.equal(state.model.value.elevenlabs.tier, 'fixture-tier');
    assert.equal(emissions, 2, 'parent deep sync needs no echo');

    props.modelValue = {
      ...structuredClone(defaultSettings),
      deepgram: {...structuredClone(defaultSettings.deepgram), utterance: 1200},
    };
    await nextTick();
    assert.equal(state.model.value.deepgram.utterance, 1200);
    assert.equal(emissions, 2, 'complete external replacement needs no echo');
    // Reordered properties describe the same settings and must not echo.
    props.modelValue = Object.fromEntries(Object.entries(props.modelValue).reverse());
    await nextTick();
    assert.equal(emissions, 2);

    props.modelValue = {deepgram: {utterance: 1300}};
    await nextTick();
    assert.equal(state.model.value.deepgram.utterance, 1300);
    assert.equal(props.modelValue.playht.engine, defaultSettings.playht.engine);
    assert.equal(emissions, 3, 'incomplete external replacement emits normalized defaults once');
    const beforeArrayEdit = props.modelValue;
    state.model.value.deepgram.keywords.push('fixture-keyword');
    assert.deepEqual(beforeArrayEdit.deepgram.keywords, defaultSettings.deepgram.keywords);
    await nextTick();
    assert.equal(emissions, 4);
    assert.equal(JSON.stringify(defaultSettings), defaultsBefore, 'default arrays must remain immutable');
    assert.notEqual(props.modelValue.deepgram.keywords, state.model.value.deepgram.keywords);

    const previousProvider = props.modelValue;
    state.model.value.playht.speed = 1.25;
    await nextTick();
    assert.equal(previousProvider.playht.speed, 1);
    assert.equal(props.modelValue.playht.speed, 1.25);
    assert.equal(emissions, 5);
    props.modelValue = {playht: {speed: 1.25},
      deepgram: {...props.modelValue.deepgram}};
    await nextTick();
    assert.equal(emissions, 6, 'same normalized partial replacement must still complete defaults');
    assert.equal(props.modelValue.elevenlabs.stability, defaultSettings.elevenlabs.stability);
    console.log('PASS: detached defaults/arrays, repeated provider edits, parent deep sync, complete/partial/reordered replacement; 6 emissions');
  } finally {
    scope.stop();
    stopParentWatch();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => fs.rmSync(fixtureDir, {recursive: true, force: true}));
