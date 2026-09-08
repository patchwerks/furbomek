export abstract class ChatEvent {
}

export class ChatCreatedEvent extends ChatEvent {
}

export class ChatMessageEvent extends ChatEvent {
  constructor(public message: string) {
    super();
  }
}

export class ChatDeltaEvent extends ChatEvent {
  constructor(public message: string) {
    super();
  }
}

interface FileReaderEventMap {
  "message": ChatMessageEvent;
  "delta": ChatDeltaEvent;
  "create": ChatCreatedEvent
}

export abstract class AbstractChat {
  private listeners: { [type: string]: ((event: ChatEvent) => void)[] } = {};

  start(assistantId: string) {
    this.run()
  }

  stop(): void {
  }

  abstract send(content: string): void;

  preSend(content: string): void {
  }

  protected abstract run(): void;


  on<K extends keyof FileReaderEventMap>(type: K, listener: (ev: FileReaderEventMap[K]) => any): void;
  on(type: string, listener: (event: ChatEvent) => any): void
  on(type: string, listener: (event: ChatEvent) => void): void {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(listener);
  }

  off(type: string, listener: (event: ChatEvent) => void): void {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter(l => l !== listener);
    }
  }

  emit(type: string, event: ChatEvent) {
    if (this.listeners[type]) {
      this.listeners[type].forEach(l => l(event));
    }
  }
}
