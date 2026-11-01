<template>
  <BTabs>
    <BTab title="OpenAI">
      <BFormGroup label="Key">
        <BFormInput v-model="model.openai.key"/>
      </BFormGroup>
      <BFormGroup label="Assistant instructions" description="Override default assistant instructions">
        <BFormTextarea
            v-model="localAssistantInstructions"
            rows="10"
            @blur="updateAssistantInstructions"
        />
      </BFormGroup>
    </BTab>

    <BTab title="Deepgram">
      <BFormGroup label="Key" label-for="deepgram">
        <BFormInput id="deepgram" v-model="model.deepgram.key"/>
      </BFormGroup>
      <BFormGroup label="Utterance" description="0 - 10000; 0 - disabled">
        <BFormInput v-model.number="model.deepgram.utterance" type="number" step="1"/>
      </BFormGroup>
      <BFormGroup label="Endpointing" description="10 - 1000">
        <BFormInput v-model.number="model.deepgram.endpointing" type="number" step="1" min="10" max="1000"/>
      </BFormGroup>
      <BFormGroup label="URL" label-for="url">
        <BFormInput id="url" v-model="model.deepgram.url"/>
      </BFormGroup>
      <BFormGroup label="Diarization" label-for="diarization">
        <BFormSelect id="diarization" v-model="model.deepgram.diarization">
          <BFormSelectOption :value="true">True</BFormSelectOption>
          <BFormSelectOption :value="false">False</BFormSelectOption>
        </BFormSelect>
      </BFormGroup>
      <BFormGroup label="Punctuation" label-for="punctuation" type="boolean">
        <BFormSelect id="punctuation" v-model="model.deepgram.punctuation">
          <BFormSelectOption :value="true">True</BFormSelectOption>
          <BFormSelectOption :value="false">False</BFormSelectOption>
        </BFormSelect>
      </BFormGroup>
      <BFormGroup label="Keywords" label-for="keywords">
        <div class="elements-container">
          <div v-for="(keyword, index) in model.deepgram.keywords" :key="index" class="element-container">
            <BInputGroupText variant="primary" class="element-badge">{{ keyword }}</BInputGroupText>
            <BButton variant="danger" class="delete-element-button" @click="removeKeyword(index)">
              ⨯
            </BButton>
          </div>
          <BFormInput
              v-if="isAddingNewKeyword"
              v-model="newKeyword"
              class="add-element-input"
              @keyup.enter="addKeyword"
              @keyup.esc="toggleAddingNewKeyword"
          />
          <BButton v-else variant="primary" @click="toggleAddingNewKeyword">
            Add Keyword
          </BButton>
        </div>
      </BFormGroup>

      <BFormGroup label="Replace words" label-for="replacewords">
        <div class="elements-container">
          <div v-for="(word, index) in model.deepgram.replace_words" :key="index" class="element-container">
            <BInputGroupText variant="primary" class="element-badge">{{ word }}</BInputGroupText>
            <BButton variant="danger" class="delete-element-button" @click="removeReplaceWord(index)">
              ⨯
            </BButton>
          </div>
          <BFormInput
              v-if="isAddingNewReplaceWord"
              v-model="newReplaceWord"
              placeholder="word:replace-word"
              class="add-element-input"
              @keyup.enter="addReplaceWord"
              @keyup.esc="toggleAddingNewReplaceWord"
          />
          <BButton v-else variant="primary" @click="toggleAddingNewReplaceWord">
            Add Replace Word
          </BButton>
        </div>
      </BFormGroup>
      <BFormGroup>
        <template #description>
          <div style="margin-top: 20px">
            Parameters documentation:
            <a href="https://developers.deepgram.com/docs/utterance-end" target="_blank">
              Utterance,
            </a>
            <a href="https://developers.deepgram.com/docs/endpointing" target="_blank">
              Endpointing,
            </a>
            <a href="https://developers.deepgram.com/docs/diarization" target="_blank">
              Diarization,
            </a>
            <a href="https://developers.deepgram.com/docs/punctuation" target="_blank">
              Punctuation,
            </a>
            <a href="https://developers.deepgram.com/docs/keywords" target="_blank">
              Keywords,
            </a>
            <a href="https://developers.deepgram.com/docs/find-and-replace" target="_blank">
              Replace words
            </a>show
          </div>
        </template>
      </BFormGroup>
    </BTab>

    <BTab title="11labs">
      <BFormGroup label="Key">
        <BFormInput v-model="model.elevenlabs.key"/>
      </BFormGroup>
      <BFormGroup label="Stability" description="0 - 1; 0 - not set/default">
        <BFormInput v-model.number="model.elevenlabs.stability" type="number" min="0" max="1" step="0.1"/>
      </BFormGroup>
      <BFormGroup label="Similarity Boost" description="0 - 1; 0 - not set/default">
        <BFormInput v-model.number="model.elevenlabs.similarity_boost" type="number" min="0" max="1" step="0.1"/>
      </BFormGroup>
      <BFormGroup label="Tier">
        <BFormInput v-model="model.elevenlabs.tier" disabled/>
      </BFormGroup>
      <BFormGroup label="Characters used">
        <BFormInput v-model.number="model.elevenlabs.characters" disabled/>
      </BFormGroup>
      <BFormGroup>
        <template #description>
          <div style="margin-top: 20px">
            Parameters documentation:
            <a href="https://elevenlabs.io/docs/speech-synthesis/voice-settings" target="_blank">
              Voice Settings
            </a>
          </div>
        </template>
      </BFormGroup>
    </BTab>

    <BTab title="Play.ht">
      <BFormGroup label="User">
        <BFormInput v-model="model.playht.user"/>
      </BFormGroup>
      <BFormGroup label="Key">
        <BFormInput v-model="model.playht.key"/>
      </BFormGroup>
      <BFormGroup label="Engine">
        <BFormSelect v-model="model.playht.engine" :options="playHtEngines"/>
      </BFormGroup>
      <BFormGroup label="Speed" description="0 - 5; 0 - not set/default">
        <BFormInput v-model.number="model.playht.speed" type="number" min="0" max="5" step="0.1"/>
      </BFormGroup>
      <BFormGroup label="Temperature" description="0 - 2; 0 - not set/default">
        <BFormInput v-model.number="model.playht.temperature" type="number" min="0" max="2" step="0.1"/>
      </BFormGroup>
      <BFormGroup label="Voice guidance" description="1 - 6; 0 - not set/default">
        <BFormInput v-model.number="model.playht.voice_guidance" type="number" min="1" max="6" step="0.1"/>
      </BFormGroup>
      <BFormGroup label="Text guidance" description="0 - 2; 0 - not set/default">
        <BFormInput v-model.number="model.playht.text_guidance" type="number" min="0" max="2" step="0.1"/>
      </BFormGroup>
      <BFormGroup description="">
        <template #description>
          You can find parameters descriptions in the <a href="https://play.ht/playground/" target="_blank">Play.ht
          playground</a>
        </template>
      </BFormGroup>
    </BTab>

  </BTabs>
