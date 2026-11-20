import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import type { ReactionPack } from '../src/generated.ts';
const exec = promisify(execFile);
const project = new URL('../../../services/embodiment-gateway/', import.meta.url).pathname;
export class FixtureError extends Error {
  readonly status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}
export async function validatePack(pack: ReactionPack): Promise<void> {
  const temp = await mkdtemp(join(tmpdir(), 'studio-pack-'));
  try {
    const file = join(temp, 'pack.json');
    await writeFile(file, JSON.stringify(pack), { mode: 0o600 });
    await exec('uv', ['run','--frozen','--project',project,'python','-m','furbomek_gateway.export_production_schema','--validate',file], { timeout: 15000, maxBuffer: 32768 });
  } catch (error) {
    if (!(error instanceof Error)) throw error;
    throw new FixtureError(422, 'Cue graph rejected by canonical validator: check dependencies, TTL, resource conflicts and the 30-second horizon.');
  } finally { await rm(temp, { recursive: true, force: true }); }
}
