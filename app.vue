<template>
  <BNavbar>
    <BNav style="gap: 5px; align-items: center; width: 100%">
      <BButton v-if="!connection" variant="outline-primary" @click="startDeepgram">
        Start mic
      </BButton>
      <BButton v-else variant="outline-primary" @click="stopDeepgramListening">Stop mic</BButton>
      <BButton @click="showSettingsModal">Settings</BButton>
      <BNavForm>
        <BFormSelect
            v-model="assistant"
            class="float-end"
            size="sm"
            :options="assistants"
            @change="handleAssistantChange"
        />
      </BNavForm>
      <BNavForm>
        <BFormSelect v-model="voice" class="float-end" size="sm" :options="voices"/>
      </BNavForm>
      <div style="flex-grow: 1"/>
      <BNavForm>
        <BFormSelect v-model="audioInputDevice" class="float-end" size="sm" :options="audioInputDevices"/>
      </BNavForm>
      <BNavForm>
        <BFormSelect v-model="audioOutputDevice" class="float-end" size="sm" :options="audioOutputDevices"/>
      </BNavForm>
      <div id="bar-container" class="bar"/>
    </BNav>
  </BNavbar>
  <BContainer class="chat-container">
    <BContainer>
      <div ref="chatEl" class="chat p-2">
        <template v-for="message in messages" :key="message.text">
          <div class="clearfix"/>
          <div v-if="message.type === 'user'" class="p-2 float-start">
            <BBadge variant="secondary">
              {{ message.userIndex !== null ? `USER ${message.userIndex}` : '' }}: {{ message.text }}
            </BBadge>
          </div>
          <div v-else class="p-2 float-end" style="display: flex; justify-content: flex-end">
            <BBadge variant="primary">
              {{ botName }}: {{ message.text }}
              (
              stt:{{ message.sttTime }},
              oai:{{ message.assistantTime }},
              tts:{{ message.ttsTime }}
              )
            </BBadge>
          </div>
        </template>
        <div v-if="phrase || phraseEnd" class="p-2 float-start">
          <BBadge variant="secondary">{{ phrase + phraseEnd }} ...</BBadge>
        </div>
        <div class="clearfix"/>
        <div v-if="latestAssistantMessage" class="p-2 float-end">
          <BBadge variant="primary">{{ latestAssistantMessage }} ...</BBadge>
        </div>
        <div class="clearfix"/>
      </div>
      <div>
        <div class="input-wrapper">
          <BButton
              :variant="isBotInput ? 'primary' : 'secondary'"
              class="toggle-button input-badge"
              @click="toggleInputMode"
          >
            {{ isBotInput ? botName : 'USER' }}:
          </BButton>
          <BFormInput
              ref="inputField"
              v-model="input"
              placeholder="Write your message here..."
              class="input-field"
              @keyup.enter="handleInput"
          />
          <BButton :disabled="!input || ((isBotInput && !voice) || (!isBotInput && !assistant))" @click="handleInput">
            Send
          </BButton>
        </div>
      </div>
    </BContainer>
  </BContainer>
  <BModal id="settings-modal" v-model="settingsModalVisible" no-close-on-backdrop size="xl">
    <template #title><h4>Settings</h4></template>
    <SettingsComponent v-model="settings"/>
  </BModal>
  <BModal id="warning-modal" v-model="warningModalVisible" no-close-on-backdrop title="Out of credits">
    <p>PlayHT API is out of credits. Please upgrade your plan or use another account.</p>
  </BModal>
</template>

<script setup lang="ts">
import {mergeDeep} from "@unocss/core";
import {defaultSettings, type Settings} from "~/src/settings";
import SettingsComponent from "~/src/settings.vue";
import type {TTSInterface, TTSStreamInterface} from "~/src/tts/interfaces";
import type {AbstractChat, ChatDeltaEvent, ChatMessageEvent} from "~/src/chat/abstractChat";
import {OpenAIAssistantChat} from "~/src/chat/openai-assistant";
import {ElevenLabsTTS} from "~/src/tts/elevenlabs";
import {PlayHtTTS} from "~/src/tts/playht";
import type {Message} from "~/src/types/message.interface";
import type {AudioDeviceSelectInterface} from "~/src/types/audio-device-select.interface";

(window as unknown as {process: {versions: {node: null}}}).process = {versions: {node: null}};

