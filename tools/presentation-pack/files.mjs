import { constants } from 'node:fs';
import { lstat, open } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { MAX_PACK_BYTES, parsePack } from '../../packages/extension-preview/index.mjs';
import { MAX_METADATA_BYTES, parseMetadata } from './metadata.mjs';

/** Explicit path only. Caller must trust parent directories; no path discovery. */
export async function readBoundedFile(path, maxBytes) {
  if (typeof path !== 'string' || !path.length || path.includes('\0')) throw new TypeError('Expected an explicit file path');
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > MAX_PACK_BYTES) throw new TypeError('Invalid read budget');
  if (!Number.isInteger(constants.O_NOFOLLOW) || !constants.O_NOFOLLOW ||
      !Number.isInteger(constants.O_NONBLOCK) || !constants.O_NONBLOCK) throw new Error('O_NOFOLLOW and O_NONBLOCK support required');
  const pathBefore = await lstat(path, { bigint: true });
  if (!pathBefore.isFile()) throw new TypeError('Input must be a regular file, not a symlink');
  const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = await file.stat({ bigint: true });
    if (!before.isFile() || before.dev !== pathBefore.dev || before.ino !== pathBefore.ino ||
        before.size !== pathBefore.size || before.mtimeNs !== pathBefore.mtimeNs || before.ctimeNs !== pathBefore.ctimeNs) throw new TypeError('Input changed during open');
    if (before.size > BigInt(maxBytes)) throw new TypeError('Input exceeds byte limit');
    const buffer = new Uint8Array(maxBytes + 1);
    let length = 0;
    while (length < buffer.length) {
      const { bytesRead } = await file.read(buffer, length, buffer.length - length, length);
      if (bytesRead === 0) break;
      length += bytesRead;
    }
    const after = await file.stat({ bigint: true });
    const pathAfter = await lstat(path, { bigint: true });
    if (length > maxBytes) throw new TypeError('Input exceeds byte limit');
    if (!after.isFile() || !pathAfter.isFile() || before.dev !== after.dev || before.ino !== after.ino ||
        after.dev !== pathAfter.dev || after.ino !== pathAfter.ino || before.size !== after.size ||
        BigInt(length) !== after.size || before.mtimeNs !== after.mtimeNs || before.ctimeNs !== after.ctimeNs ||
        after.size !== pathAfter.size || after.mtimeNs !== pathAfter.mtimeNs || after.ctimeNs !== pathAfter.ctimeNs) throw new TypeError('Input changed during read');
    return buffer.slice(0, length);
  } finally { await file.close(); }
}

export async function readPack(path) {
  const bytes = await readBoundedFile(path, MAX_PACK_BYTES);
  const pack = parsePack(bytes);
  const packSha256 = createHash('sha256').update(bytes).digest('hex');
  return { bytes, pack, packSha256 };
}
export async function readMetadata(path) { return parseMetadata(await readBoundedFile(path, MAX_METADATA_BYTES)); }
