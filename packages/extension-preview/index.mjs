/** Data-only preview contract. No renderer, live transport, or action authority. */
export const MAX_PACK_BYTES = 1024 * 1024;
const acceptedPacks = new WeakSet();
const EXPRESSION = 'presentation.expression';
const REACTION = 'presentation.reaction';

function invalid(message) {
  throw new TypeError(`Invalid preview pack: ${message}`);
}

// Parse JSON directly so duplicate decoded keys cannot disappear in JSON.parse.
// Only individual string tokens use JSON.parse, for JSON escape semantics.
function strictJSON(text) {
  let cursor = 0;
  const whitespace = () => {
    while (cursor < text.length && /[\x20\t\r\n]/.test(text[cursor])) cursor++;
  };
  const string = () => {
    const start = cursor++;
    while (cursor < text.length) {
      const char = text[cursor++];
      if (char === '"') {
        try { return JSON.parse(text.slice(start, cursor)); }
        catch { invalid('invalid JSON string'); }
      }
      if (char === '\\') cursor++;
    }
    invalid('unterminated JSON string');
  };
  const value = (depth) => {
    whitespace();
    const char = text[cursor];
    if (char === '{' || char === '[') {
      if (depth >= 8) invalid('JSON nesting exceeds 8 containers');
      cursor++;
      const object = char === '{';
      const result = object ? Object.create(null) : [];
      const end = object ? '}' : ']';
      whitespace();
      if (text[cursor] === end) { cursor++; return result; }
      while (cursor < text.length) {
        whitespace();
        if (object) {
          if (text[cursor] !== '"') invalid('expected object key');
          const key = string();
          if (Object.hasOwn(result, key)) invalid('duplicate JSON key');
          whitespace();
          if (text[cursor++] !== ':') invalid('expected colon');
          result[key] = value(depth + 1);
        } else {
          result.push(value(depth + 1));
        }
        whitespace();
        const separator = text[cursor++];
        if (separator === end) return result;
        if (separator !== ',') invalid('expected comma or closing delimiter');
      }
      invalid('unterminated container');
    }
    if (char === '"') return string();
    for (const [token, result] of [['true', true], ['false', false], ['null', null]]) {
      if (text.startsWith(token, cursor)) { cursor += token.length; return result; }
    }
    const number = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(cursor));
    if (!number) invalid('expected JSON value');
    cursor += number[0].length;
    const result = Number(number[0]);
    if (!Number.isFinite(result)) invalid('non-finite number');
    return result;
  };
  const result = value(0);
  whitespace();
  if (cursor !== text.length) invalid('trailing JSON content');
  return result;
}

function exactKeys(object, keys) {
  if (object === null || typeof object !== 'object' || Array.isArray(object)) invalid('expected object');
  const actual = Object.keys(object);
  if (actual.length !== keys.length || !keys.every(key => Object.hasOwn(object, key))) invalid('unexpected or missing fields');
}

function validate(pack) {
  exactKeys(pack, ['schemaVersion', 'packId', 'packVersion', 'previewContractVersion', 'capabilities', 'durationMs', 'events']);
  if (pack.schemaVersion !== 1 || pack.previewContractVersion !== 1) invalid('unsupported contract version');
  if (typeof pack.packId !== 'string' || !/^[a-z][a-z0-9-]{0,63}$(?![\s\S])/.test(pack.packId)) invalid('invalid packId');
  if (typeof pack.packVersion !== 'string' || pack.packVersion.length > 32 || !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$(?![\s\S])/.test(pack.packVersion)) invalid('invalid packVersion');
  const capabilities = pack.capabilities;
  if (!Array.isArray(capabilities) || capabilities.length < 1 || capabilities.length > 2 ||
      new Set(capabilities).size !== capabilities.length || !capabilities.includes(EXPRESSION) ||
      !capabilities.every(capability => capability === EXPRESSION || capability === REACTION)) invalid('invalid capabilities');
  if (!Number.isInteger(pack.durationMs) || pack.durationMs < 1 || pack.durationMs > 30000) invalid('invalid durationMs');
  if (!Array.isArray(pack.events) || pack.events.length < 1 || pack.events.length > 64) invalid('invalid events');
  let previousTime = 0;
  pack.events.forEach((event, index) => {
    exactKeys(event, ['seq', 'atMs', 'kind', 'value']);
    if (event.seq !== index + 1) invalid('non-contiguous sequence');
    if (!Number.isInteger(event.atMs) || event.atMs < previousTime || event.atMs >= pack.durationMs) invalid('invalid event time');
    if (!capabilities.includes(event.kind)) invalid('undeclared event capability');
    if (event.kind === EXPRESSION ? !['neutral', 'curious'].includes(event.value) : event.value !== 'acknowledge') invalid('invalid event value');
    if ((index === 0 && event.atMs !== 0) || (event.atMs === 0 && (event.kind !== EXPRESSION || event.value !== 'neutral'))) invalid('time zero must be neutral expression');
    previousTime = event.atMs;
    Object.freeze(event);
  });
  Object.freeze(pack.events);
  Object.freeze(pack.capabilities);
  return Object.freeze(pack);
}

/** Parse at most 1 MiB of strict UTF-8 JSON into an immutable branded pack. */
export function parsePack(bytes) {
  if (!(bytes instanceof Uint8Array)) invalid('expected Uint8Array bytes');
  if (bytes.byteLength > MAX_PACK_BYTES) invalid('input exceeds 1 MiB');
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { invalid('invalid UTF-8'); }
  if (text.charCodeAt(0) === 0xfeff) invalid('BOM is forbidden');
  const pack = validate(strictJSON(text));
  acceptedPacks.add(pack);
  return pack;
}

/** Stateless elapsed-time sampling; calling with zero is always a neutral reset. */
export function samplePack(pack, positionMs) {
  if (!acceptedPacks.has(pack)) invalid('sample requires an unmodified parsePack result');
  if (typeof positionMs !== 'number' || !Number.isFinite(positionMs) || positionMs < 0) invalid('invalid sample time');
  positionMs = Math.min(positionMs, pack.durationMs);
  let expression = 'neutral';
  let reaction = null;
  let reactionProgress = 0;
  if (positionMs < pack.durationMs) {
    let expressionEvent;
    let reactionEvent;
    for (const event of pack.events) {
      if (event.atMs > positionMs) break;
      if (event.kind === EXPRESSION) expressionEvent = event;
      else reactionEvent = event;
    }
    if (expressionEvent.value === 'curious' && positionMs - expressionEvent.atMs < 1000) expression = 'curious';
    if (reactionEvent && positionMs - reactionEvent.atMs < 600) {
      reaction = 'acknowledge';
      reactionProgress = (positionMs - reactionEvent.atMs) / 600;
    }
  }
  return Object.freeze({ positionMs, expression, reaction, reactionProgress });
}