const {
  createClient,
  LiveTranscriptionEvents,
  LiveClient,
  DeepgramClient
} = await import("@deepgram/sdk");

class DeepgramClientType extends DeepgramClient {
}

class LiveClientType extends LiveClient {
}

let deepgram: DeepgramClientType | undefined;

onMounted(() => {
  try {
    deepgram = createClient(settings.value.deepgram.key, {
      global: {
        url: settings.value.deepgram.url || 'https://api.deepgram.com'
      }
    });
  } catch (e) {
    console.log('ERROR:', e)
  }
});

let firstAudio;
let textAdded;
let openAiResponse;
let ttsStream: TTSStreamInterface | undefined;
let deepgramStart;
let deepgramLast;
let audioStream: MediaStream;

const {audioInputDevices, audioInputDevice, audioOutputDevices, audioOutputDevice} = useDevices()
const {settings, settingsHaveChanged} = useSettings();
const {
  assistants,
  assistant,
  latestAssistantMessage,
  handleAssistantChange,
  initOpenAiQuery
} = useAssistants(settings);
const {
  voice,
  voices,
  ttss,
  initTTS
} = useTextToSpeech()
const {
  input,
  isBotInput,
  chat,
  chatEl,
  handleInput,
  toggleInputMode
} = useChatHandlers(settings, ttss, assistant, voice);
const {messages, addUserText, addBotText, addText, botName} = useMessages(
    settings,
    assistant,
    ttss,
    initTTS
);
const {
  phrase,
  phraseEnd,
  connection,
  startDeepgram,
  stopDeepgramListening
} = useDeepgram(
    settings
);

const settingsModalVisible = ref(false)
const warningModalVisible = ref(false)
const showSettingsModal = () => { settingsModalVisible.value = true }
const showWarningModal = () => { warningModalVisible.value = true }

function useDevices() {
  const audioInputDevices = ref<AudioDeviceSelectInterface[]>([{
    value: "",
    text: "Please select an audio input",
    disabled: true
  }]);
  const audioInputDevice = ref<MediaDeviceInfo | ''>('');
  const audioOutputDevices = ref<AudioDeviceSelectInterface[]>([{
    value: "",
    text: "Please select an audio output",
    disabled: true
  }]);
  const audioOutputDevice = ref<MediaDeviceInfo | ''>('');

  onMounted(() => {
    try {
      navigator.mediaDevices.getUserMedia({
        audio: audioInputDevice.value ? {deviceId: {exact: audioInputDevice.value.deviceId}} : true,
        video: false
      }).then((stream) => {
        audioStream = stream;
        useAudioVisualizer(audioStream);

        navigator.mediaDevices.enumerateDevices().then((devices) => {
          return devices.filter(({kind}) => kind === 'audioinput' || kind === 'audiooutput');
        }).then((audioDevices) => {
          const defaultInput = audioDevices.find(({kind, label}) => kind === 'audioinput' && label === 'Default');
          const defaultOutput = audioDevices.find(({kind, label}) => kind === 'audiooutput' && label === 'Default');

          if (defaultInput) {
            audioInputDevices.value.push({value: defaultInput, text: defaultInput.label});
          }

          if (defaultOutput) {
            audioOutputDevices.value.push({value: defaultOutput, text: defaultOutput.label});
          }

          for (const audioDevice of audioDevices) {
            if (audioDevice.deviceId !== 'default') {
              if (audioDevice.kind === 'audioinput') {
                audioInputDevices.value.push({value: audioDevice, text: audioDevice.label})
              } else {
                audioOutputDevices.value.push({value: audioDevice, text: audioDevice.label})
              }
            }
          }
        })
      })
    } catch (e) {
      console.log("ERROR:", e)
    }
  });

  watch(audioInputDevice, async () => {
    audioStream = await navigator.mediaDevices.getUserMedia({
      audio: audioInputDevice.value ? {deviceId: {exact: audioInputDevice.value.deviceId}} : true,
      video: false
    });

    if (connection.value) {
      stopDeepgramListening();
      await startDeepgram();
    }

    await useAudioVisualizer(audioStream)
  })

  watch(audioOutputDevice, () => {
    if (ttsStream && audioOutputDevice.value) {
      ttsStream.changeSinkId(audioOutputDevice.value.deviceId)
    }
  })

  return {
    audioInputDevices,
    audioInputDevice,
    audioOutputDevices,
    audioOutputDevice
  }
}

