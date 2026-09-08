export interface AudioContextWithSetSinkId extends AudioContext {
  setSinkId(sinkId: string): Promise<void>;
}
