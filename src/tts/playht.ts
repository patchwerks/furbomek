import type {Settings} from "~/src/settings";
import type {TTSInterface, TTSStreamInterface} from "~/src/tts/interfaces";
import type {AudioContextWithSetSinkId} from "~/src/types/audio-context.interface";


const HEADERS_SIZE: number = 78;

export class PlayHtTTSStream extends EventTarget implements TTSStreamInterface {
  private nextPlayTime: number = 0;
  private readonly audioContext: AudioContext;
  private textBuffer: string = '';
  private audioStack: Promise<any>[] = [];
  private reader?: ReadableStreamDefaultReader<Uint8Array>;
  private queue: string[] = [];
  private currentRequest: any;

  constructor(private settings: Settings, private voice: string, audioOutputId?: string) {
    super();
    this.audioContext = new AudioContext();

    const audioContext = this.audioContext as AudioContextWithSetSinkId

    if (audioOutputId) {
      audioContext.setSinkId(audioOutputId)
    }
  }

  public end(text: string = '') {
    this.send(text, true);
    this.dispatchEvent(new Event('last'));
  }

  public send(text: string, force = false) {
    const _text = text.trim();
    this.textBuffer += _text + ' ';

    if (force || /[.!?]$/.test(_text)) {
      const text = this.textBuffer.trim();
      this.textBuffer = '';

      if (text.length === 0) return;
      this.queue.push(text);

      this._send();
    }
  }

  public _send() {
    if (this.currentRequest) return;
    if (this.queue.length === 0) return;
    const text = this.queue.join(' ')
    this.queue.length = 0;

    this.dispatchEvent(new Event('send'));
    this.currentRequest = fetch('http://localhost:3500/proxy/playht/stream', {
      method: 'POST',
      headers: {
        "Content-Type": "application/json",
        "Authorization": this.settings.playht.key,
        "X-USER-ID": this.settings.playht.user,
        "accept": "audio/wav"
      },
      body: JSON.stringify({
        "text": text,
        "voice": this.voice,
        "output_format": "wav",
        "sample_rate": 44100,
        "voice_engine": this.settings.playht.engine,
        ...(this.settings.playht.voice_guidance && {voice_guidance: this.settings.playht.voice_guidance}),
        ...(this.settings.playht.text_guidance && {text_guidance: this.settings.playht.text_guidance}),
        ...(this.settings.playht.temperature && {temperature: this.settings.playht.temperature}),
        ...(this.settings.playht.speed && {speed: this.settings.playht.speed}),
      }),
    }).then(response => {
      console.log("STATUS", response.status, response.headers)

      if (response.status === 403) {
        response.json().then((responseJson) => {
          if (responseJson.error_id === "OUT_OF_CREDITS") {
            this.dispatchEvent(new Event('outOfCredits'));
          }

          return;
        });
      } else {
        return response.body!.getReader();
      }
    })

    this.audioStack.push(this.currentRequest);

    this.currentRequest.then((result: any) => {
      console.log("RESULT", result)

      if (!result) {
        return
      }

      this.reader || this.read();
    });
  }

  private async read(): Promise<void> {
    console.log("read method", this.audioStack)

    if (!this.reader) {
      if (this.audioStack.length > 0) {
        this.reader = await this.audioStack.shift();
      } else {
        return;
      }
    }
    const reader = this.reader!;
    console.log("reader", reader)

    //first chunk is headers
    await reader!.read();
    let value: Uint8Array = new Uint8Array(0);

    async function read() {
      const chunk = await reader!.read();
      if (!chunk.done) {
        value = chunk.value;
      }
      return !chunk.done;
    }

    this.currentRequest = undefined;
    this._send();

    let first = true;
    console.log('reading')
    let offset = 0;
    while (await read()) {
      if (first) {
        first = false;
        this.dispatchEvent(new Event('first'));
      }

      let buffer = value!.buffer;
      console.log('buffer', buffer.byteLength)
      if (buffer.byteLength > 0) {
        const [audioBuffer, _offset] = this.createAudioBuffer(buffer, buffer.byteLength, offset);
        offset = _offset;

        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);

        if (this.nextPlayTime < this.audioContext.currentTime) this.nextPlayTime = this.audioContext.currentTime;

        source.start(this.nextPlayTime);

        this.nextPlayTime += audioBuffer.duration;
      }
    }
    this.reader = undefined;
    return this.read();
  }

  public close() {
    this.audioContext.close();
  }

  public async stopAudio() {
    await this.audioContext.suspend();
  }

  private createAudioBuffer(arrayBuffer: ArrayBuffer, length: number, offset = 0) {
    const data = new DataView(arrayBuffer, offset);

    const audioBuffer = this.audioContext.createBuffer(1, length / 2, 44100);
    const channelData = audioBuffer.getChannelData(0);

    for (let i = 0; i < data.byteLength - 1; i += 2) {
      const sample = data.getInt16(i, true);
      channelData[i / 2] = sample / 32768;
    }

    return [audioBuffer, data.byteLength % 2] as const;
  }

  public async changeSinkId(audioOutputId: string) {
    const audioContext = this.audioContext as AudioContextWithSetSinkId;
    await audioContext.setSinkId(audioOutputId);
  }
}

export class PlayHtTTS implements TTSInterface {
  constructor(private settings: Settings) {
  }

  public stream(voice: string, audioOutputId?: string) {
    return new PlayHtTTSStream(this.settings, voice, audioOutputId);
  }

  public async getVoices() {
    const fetchVoicesResponse = await fetch('http://localhost:3500/proxy/playht/voices', {
      method: 'GET',
      headers: {
        "Accept": "application/json",
        "Authorization": this.settings.playht.key,
        "X-USER-ID": this.settings.playht.user,
      }
    })
    const jsonVoicesResponse = await fetchVoicesResponse.json();
    const voicesResponse = Object.fromEntries(
      jsonVoicesResponse
        .filter((voice: any) => voice.voice_engine === 'PlayHT2.0')
        .map((voice: { id: string, name: string }) => [voice.id, voice.name])
    )

    const fetchClonedVoicesResponse = await fetch('http://localhost:3500/proxy/playht/cloned-voices', {
      method: 'GET',
      headers: {
        "Accept": "application/json",
        "Authorization": this.settings.playht.key,
        "X-USER-ID": this.settings.playht.user,
      }
    })
    const jsonClonedVoicesResponse = await fetchClonedVoicesResponse.json();
    const clonedVoicesResponse = Object.fromEntries(
      jsonClonedVoicesResponse
        .filter((voice: any) => voice.voice_engine === 'PlayHT2.0')
        .map((voice: { id: string, name: string }) => [voice.id, voice.name])
    )

    return {...voicesResponse, ...clonedVoicesResponse}
  }

  async getSubscription(): Promise<Record<string, any>> {
    return {"1": 'tier'}
  }
}
