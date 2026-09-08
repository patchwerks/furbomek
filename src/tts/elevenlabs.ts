import type {Settings} from "~/src/settings";
import type {TTSInterface, TTSStreamInterface} from "~/src/tts/interfaces";
import type {AudioContextWithSetSinkId} from "~/src/types/audio-context.interface";


const chunk_length_schedule = [120, 160, 250, 290];

export class ElevenLabsTTSStream extends EventTarget implements TTSStreamInterface {
  private ws: WebSocket;
  private nextPlayTime: number = 0;
  private readonly audioContext: AudioContext;

  constructor(private settings: Settings, voice: string, audioOutputId?: string) {
    super();
    this.audioContext = new AudioContext();
    const audioContext = this.audioContext as AudioContextWithSetSinkId
    if (audioOutputId) {
      audioContext.setSinkId(audioOutputId)
    }
    this.ws = new WebSocket(`wss://api.elevenlabs.io/v1/text-to-speech/${voice}/stream-input?model_id=eleven_turbo_v2&output_format=pcm_24000`);
    this.ws.addEventListener('open', () => {
      console.log('ElevenLab connection open');

      this.dispatchEvent(new Event('connection is opened'));
    });
    this.ws.addEventListener('close', () => {
      console.log('ElevenLab connection closed');
    });
    this.ws.addEventListener('message', async (event) => {
      await this.audioContext.resume()

      const parsedMessage = JSON.parse(event.data);
      if (!parsedMessage.audio) return;
      this.dispatchEvent(new Event('first'));
      const {arrayBuffer, length} = this.base64ToArrayBuffer(parsedMessage.audio);
      const audioBuffer = this.createAudioBuffer(arrayBuffer, length);

      console.log("AUDIO BUFFER", audioBuffer);

      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;

      source.connect(this.audioContext.destination);

      if (this.nextPlayTime < this.audioContext.currentTime) this.nextPlayTime = this.audioContext.currentTime;

      source.start(this.nextPlayTime);

      this.nextPlayTime += audioBuffer.duration;
    });
    this.ws.addEventListener('error', async (event) => {
      console.error(`WebSocket Error: ${event}`);
    });
  }

  public end(text?: string) {
    console.log("ELEVENLABS END", text)
    text && this.send(text);
    this.ws.send(JSON.stringify({
      text: '',
      xi_api_key: this.settings.elevenlabs.key
    }));
    this.dispatchEvent(new Event('last'));
  }

  public send(text: string) {
    this.dispatchEvent(new Event('send'));
    const _text = text.trim();
    this.ws.send(JSON.stringify({
      text: _text + ' ',
      voice_settings: {
        stability: this.settings.elevenlabs.stability,
        similarity_boost: this.settings.elevenlabs.similarity_boost
      },
      generation_config: {chunk_length_schedule},
      try_trigger_generation: true,
      xi_api_key: this.settings.elevenlabs.key,
      flush: /[.!?,]$/.test(_text),
    }));
  }

  public close() {
    this.ws.close();
    this.audioContext.close();
  }

  public async stopAudio() {
    await this.audioContext.suspend();
  }

  private createAudioBuffer(arrayBuffer: ArrayBuffer, length: number) {
    const data = new DataView(arrayBuffer);

    const audioBuffer = this.audioContext.createBuffer(1, length / 2, 24000);
    const channelData = audioBuffer.getChannelData(0);

    for (let i = 0; i < length; i += 2) {
      const sample = data.getInt16(i, true);
      channelData[i / 2] = sample / 32768;
    }

    return audioBuffer;
  }

  private base64ToArrayBuffer(base64: string) {
    const binaryData = atob(base64);
    const length = binaryData.length;
    const arrayBuffer = new ArrayBuffer(length);
    const uint8Array = new Uint8Array(arrayBuffer);

    for (let i = 0; i < length; i++) {
      uint8Array[i] = binaryData.charCodeAt(i);
    }

    return {arrayBuffer, length};
  }

  public async changeSinkId(audioOutputId: string) {
    const audioContext = this.audioContext as AudioContextWithSetSinkId;
    await audioContext.setSinkId(audioOutputId);
  }
}

export class ElevenLabsTTS implements TTSInterface {
  constructor(private settings: Settings) {
  }

  public stream(voice: string, audioOutputId?: string) {
    return new ElevenLabsTTSStream(this.settings, voice, audioOutputId);
  }

  public async getVoices() {
    return fetch('http://localhost:3500/proxy/elevenlabs/voices', {
      method: 'GET',
      headers: {
        "Accept": "application/json",
        "xi-api-key": this.settings.elevenlabs.key,
        "Content-Type": "application/json",
      }
    }).then((response) => response.json())
      .then((response) => Object.fromEntries(
        response.voices
          .map((voice: any) => [voice.voice_id, voice.name])
      ))
  }

  public async getSubscription(): Promise<Record<string, any>> {
    const fetchClonedVoicesResponse = await fetch('http://localhost:3500/proxy/elevenlabs/subscription', {
      method: 'GET',
      headers: {
        "Accept": "application/json",
        "xi-api-key": this.settings.elevenlabs.key,
        "Content-Type": "application/json",
      }
    })

    return await fetchClonedVoicesResponse.json();
  }
}
