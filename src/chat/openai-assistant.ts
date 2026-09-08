import OpenAI from "openai";
import type {APIPromise} from "openai/core";
import type {AssistantStream, RunCreateParamsBaseStream} from "openai/lib/AssistantStream";
import type {Settings} from "~/src/settings";
import {AbstractChat, ChatCreatedEvent, ChatDeltaEvent, ChatMessageEvent} from "~/src/chat/abstractChat";
// @ts-ignore
import {MessageStreamEvent, Thread} from "openai/resources/beta";

export class OpenAIAssistantChat extends AbstractChat {
  protected client: OpenAI;
  private thread: Thread | null = null;
  private preMessage: APIPromise<MessageStreamEvent> | null = null;
  private currentRun: AssistantStream | null = null;
  protected settings: Settings
  private assistantId: string = ''
  protected useStream = true;

  constructor(settings: Settings) {
    super();
    this.settings = settings;
    this.client = this.getClient();
  }

  protected getClient(): OpenAI {
    const client = new OpenAI({
      dangerouslyAllowBrowser: true,
      apiKey: this.settings.openai.key,
    });

    if (!client) {
      throw new Error("Failed to initialize OpenAI client");
    }

    return client;
  }

  override start(assistantId: string) {
    console.log("START OPEN AI");

    this.assistantId = assistantId;
    this.client.beta.threads.create().then(thread => {
      this.thread = thread;
      this.run();
    });
  }

  public override async preSend(content: string) {
    if (!this.thread) {
      throw new Error('Thread not initialized');
    }
    this.preMessage?.then(({id}) => this.client.beta.threads.messages.del(this.thread.id, id));
    this.preMessage = this.client.beta.threads.messages.create(this.thread.id, {role: 'user', content});
  }

  public send(content: string) {
    if (!this.thread) {
      throw new Error('Thread not initialized');
    }
    (this.preMessage ?? this.client.beta.threads.messages.create(this.thread.id, {role: 'user', content,}))
      .then(() => {
        this.run();
      });
    this.preMessage = null;
  }

  protected run() {
    if (this.useStream) {
      const runBody: RunCreateParamsBaseStream = {
        assistant_id: this.assistantId,
      }

      if (this.settings.openai.assistantInstructions) {
        runBody.instructions = this.settings.openai.assistantInstructions;
      }

      console.log("RUN", this.settings.openai.assistantInstructions)
      console.log("runBody", runBody)

      this.currentRun?.controller.abort();
      this.currentRun = this.client.beta.threads.runs
        .stream(this.thread.id, runBody)
        .on('textCreated', (text) => {
          this.emit('create', new ChatCreatedEvent());
        })
        .on('textDelta', (textDelta) => {
          textDelta.value && this.emit('delta', new ChatDeltaEvent(textDelta.value));
        })
        .on('textDone', (text) => {
          this.emit('message', new ChatMessageEvent(text.value));
          this.currentRun = null;
        })
    } else {
      this.client.beta.threads.runs.create(this.thread.id, {
        assistant_id: this.assistantId,
      }).then(({id}) => {
        this.client.beta.threads.runs.poll(this.thread.id, id)
          .then((run) => {
            this.emit('message', new ChatMessageEvent(run.instructions));
          });
      });
    }
  }

  override async stop() {
    this.currentRun?.controller.abort();
    this.thread && this.client.beta.threads.del(this.thread.id);
  }

  async getAssistants() {
    return this.client.beta.assistants.list()
      .then((response) => Object.fromEntries(
        response.data.map((assistant) => [
          assistant.id,
          assistant.name || assistant.id,
        ]))
      );
  }
}