async function useAudioVisualizer(stream) {
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  const analyzer = context.createAnalyser();
  source.connect(analyzer);
  analyzer.fftSize = 256;
  const bufferLength = analyzer.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  const barContainer = document.getElementById('bar-container');
  const barsNumber = 40;

  const prevBars = document.querySelectorAll(`.indicator`);
  prevBars.forEach(element => element.remove());

  function getPeakLevel() {
    analyzer.getByteFrequencyData(dataArray);
    return dataArray.slice(0, barsNumber);
  }

  function createBars() {
    for (let i = 0; i < barsNumber; i++) {
      const bar = document.createElement('div');
      bar.className = 'indicator';
      barContainer.appendChild(bar);
    }
  }

  function updateBars(volumeLevels) {
    const bars = document.getElementsByClassName('indicator') as HTMLCollectionOf<HTMLElement>;
    for (let i = 0; i < bars.length; i++) {
      bars[i].style.height = `${30 * volumeLevels[i] / 100}%`;
    }
  }

  function tick() {
    const peakLevels = getPeakLevel();
    updateBars(peakLevels);
    requestAnimationFrame(tick);
  }

  createBars();
  tick();
}

function useSettings() {
  const settings = ref<Settings>(
      mergeDeep(defaultSettings, JSON.parse(localStorage.getItem("settings") || "{}") || {})
  );

  watch(
      settings,
      (settings) => {
        localStorage.setItem("settings", JSON.stringify(settings));
      },
      {deep: true}
  );


  function settingsHaveChanged(newSettings, oldSettings, key) {
    if (!oldSettings || !oldSettings[key]) return true;
    for (const subKey in newSettings[key]) {
      if (newSettings[key][subKey] !== oldSettings[key][subKey]) {
        return true;
      }
    }
    return false;
  }

  return {settings, settingsHaveChanged};
}

type SelectEntry<T> = {value: T | ""; text: string; disabled: boolean} | {
  label: string;
  options: {value: T; text: string; disabled: boolean}[];
};

function useTextToSpeech() {
  const voices = ref<SelectEntry<{tts: string; voice: string}>[]>([
    {value: "", text: "Please select a voice", disabled: true},
  ]);
  const voice = ref<{ tts: string; voice: string } | "">("");
  const ttss = ref<Record<string, TTSInterface>>({});

  watch(
      settings,
      (settings: Settings, prevSettings: Settings) => {
        if (settingsHaveChanged(settings, prevSettings, "elevenlabs")) {
          ttss.value['elevenlabs'] = new ElevenLabsTTS(settings);

          if (settings?.elevenlabs?.key !== prevSettings?.elevenlabs?.key) {
            updateSubscriptionsInfo(ttss.value.elevenlabs);
          }
        }

        if (settingsHaveChanged(settings, prevSettings, "playht")) {
          ttss.value['playht'] = new PlayHtTTS(settings);
        }

        if (settingsHaveChanged(settings, prevSettings, "elevenlabs") || settingsHaveChanged(settings, prevSettings, "playht")) {
          updateVoices(ttss, voices);
        }
      },
      {deep: true, immediate: true}
  );

  async function updateVoices(ttss, voices) {
    Promise.allSettled(
        Object.entries(ttss.value).map(async ([name, tts]: [string, TTSInterface]) => ({
          name,
          voices: await tts.getVoices(),
        }))
    ).then((list) => {
      const _list = list
          .filter(({status}) => status === "fulfilled")
          .map((result: PromiseFulfilledResult<{ name: string; voices: Record<string, string> }>) => result.value)
      voices.value = [
        {value: "", text: "Please select a voice", disabled: true},
        ..._list.map(({name, voices}) => ({
          label: name,
          options: Object.entries(voices).map(([value, text]) => ({
            value: {
              tts: name,
              voice: value,
            },
            text,
            disabled: false,
          })),
        })),
      ];
    });
  }

  async function updateSubscriptionsInfo(tts: TTSInterface) {
    const {tier, character_count, character_limit} = await tts.getSubscription();

    settings.value.elevenlabs.characters = `${character_count}/${character_limit}`;
    settings.value.elevenlabs.tier = tier;
  }

  async function initTTS(audioOutputId?: string) {
    firstAudio = Date.now();
    textAdded = Date.now();
    openAiResponse = 0;
    latestAssistantMessage.value = '';
    ttsStream?.close();

    if (voice.value) {
      const tts = ttss.value[voice.value.tts]
      ttsStream = tts.stream(voice.value.voice, audioOutputId);

      ttsStream?.addEventListener("first", () => {
        if (!firstAudio || firstAudio === openAiResponse) {
          firstAudio = Date.now();
          if (!latestAssistantMessage.value) {
            messages.value[messages.value.length - 1].ttsTime = firstAudio - openAiResponse;
          }
        }
      });

      ttsStream?.addEventListener('last', async () => {
        if (voice.value && voice.value.tts === 'elevenlabs') {
          await updateSubscriptionsInfo(tts);
        }
      })

      ttsStream?.addEventListener('outOfCredits', async () => {
        showWarningModal()
      })
    }
  }

  return {voice, voices, ttss, initTTS}
}

