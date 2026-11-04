/** Node-only explicit operator file input; never imported by the browser core. */
import { constants } from 'node:fs';
import { lstat, open } from 'node:fs/promises';
import { MAX_PACK_BYTES, parsePack } from './index.mjs';

export async function loadPackFile(path) {
  if (typeof path !== 'string' || path.length === 0 || path.includes('\0')) throw new TypeError('Expected an explicit operator file path');
  // Fail closed where the platform cannot prevent following a final symlink.
  if (!Number.isInteger(constants.O_NOFOLLOW) || constants.O_NOFOLLOW === 0) throw new Error('O_NOFOLLOW is required');
  const beforeOpen = await lstat(path, { bigint: true });
  if (!beforeOpen.isFile()) throw new TypeError('Pack input must be a regular file, not a symlink');
  // O_NONBLOCK prevents a raced replacement FIFO from blocking open before fstat.
  const file = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW | (constants.O_NONBLOCK ?? 0));
  try {
    const before = await file.stat({ bigint: true });
    if (!before.isFile() || before.dev !== beforeOpen.dev || before.ino !== beforeOpen.ino) throw new TypeError('Pack file changed during open');
    if (before.size > BigInt(MAX_PACK_BYTES)) throw new TypeError('Pack input exceeds 1 MiB');
    const bytes = new Uint8Array(MAX_PACK_BYTES + 1);
    let length = 0;
    while (length < bytes.length) {
      const { bytesRead } = await file.read(bytes, length, bytes.length - length, length);
      if (bytesRead === 0) break;
      length += bytesRead;
    }
    const after = await file.stat({ bigint: true });
    if (length > MAX_PACK_BYTES) throw new TypeError('Pack input exceeds 1 MiB');
    if (!after.isFile() || before.size !== after.size || BigInt(length) !== after.size ||
        before.mtimeNs !== after.mtimeNs || before.ctimeNs !== after.ctimeNs) throw new TypeError('Pack file changed during read');
    return parsePack(bytes.subarray(0, length));
  } finally {
    await file.close();
  }
}
