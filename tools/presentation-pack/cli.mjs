import { readPack, readMetadata } from './files.mjs';
import { createMetadata, matchMetadata } from './metadata.mjs';

// Escape all non-ASCII characters as well as JSON control escapes, including bidi.
const safeJSON = value => JSON.stringify(value).replace(/[\u007f-\uffff]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
const usage = 'Usage: validate PACK [--metadata META] [--json] | template PACK --author NAME --license ID';
const fileErrors = new Map([
  ['ENOENT', 'Input file was not found.'],
  ['EACCES', 'Permission denied while reading input file.'],
  ['EPERM', 'Permission denied while reading input file.'],
  ['ENOTDIR', 'An input path component is not a directory.'],
  ['EISDIR', 'Input must be a regular file.'],
  ['ELOOP', 'Input path contains a symbolic-link loop or disallowed symbolic link.'],
  ['ENAMETOOLONG', 'Input path is too long.'],
  ['EMFILE', 'Too many files are open. Close other files and try again.'],
  ['ENFILE', 'System file limit reached. Try again later.'],
  ['EIO', 'Could not read input file because of an I/O error.'],
]);
const args = process.argv.slice(2);
let json = false;
let mode;
let path;
let options;
try {
  [mode, path] = args;
  if (!['validate', 'template'].includes(mode) || !path || path.startsWith('--')) throw new Error(usage);
  options = Object.create(null);
  for (let i = 2; i < args.length; i++) {
    const flag = args[i];
    const allowed = mode === 'validate' ? ['--metadata', '--json'] : ['--author', '--license'];
    if (!allowed.includes(flag) || Object.hasOwn(options, flag)) throw new Error(usage);
    if (flag === '--json') options[flag] = true;
    else {
      const value = args[++i];
      if (!value || value.startsWith('--')) throw new Error(usage);
      options[flag] = value;
    }
  }
  json = options['--json'] === true;
  if (mode === 'template' && (!options['--author'] || !options['--license'])) throw new Error(usage);
} catch {
  // A malformed invocation with --json still has machine-readable diagnostics.
  if (args.includes('--json')) process.stdout.write(safeJSON({ ok: false, error: 'usage', message: usage }) + '\n');
  else process.stderr.write(usage + '\n');
  process.exitCode = 2;
}
if (process.exitCode !== 2) {
  try {
    const loaded = await readPack(path);
    if (mode === 'template') {
      const metadata = createMetadata(loaded, options['--author'], options['--license']);
      process.stdout.write(safeJSON(metadata) + '\n');
    } else {
      const metadata = options['--metadata'] ? matchMetadata(await readMetadata(options['--metadata']), loaded) : null;
      const result = { ok: true, pack: path, packId: loaded.pack.packId, packVersion: loaded.pack.packVersion,
        packSha256: loaded.packSha256, metadata: metadata ? 'matched' : 'absent' };
      process.stdout.write(json ? safeJSON(result) + '\n' : `Valid presentation data: ${safeJSON(path)}; metadata ${result.metadata}. No rights or installation approval.\n`);
    }
  } catch (error) {
    // Coded filesystem failures use fixed diagnostics without paths. Validation
    // messages retain their detail, JSON-escaped below; stacks are never emitted.
    const message = error && typeof error === 'object' && 'code' in error
      ? fileErrors.get(error.code) ?? 'Could not read input file.'
      : error instanceof Error ? error.message : 'Validation failed';
    if (json) process.stdout.write(safeJSON({ ok: false, error: 'invalid', message }) + '\n');
    else process.stderr.write(`Validation failed: ${safeJSON(message)}\n`);
    process.exitCode = 1;
  }
}