</template>

<script setup lang="ts">
import {defaultSettings, type Settings} from "~/src/settings.js";
import {mergeDeep} from "@unocss/core";

defineOptions({name: 'ProviderSettings'});

const {modelValue} = defineProps(['modelValue']) as { modelValue: Settings };
const emit = defineEmits(['update:modelValue']);

// Settings are JSON-persisted values. Detach defaults, parent props and emitted
// snapshots so a later edit cannot mutate the parent's previous provider state.
const snapshot = (value: Settings): Settings => JSON.parse(JSON.stringify(value));
const normalized = (value: Settings): Settings => snapshot(mergeDeep(defaultSettings, value));
const serialized = (value: Settings) => JSON.stringify(value, (_key, entry) =>
  entry && typeof entry === 'object' && !Array.isArray(entry)
    ? Object.fromEntries(Object.keys(entry).sort().map(key => [key, entry[key]]))
    : entry);
const model = ref<Settings>(normalized(modelValue));

watch(() => modelValue, (value) => {
  const next = normalized(value);
  if (serialized(next) === serialized(model.value)) {
    // A partial replacement may normalize to the current local value; still
    // complete the parent's missing fields once without replacing local state.
    if (serialized(next) !== serialized(value)) emit('update:modelValue', snapshot(next));
    return;
  }
  model.value = next;
}, {deep: true});

watch(model, (value) => {
  // Compare values, not references: a parent echo must not start another merge.
  if (serialized(value) === serialized(modelValue)) return;
  emit('update:modelValue', snapshot(value));
}, {deep: true});

const playHtEngines = [
  {text: 'PlayHT2.0', value: 'PlayHT2.0'},
  {text: 'PlayHT2.0-turbo', value: 'PlayHT2.0-turbo'},
]

const localAssistantInstructions = ref(model.value.openai.assistantInstructions)
const updateAssistantInstructions = () => {
  model.value.openai.assistantInstructions = localAssistantInstructions.value;
}

const newKeyword = ref('')
const isAddingNewKeyword = ref(false);
const toggleAddingNewKeyword = () => {
  if (!isAddingNewKeyword.value) {
    newKeyword.value = ''
  }

  isAddingNewKeyword.value = !isAddingNewKeyword.value
}
const addKeyword = () => {
  if (!Array.isArray(model.value.deepgram.keywords)) {
    model.value.deepgram.keywords = [];
  }
  model.value.deepgram.keywords.push(newKeyword.value);

  isAddingNewKeyword.value = false;
  newKeyword.value = '';
}
const removeKeyword = (index: number) => {
  model.value.deepgram.keywords.splice(index, 1);
}

const newReplaceWord = ref('')
const isAddingNewReplaceWord = ref(false);
const toggleAddingNewReplaceWord = () => {
  if (!isAddingNewReplaceWord.value) {
    newReplaceWord.value = ''
  }

  isAddingNewReplaceWord.value = !isAddingNewReplaceWord.value
}
const addReplaceWord = () => {
  if (!Array.isArray(model.value.deepgram.replace_words)) {
    model.value.deepgram.replace_words = [];
  }
  model.value.deepgram.replace_words.push(newReplaceWord.value);

  isAddingNewReplaceWord.value = false;
  newReplaceWord.value = '';
}
const removeReplaceWord = (index: number) => {
  model.value.deepgram.replace_words.splice(index, 1);
}

</script>

<style>
.add-element-input {
  display: inline;
  width: 162px;
}

.delete-element-button {
  position: absolute;
  z-index: 1;
}

.elements-container {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.element-container {
  position: relative;
  display: inline-block;
}

.delete-element-button {
  position: absolute;
  top: 10%;
  transform: translateY(-50%);
  right: -5px;
  padding: 0 0 0 1px;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  line-height: 18px;
  text-align: center;
}
</style>
