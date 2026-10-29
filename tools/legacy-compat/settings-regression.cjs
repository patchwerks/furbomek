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
  const {reactive, nextTick, effectScope} = await import('vue');
  const {default: component} = await import(pathToFileURL(path.join(fixtureDir, 'component.mjs')));
  const {defaultSettings} = await import(pathToFileURL(path.join(fixtureDir, 'settings-fixture.mjs')));
  const props = reactive({modelValue: structuredClone(defaultSettings)});
  let emissions = 0;
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
    state.model.value.deepgram.utterance = 900;
    await nextTick();
    assert.equal(props.modelValue.deepgram.utterance, 900);
    assert.equal(emissions, 1);

    props.modelValue = {
      ...structuredClone(defaultSettings),
      deepgram: {...structuredClone(defaultSettings.deepgram), utterance: 1200},
    };
    await nextTick();
    assert.equal(state.model.value.deepgram.utterance, 1200);
    assert.equal(emissions, 2);

    state.model.value.deepgram.utterance = 1500;
    await nextTick();
    assert.equal(props.modelValue.deepgram.utterance, 1500);
    assert.equal(emissions, 3);
    console.log('PASS: compiled Settings setup local edit, external replacement, repeated edit; 3 emissions');
  } finally {
    scope.stop();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => fs.rmSync(fixtureDir, {recursive: true, force: true}));
