export interface Message {
  type: 'user' | 'assistant';
  text: string;
  userIndex?: number;
  assistantTime?: number;
  ttsTime?: number;
  sttTime?: number;
}