function useAssistants(settings) {
  const assistImpl = ref<Record<string, OpenAIAssistantChat>>({});
  const assistant = ref<{ id: string, assistant: string } | string>("");
  const assistants = ref<SelectEntry<{id: string; assistant: string}>[]>([{value: "", text: "Please select an assistant", disabled: true}]);
  const prevDelta = ref("");
  const latestAssistantMessage = ref('');

  watch(
      settings,
      (settings: Settings, prevSettings: Settings) => {
        if (settingsHaveChanged(settings, prevSettings, "openai")) {
          assistImpl.value = {
            openai: new OpenAIAssistantChat(settings),
          };
          handleAssistantChange();
          updateAssistants(assistImpl, assistants);
        }
      },
      {deep: true, immediate: true}
  );

  function updateAssistants(assistImpl, assistants) {
    Promise.allSettled(
        Object.entries(assistImpl.value).map(async ([name, assistant]: [string, OpenAIAssistantChat]) => ({
          name,
          assistants: await assistant.getAssistants(),
        }))
    ).then((list) => {
      const _list = list
          .filter(({status}) => status === "fulfilled")
          .map((result: PromiseFulfilledResult<{ name: string; assistants: Record<string, string> }>) => result.value);
      assistants.value = [
        {value: "", text: "Please select an assistant", disabled: true},
        ..._list.map(({name, assistants}) => ({
          label: name,
          options: Object.entries(assistants).map(([id, text]) => ({
            value: {
              assistant: name,
              id,
            },
            text,
            disabled: false,
          })),
        })),
      ];
    });
  }

  function handleAssistantChange() {
    if (!assistant.value || typeof assistant.value === 'string') return;

    messages.value = [];
    chat.value?.stop();
    chat.value = null;

    deepgramStart = Date.now();
    deepgramLast = Date.now();
    initTTS(typeof audioOutputDevice.value !== 'string' ? audioOutputDevice.value.deviceId : undefined);

    const _chat = assistImpl.value[assistant.value.assistant];
    chat.value = _chat;
    _chat.on("created", () => {
      openAiResponse = Date.now();
    });

    _chat.on("message", (event: ChatMessageEvent) => {
      handleMessage(event);
    });

    _chat.on("delta", (event: ChatDeltaEvent) => {
      handleDelta(event);
    });

    _chat.start(assistant.value.id);
  }

  function initOpenAiQuery(query: string) {
    console.log('init openai query')
    initTTS(audioOutputDevice.value ? audioOutputDevice.value.deviceId : undefined);
    chat.value?.send(query);
  }

  function handleMessage(event: ChatMessageEvent) {
    latestAssistantMessage.value = "";
    messages.value.push({
      type: "assistant",
      text: event.message.replace(/[#*]/g, ''),
      sttTime: textAdded - deepgramLast,
      assistantTime: openAiResponse - textAdded,
      ttsTime: firstAudio - openAiResponse,
    });
    deepgramStart = 0;
    console.log("textDone > ", Date.now() - textAdded, event.message);
    ttsStream?.end(prevDelta.value);
    prevDelta.value = "";
    nextTick(() => {
      chatEl.value?.scrollTo(0, chatEl.value?.scrollHeight);
    });
  }

  function handleDelta(event: ChatDeltaEvent) {
    console.log("HANDLE DELTA EVENT", event)

    if (!openAiResponse) {
      firstAudio = Date.now();
      openAiResponse = Date.now();
    }
    latestAssistantMessage.value = (latestAssistantMessage.value + event.message.replace(/[#*]/g, '')).trim();
    if (!event.message.startsWith(" ")) {
      prevDelta.value += event.message.replace(/[#*]/g, '');
      return;
    }

    ttsStream?.send(prevDelta.value);
    prevDelta.value = event.message.trim();
    nextTick(() => {
      chatEl.value?.scrollTo(0, chatEl.value?.scrollHeight);
    });
  }

  return {
    assistImpl,
    assistants,
    assistant,
    latestAssistantMessage,
    handleAssistantChange,
    initOpenAiQuery,
  };
}

function useChatHandlers(settings, ttss, assistant, voice) {
  const input = ref("");
  const isBotInput = ref(true);
  const chat = ref<AbstractChat | null>(null);
  const chatEl = ref<HTMLDivElement | null>(null);

  function handleInput() {
    const text = input.value;

    if (assistant.value && text) {
      input.value = "";

      if (!isBotInput.value) {
        addUserText("chat", text);
      }
    }

    if (text && isBotInput.value && voice.value) {
      input.value = "";
      addBotText(text);
    }
  }

  function toggleInputMode() {
    isBotInput.value = !isBotInput.value;
  }

  return {
    input,
    isBotInput,
    chat,
    chatEl,
    handleInput,
    toggleInputMode,
  };
}

function useMessages(settings, assistant, ttss, initTTS) {
  const messages = ref<Message[]>([
    {type: "user", text: "Hello!", userIndex: 0},
    {type: "user", text: "Hello, bro!", userIndex: 1},
    {type: "assistant", text: "Hello, how can I help you?"},
  ] as Message[]);

  function addUserText(index: number | string, text: string) {
    deepgramStart = Date.now();
    deepgramLast = Date.now();
    initOpenAiQuery(text);
    addText(index, text);
  }

  function addBotText(text: string) {
    messages.value.push({type: "assistant", text});
    initTTS(audioOutputDevice.value ? audioOutputDevice.value.deviceId : undefined);

    if (voice.value) {
      if (voice.value.tts === "elevenlabs") {
        ttsStream?.addEventListener("connection is opened", () => {
          ttsStream?.end(text);
        });
      } else {
        ttsStream?.send(text, true);
      }
    }
  }

  function addText(index: number | string | null, text: string) {
    messages.value.push({userIndex: index, type: 'user', text} as Message);
    chatEl.value?.scrollTo(0, chatEl.value?.scrollHeight);
  }

  return {
    messages,
    addUserText,
    addBotText,
    addText,
    botName: "BIPCI"
  };
}

function useDeepgram(settings) {
  const phrase = ref("");
  const phraseEnd = ref("");
  const utteranceChatLogs = ref([]);
  const connection = ref<LiveClientType | null>(null);
  let mediaRecorder: MediaRecorder | null = null;

  async function startDeepgram() {
    await startDeepgramListening();
  }

  async function startDeepgramListening() {
    if (!deepgram) {
      return;
    }

    const deepGramEndpoint = `v1/listen?` +
        `diarize=${settings.value.deepgram.diarization}&` +
        `punctuate=${settings.value.deepgram.punctuation}&` +
        `${settings.value.deepgram.keywords.map((keyword) => `keywords=${keyword}`).join("&")}&` +
        `${settings.value.deepgram.replace_words.map((similarWord) => `replace=${similarWord}`).join("&")}`;

    const _connection = deepgram.listen.live({
      channels: 1,
      encoding: "linear16",
      model: "nova-2-meeting",
      language: "en-US",
      smart_format: true,
      interim_results: true,
      vad_events: true,
      endpointing: settings.value.deepgram.endpointing,
      ...(settings.value.deepgram.utterance && {
        utterance_end_ms: settings.value.deepgram.utterance,
      }),
    }, deepGramEndpoint);
    connection.value = _connection;

    _connection.on(LiveTranscriptionEvents.Open, async () => {
      const interval = setInterval(() => {
        _connection.keepAlive();
        console.log("keepAlive");
      }, 3000);

      _connection.on(LiveTranscriptionEvents.Close, () => {
        clearInterval(interval);
        utteranceChatLogs.value = [];

        console.log("Connection closed.");
      });

      _connection.on(LiveTranscriptionEvents.Transcript, (data) => {
        handleTranscript(data);
      });

      _connection.on(LiveTranscriptionEvents.SpeechStarted, (data) => {
        console.log("Speech started", data)
      });

      _connection.on(LiveTranscriptionEvents.UtteranceEnd, () => {
        handleUtteranceEnd();
      });

      _connection.on(LiveTranscriptionEvents.Metadata, (data) => {
        console.log("Metadata", data);
      });

      _connection.on(LiveTranscriptionEvents.Error, (err) => {
        utteranceChatLogs.value = [];

        console.error("Error", err);
      });

      mediaRecorder = new MediaRecorder(audioStream);

      const dataAvailable = (event: BlobEvent) => {
        if (event.data.size > 0 && connection.value) {
          connection.value.send(event.data);
        }
      }

      mediaRecorder.addEventListener("dataavailable", dataAvailable);
      mediaRecorder.start(100);
      mediaRecorder.addEventListener("error", (err) => {
        console.error("Error", err);
      });
    });
  }

  function dataAvailable(event: BlobEvent) {
    if (event.data.size > 0 && connection.value) {
      connection.value.send(event.data);
    }
  }

  function handleUtteranceEnd() {
    if (settings.value.deepgram.diarization) {
      utteranceChatLogs.value.forEach((chatLog) => {
        addText(chatLog.speaker, chatLog.words);
      });
    } else {
      addText(null, phrase.value);
    }

    initOpenAiQuery(phrase.value);

    phrase.value = "";
    phraseEnd.value = "";
    utteranceChatLogs.value = [];
  }

  function handleTranscript(data) {
    if (!deepgramStart && data.channel.alternatives[0].transcript) {
      deepgramStart = Date.now();
    }

    if (data.is_final && data.channel.alternatives[0].transcript) {
      if (ttsStream) {
        ttsStream?.stopAudio();
      }

      console.log("data.is_final", data.channel.alternatives[0].words);

      if (settings.value.deepgram.diarization) {
        let speaker;
        let chatLog;

        for (const word of data.channel.alternatives[0].words) {
          if (word.speaker === utteranceChatLogs.value[utteranceChatLogs.value.length - 1]?.speaker) {
            utteranceChatLogs.value[utteranceChatLogs.value.length - 1].words += ` ${word.punctuated_word}`;
          } else if (speaker !== word.speaker) {
            speaker = word.speaker;
            chatLog = {speaker, words: word.punctuated_word};

            utteranceChatLogs.value.push(chatLog);
          } else {
            chatLog.words += ` ${word.punctuated_word}`;
          }
        }
      }

      phrase.value = (phrase.value + " " + data.channel.alternatives[0].transcript).trim();
      phraseEnd.value = "";

      chat.value?.preSend(phrase.value);
      if (!settings.value.deepgram.utterance) {
        if (settings.value.deepgram.diarization) {
          utteranceChatLogs.value.forEach((chatLog) => {
            addText(chatLog.speaker, chatLog.words);
          });
        } else {
          addText(null, phrase.value);
        }

        initOpenAiQuery(phrase.value);

        phrase.value = "";
        phraseEnd.value = "";

        utteranceChatLogs.value = [];
      }
    } else {
      phraseEnd.value = data.channel.alternatives[0].transcript;
      if (data.channel.alternatives[0].transcript) deepgramLast = Date.now();
    }
  }

  function stopDeepgramListening() {
    if (mediaRecorder) {
      mediaRecorder?.stop()
      mediaRecorder?.removeEventListener('dataavailable', dataAvailable);
    }

    connection.value?.finish();
    connection.value = null;
  }

  return {
    phrase,
    phraseEnd,
    connection,
    mediaRecorder,
    startDeepgram,
    stopDeepgramListening
  };
}
</script>
<style>
.chat {
  height: calc(100vh - 254px);
  overflow-y: scroll;
}

.badge {
  text-wrap: wrap;
  text-align: left;
  max-width: 95%;
}

.input-wrapper {
  display: flex;
  align-items: center;
  position: relative;
}

.input-badge {
  position: absolute;
  z-index: 1;
}

.input-field {
  padding-left: 70px;
}

.bar {
  height: 30px;
  width: 200px;
  position: relative;
  background-color: lightgray;
  display: flex;
  align-items: flex-end;
  gap: 1px;
  border: blue 1px solid
}

.indicator {
  width: 5px;
  background: blue;
}

.chat-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 54px);
}

</style>
