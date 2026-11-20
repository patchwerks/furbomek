import assert from 'node:assert/strict';
import { mkdtemp, rm, mkdir, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import ky from 'ky';
import { startFixture } from '../fixture/server.ts';
import { stateSchema, previewSchema, initialFraming } from '../src/model.ts';
import { reactionPackSchema } from '../src/generated.ts';
import type { State } from '../src/model.ts';

if (!process.argv.includes('--fixture') || process.argv.at(-1) !== 'all') throw new Error('Use qa -- --fixture all');
const output = resolve(process.env['STUDIO_EVIDENCE_DIR'] ?? '.qa');
await mkdir(output, { recursive: true });
const temp = await mkdtemp(join(tmpdir(), 'studio-qa-'));
const file = join(temp, 'state.json');
let server = await startFixture(file);
let origin = new URL(server.url).origin;
let state: State;
const happy: {scenario:string; observable:unknown}[] = [];
const failure: {scenario:string; observable:unknown}[] = [];
const original = reactionPackSchema.parse(JSON.parse(await readFile(new URL('../../../packages/production-contracts/fixtures/liquidation.json', import.meta.url), 'utf8')));
async function read() { return stateSchema.parse(await ky.get(`${origin}/fixture/state`, { retry:0 }).json()); }
async function post(action: string, payload: unknown, from = origin) {
  return ky.post(`${origin}/fixture/${action}`, { json:payload, headers:{origin:from}, retry:0, timeout:20000, throwHttpErrors:false });
}
const base = () => ({ epoch:state.epoch, revision:state.revision });
try {
  state = await read();
  const effect = { capability:'graphics.pulse.v1', preset:'rgb', intensity_percent:37, duration_ms:800 };
  const response = await post('preview', { ...base(), effect });
  assert.equal(response.status, 200);
  const preview = previewSchema.parse(await response.json());
  assert.deepEqual(preview.effect, effect);
  assert.equal((await read()).revision, 0);
  happy.push({scenario:'preview leaves applied state unchanged', observable:{preview,revision:0}});
  state = stateSchema.parse(await (await post('apply', {...base(), effect})).json());
  assert.deepEqual(state.applied, effect); assert.equal(state.revision, 1);
  const snapshot = structuredClone(state);
  state = stateSchema.parse(await (await post('save', {...base(), saved:{effect:state.applied,pack:original,framing:initialFraming,binding:'liquidation'}})).json());
  const second = {...effect,intensity_percent:65};
  state = stateSchema.parse(await (await post('apply', {...base(),effect:second})).json());
  state = stateSchema.parse(await (await post('revert',base())).json());
  assert.deepEqual(state.applied,effect); assert.equal(state.revision,3);
  state = stateSchema.parse(await (await post('apply',{...base(),effect:second})).json());
  state = stateSchema.parse(await (await post('restore',base())).json());
  assert.deepEqual(state.applied,effect); assert.equal(state.revision,5);
  happy.push({scenario:'apply save explicit revert and restore preserve exact parameters',observable:state});
  let result = await post('apply',{epoch:snapshot.epoch,revision:snapshot.revision,effect:second});
  assert.equal(result.status,409); assert.deepEqual((await read()).applied,effect);
  failure.push({scenario:'stale revision cannot overwrite current state',observable:{status:result.status,revision:state.revision}});
  for (const [name, bad] of [
    ['unavailable motion',original.cues.find(c => c.id === 'motion')?.effect],
    ['out of range',{...effect,intensity_percent:101}],
    ['arbitrary command',{...effect,command:'unsafe'}],
    ['unknown capability',{...effect,capability:'serial.raw'}],
  ]) {
    result = await post('apply',{...base(),effect:bad});
    assert.equal(result.status,422); assert.deepEqual((await read()).applied,effect);
    failure.push({scenario:String(name),observable:{status:result.status,revision:(await read()).revision}});
  }
  result = await post('apply',{...base(),effect:second},'https://invalid.example'); assert.equal(result.status,403);
  failure.push({scenario:'cross-origin write rejected',observable:{status:403}});
  result = await post('save',{...base(),saved:{effect:state.applied,pack:original,framing:{...initialFraming,rules:['subject','subject']},binding:'liquidation'}});
  assert.equal(result.status,422);
  failure.push({scenario:'duplicate framing fallbacks rejected',observable:{status:422}});
  const dry = previewSchema.parse(await (await post('dry-run',{...base(),pack:original})).json());
  assert.equal(dry.dispatch,false); assert.equal(dry.timeline?.find(r=>r.id==='motion')?.status,'skipped');
  assert.equal(dry.timeline?.find(r=>r.id==='graphics')?.start_ms,0);
  assert.equal(dry.timeline?.find(r=>r.id==='motion')?.start_ms,1000);
  happy.push({scenario:'canonical liquidation graph has parallel media and skipped conditional motion',observable:dry});
  const cancellationPack = structuredClone(original);
  const motion = cancellationPack.cues.find(c => c.id === 'motion'); assert.ok(motion); motion.on_unavailable = 'cancel_pack';
  cancellationPack.cues.push({id:'after-cancel',after:['motion','graphics'],effect:{capability:'graphics.pulse.v1',preset:'neutral',intensity_percent:50,duration_ms:1000},condition:'always',ttl_ms:1000,on_unavailable:'skip',on_fault:'cancel_pack'});
  const cancellationPreview = previewSchema.parse(await (await post('dry-run',{...base(),pack:cancellationPack})).json());
  assert.equal(cancellationPreview.timeline?.find(r => r.id === 'motion')?.status,'would_cancel_pack');
  assert.equal(cancellationPreview.timeline?.find(r => r.id === 'after-cancel')?.status,'cancelled');
  happy.push({scenario:'unavailable cancel policy is represented in dry-run',observable:cancellationPreview});
  const badPack = structuredClone(original);
  const first = badPack.cues[0]; assert.ok(first); first.ttl_ms = 1;
  result = await post('dry-run',{...base(),pack:badPack}); assert.equal(result.status,422);
  const conflict = structuredClone(original); const duplicate = conflict.cues[0]; assert.ok(duplicate); conflict.cues.push({...duplicate,id:'conflict'});
  result = await post('dry-run',{...base(),pack:conflict}); assert.equal(result.status,422);
  failure.push({scenario:'canonical validator rejects TTL overflow and concurrent resource conflict',observable:{status:422}});
  state = stateSchema.parse(await (await post('cancel',base())).json()); assert.equal(state.run,'cancelled');
  happy.push({scenario:'cancel clears fixture rehearsal',observable:{run:state.run}});
  state = stateSchema.parse(await (await post('scenario',{...base(),scenario:'stale'})).json());
  result = await post('apply',{...base(),effect:second}); assert.equal(result.status,409);
  failure.push({scenario:'stale health blocks writes',observable:{status:409}});
  state = stateSchema.parse(await (await post('reconnect',base())).json());
  await post('scenario',{...base(),scenario:'disconnect'});
  result = await ky.get(`${origin}/fixture/state`,{throwHttpErrors:false,retry:0}); assert.equal(result.status,503);
  failure.push({scenario:'network-disconnect scenario refuses state reads',observable:{status:503}});
  state = stateSchema.parse(await (await post('reconnect',base())).json());
  const priorEpoch = state.epoch;
  await server.close(); server = await startFixture(file); origin = new URL(server.url).origin;
  state = await read(); assert.equal(state.health,'stale'); assert.notEqual(state.epoch,priorEpoch); assert.deepEqual(state.applied,effect);
  state = stateSchema.parse(await (await post('reconnect',base())).json());
  result = await post('apply',{epoch:priorEpoch,revision:state.revision,effect:second}); assert.equal(result.status,409);
  assert.deepEqual(state.applied,effect); assert.equal(state.health,'fresh');
  happy.push({scenario:'restart marks persistent applied state stale; explicit reconnect preserves it exactly',observable:state});
  failure.push({scenario:'old session after restart cannot mutate',observable:{status:409}});
  await writeFile(join(output,'happy.json'),JSON.stringify({mode:'fixture',dispatch:false,passed:true,invocation:'npm --prefix apps/production-studio run qa -- --fixture all',scenarios:happy},null,2));
  await writeFile(join(output,'failure.json'),JSON.stringify({mode:'fixture',dispatch:false,passed:true,scenarios:failure},null,2));
  console.log(JSON.stringify({passed:true,happy:happy.length,failure:failure.length,evidence:output,previewCommand:'npm --prefix apps/production-studio run fixture'}));
} finally { await server.close(); await rm(temp,{recursive:true,force:true}); await writeFile(join(output,'cleanup.json'),JSON.stringify({serverClosed:true,temporaryStateRemoved:true})); }
