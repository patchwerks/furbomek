/** Separate, data-only companion format; never extends the core pack schema. */
export const MAX_METADATA_BYTES = 16 * 1024;
const keys = ['metadataVersion', 'packId', 'packVersion', 'previewContractVersion', 'author', 'license', 'packSha256'];
const invalid = message => { throw new TypeError(`Invalid companion metadata: ${message}`); };

export function validateAuthorLicense(author, license) {
  if (typeof author !== 'string' || [...author].length < 1 || [...author].length > 80 ||
      author !== author.trim() || /[\p{C}\p{Zl}\p{Zp}]/u.test(author)) invalid('author must be a printable public name of 1–80 characters without surrounding whitespace');
  if (license !== 'MIT' && license !== 'CC0-1.0') invalid('license must explicitly be MIT or CC0-1.0');
}

export function parseMetadata(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.byteLength > MAX_METADATA_BYTES) invalid('expected at most 16 KiB of bytes');
  let text;
  try { text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { invalid('invalid UTF-8'); }
  if (text.charCodeAt(0) === 0xfeff) invalid('BOM is forbidden');
  let cursor = 0;
  const whitespace = () => { while (cursor < text.length && /[\x20\t\r\n]/.test(text[cursor])) cursor++; };
  const string = () => {
    if (text[cursor] !== '"') invalid('expected JSON string');
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
  whitespace();
  if (text[cursor++] !== '{') invalid('expected flat object');
  const result = Object.create(null);
  whitespace();
  if (text[cursor] !== '}') {
    while (cursor < text.length) {
      whitespace();
      const key = string();
      if (Object.hasOwn(result, key)) invalid('duplicate decoded key');
      if (!keys.includes(key)) invalid('unknown field');
      whitespace();
      if (text[cursor++] !== ':') invalid('expected colon');
      whitespace();
      if (text[cursor] === '"') result[key] = string();
      else {
        const token = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(cursor));
        if (!token) invalid('expected string or number; nesting is forbidden');
        cursor += token[0].length;
        result[key] = Number(token[0]);
      }
      whitespace();
      if (text[cursor] === '}') break;
      if (text[cursor++] !== ',') invalid('expected comma or closing delimiter');
    }
  }
  if (text[cursor++] !== '}') invalid('unterminated object');
  whitespace();
  if (cursor !== text.length) invalid('trailing JSON content');
  if (Object.keys(result).length !== keys.length) invalid('missing fields');
  if (result.metadataVersion !== 1 || result.previewContractVersion !== 1) invalid('unsupported version');
  if (typeof result.packId !== 'string' || !/^[a-z][a-z0-9-]{0,63}$(?![\s\S])/.test(result.packId)) invalid('invalid packId');
  if (typeof result.packVersion !== 'string' || result.packVersion.length > 32 || !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$(?![\s\S])/.test(result.packVersion)) invalid('invalid packVersion');
  validateAuthorLicense(result.author, result.license);
  if (typeof result.packSha256 !== 'string' || !/^[a-f0-9]{64}$(?![\s\S])/.test(result.packSha256)) invalid('invalid packSha256');
  return Object.freeze(result);
}

export function createMetadata({ pack, packSha256 }, author, license) {
  validateAuthorLicense(author, license);
  return parseMetadata(new TextEncoder().encode(JSON.stringify({
    metadataVersion: 1, packId: pack.packId, packVersion: pack.packVersion,
    previewContractVersion: pack.previewContractVersion, author, license, packSha256,
  })));
}

export function matchMetadata(metadata, { pack, packSha256 }) {
  for (const key of ['packId', 'packVersion', 'previewContractVersion']) {
    if (metadata[key] !== pack[key]) invalid(`${key} does not match pack`);
  }
  if (metadata.packSha256 !== packSha256) invalid('exact-byte digest does not match pack');
  return metadata;
}
