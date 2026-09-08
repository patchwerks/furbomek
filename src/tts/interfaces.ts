export interface TTSStreamInterface extends EventTarget {
  send(text: string, force?: boolean): void;

  end(text?: string): void;

  stopAudio(): void;

  close(): void;

  changeSinkId(deviceId: string): void;
}

export interface TTSInterface {
  stream(voice: string, audioOutputId?: string): TTSStreamInterface;

  getVoices(): Promise<Record<string, string>>;

  getSubscription(): Promise<Record<string, any>>;
}
