import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startFixture } from './server.ts';
const dir = await mkdtemp(join(tmpdir(), 'production-studio-'));
const server = await startFixture(join(dir, 'state.json'));
console.log(JSON.stringify({ mode: 'fixture', url: server.url, dispatch: false }));
const stop = async () => { await server.close(); await rm(dir, { recursive: true, force: true }); process.exit(0); };
process.once('SIGINT', stop); process.once('SIGTERM', stop);
