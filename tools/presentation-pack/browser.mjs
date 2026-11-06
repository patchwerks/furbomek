import { MAX_PACK_BYTES, parsePack } from '../../packages/extension-preview/index.mjs';
import { MAX_METADATA_BYTES, parseMetadata, matchMetadata } from './metadata.mjs';

const unsupported = 'Browser metadata validation requires Web Crypto SHA-256 in a secure context';

/** Validate a companion against a snapshot of exact pack bytes; no I/O or authority grant. */
export async function validateBrowserMetadata(packBytes, metadataBytes) {
  if (!(packBytes instanceof Uint8Array) || packBytes.byteLength > MAX_PACK_BYTES) {
    throw new TypeError('Expected at most 1 MiB of Uint8Array pack bytes');
  }
  if (!(metadataBytes instanceof Uint8Array) || metadataBytes.byteLength > MAX_METADATA_BYTES) {
    throw new TypeError('Expected at most 16 KiB of Uint8Array companion bytes');
  }
  if (typeof SharedArrayBuffer !== 'undefined' &&
      (packBytes.buffer instanceof SharedArrayBuffer || metadataBytes.buffer instanceof SharedArrayBuffer)) {
    throw new TypeError('Shared byte buffers are unsupported');
  }
  // Copy both views before the first await: parsing and hashing must see one snapshot.
  const packSnapshot = new Uint8Array(packBytes);
  const metadataSnapshot = new Uint8Array(metadataBytes);
  const pack = parsePack(packSnapshot);
  const metadata = parseMetadata(metadataSnapshot);
  let digest;
  try {
    if (globalThis.isSecureContext === false || !globalThis.crypto?.subtle) throw new Error(unsupported);
    digest = await globalThis.crypto.subtle.digest('SHA-256', packSnapshot);
  } catch {
    throw new Error(unsupported);
  }
  const packSha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  matchMetadata(metadata, { pack, packSha256 });
  return Object.freeze({ pack, metadata, packSha256 });
}
