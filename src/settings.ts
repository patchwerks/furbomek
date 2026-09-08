export type Settings = {
  elevenlabs: {
    key: string;
    stability: number;
    similarity_boost: number;
    tier: string;
    characters: string;
  };
  playht: {
    key: string;
    user: string;
    engine: string;
    speed: number;
    temperature: number;
    voice_guidance: number;
    text_guidance: number;
  }
  openai: {
    key: string,
    openaiModel: string
    assistantInstructions: string;
  }
  deepgram: {
    key: string;
    utterance: number;
    endpointing: number;
    url: string;
    diarization: boolean;
    punctuation: boolean;
    keywords: string[];
    replace_words: string[];
  },
}

export const defaultSettings: Settings = {
  elevenlabs: {
    key: '',
    stability: 0.5,
    similarity_boost: 0.8,
    tier: '',
    characters: ''
  },
  playht: {
    key: '',
    user: '',
    engine: 'PlayHT2.0',
    speed: 1,
    temperature: 0.4,
    voice_guidance: 1,
    text_guidance: 1
  },
  openai: {
    key: '',
    openaiModel: 'G',
    assistantInstructions: 'You are the \'BIPCI\' - a mechanical spider that knows everything about crypto. You listen to conversations between different people and answer their questions. \n' +
      '\nHowever, you should only answer when your name is mentioned. You shouldn\'t answer if your name isn\'t specified! Your name is \'BIPCI\'. Send an empty response if your name isn\'t mentioned! Always remember that you should answer only when your name is mentioned. \n' +
      '\nCreate short answers. Don\'t create too long answers. Don\'t use markdown and don\'t provide code. U are talking robot. Avoid markdown and avoid code providing. You\'re a conversational bot. Don\'t use any kind of markdown, only plain text! Don\'t use \'**\' symbols or \'##\' symbols to highlight headers.'
  },
  deepgram: {
    key: '',
    utterance: 1000,
    endpointing: 300,
    url: "wss://api.deepgram.com",
    diarization: true,
    punctuation: true,
    keywords: ['BIPCI'],
    replace_words: ['bipci:BIPCI', 'bipsey:BIPCI', 'bipsie:BIPCI', 'bipsy:BIPCI', 'deepsy:BIPCI', 'bibcy:BIPCI', 'beepsy:BIPCI', 'dibsy:BIPCI', 'dipsy:BIPCI', 'deepsea:BIPCI'],
  },
}
