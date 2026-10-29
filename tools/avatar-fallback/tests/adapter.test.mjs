import {test} from 'node:test';
import assert from 'node:assert/strict';
import '../adapter.js';
const {ASSET, createAdapter} = globalThis.FurbomekStatic;
const START = Date.parse('2026-10-29T12:00:00.000Z');
const event = (overrides = {}) => JSON.stringify({schemaVersion:'furbomek.character.v1', kind:'agent.activity', source:'hermes-adapter', audience:'public', sensitivity:'public', seq:1, observedAt:new Date(START).toISOString(), ttlMs:1000, payload:{title:'Furb-o-Mek', summary:'Fixture caption', status:'thinking', tool:'AGENT'}, ...overrides});
function setup() { let time = START; const frames=[]; const adapter=createAdapter({now:()=>time, render:s=>frames.push(s)}); adapter.load_character(ASSET); return {adapter, frames, time:t=>{time=t;}}; }

test('loads only bundled asset; begins honestly offline; capabilities exclude speech/animation', () => {
 const {adapter:a}=setup(); assert.equal(a.health(),'degraded'); assert.equal(a.snapshot().state,'offline');
 assert.equal(a.load_character('https://example.com/model.vrm'),false); assert.equal(a.snapshot().asset,ASSET);
 assert.deepEqual(a.capabilities().visemes,[]); assert.equal(a.capabilities().audio,false);
});
test('accepted public projection reaches rendering without screen or timeline data', () => {
 const {adapter:a,frames}=setup(); const p=JSON.parse(event()).payload;
 p.screen={filename:'private.png'}; p.timeline=[{detail:'not part of static consumer'}];
 assert.equal(a.apply_event(event({payload:p})),true); assert.equal(frames.at(-1).caption,'Fixture caption');
 assert.equal(a.health(),'ready'); assert.equal('screen' in a.snapshot(),false); assert.equal('timeline' in a.snapshot(),false);
});
test('expiry clears caption and cannot be reversed by clock rollback or stale replay', () => {
 const {adapter:a,time}=setup(); a.apply_event(event()); time(START+1000); a.tick();
 assert.equal(a.snapshot().caption,'Activity unavailable'); time(START+500);
 assert.equal(a.apply_event(event()),false); assert.equal(a.snapshot().state,'offline');
});
test('duplicate and out-of-order snapshots do not extend freshness', () => {
 const {adapter:a,time}=setup(); a.apply_snapshot(event({seq:2}));
 assert.equal(a.apply_snapshot(event({seq:2,ttlMs:30000})),false); assert.equal(a.apply_event(event({seq:1})),false);
 time(START+1000); assert.equal(a.snapshot().state,'offline');
});
test('invalid boundaries cannot mutate accepted state', () => {
 const {adapter:a}=setup(); a.apply_event(event());
 const cases=[{seq:-1},{seq:1.1},{seq:Number.MAX_SAFE_INTEGER+1},{ttlMs:0},{ttlMs:30001},{ttlMs:1.5},{audience:'private'},{sensitivity:'secret'},{kind:'robot.move'},{source:'unknown'},{schemaVersion:'v2'},{observedAt:'2026-02-30T12:00:00.000Z'},{observedAt:new Date(START+1).toISOString()},{observedAt:new Date(START-1000).toISOString()},{payload:{title:'x',summary:'x',status:'x'.repeat(25),tool:'AGENT'}},{payload:{title:'x',summary:'x'.repeat(181),status:'idle',tool:'AGENT'}}];
 for (const c of cases) assert.equal(a.apply_event(event({seq:2,...c})),false,JSON.stringify(c));
 for(const raw of ['null','[]','{', ' '.repeat(8193), event({payload:{title:9}})]) assert.equal(a.apply_event(raw),false);
 assert.equal(a.snapshot().seq,1); assert.equal(a.snapshot().caption,'Fixture caption');
});
test('hide/show retains current snapshot; shutdown is terminal and idempotent', () => {
 const {adapter:a}=setup(); a.apply_event(event()); a.set_visible(false); assert.equal(a.snapshot().visible,false);
 a.set_visible(true); assert.equal(a.snapshot().visible,true); assert.equal(a.set_visible('yes'),false);
 a.shutdown(); a.shutdown(); assert.equal(a.health(),'failed'); assert.equal(a.snapshot().visible,false);
 assert.equal(a.apply_event(event({seq:2})),false); assert.equal(a.load_character(ASSET),false);
});
test('fixture provenance is immutable and explicit', () => {
 const frames=[]; const a=createAdapter({render:s=>frames.push(s),now:()=>START,fixture:true});
 a.load_character(ASSET); a.apply_event(event()); assert.equal(frames.at(-1).fixture,true);
 a.shutdown(); assert.equal(a.snapshot().fixture,true);
});
test('text is passed as text; no markup interpretation in model', () => {
 const {adapter:a}=setup(); const payload=JSON.parse(event()).payload; payload.summary='<img src=x onerror=alert(1)>';
 assert.equal(a.apply_event(event({payload})),true); assert.equal(a.snapshot().caption,payload.summary);
});

test('text bounds match producer Unicode codepoint counts, not UTF-16 units', () => {
 const {adapter:a}=setup();
 const payload={title:'🦊'.repeat(180),summary:'🦊'.repeat(100),status:'🦊'.repeat(24),tool:'🦊'.repeat(12)};
 assert.equal(a.apply_event(event({payload})),true);
 assert.equal(a.snapshot().caption,payload.summary);
 for (const [field,limit] of [['title',180],['summary',180],['status',24],['tool',12]]) {
   const boundary={...payload,[field]:'🦊'.repeat(limit)};
   assert.equal(a.apply_event(event({seq:a.snapshot().seq+1,payload:boundary})),true,field+' at limit');
   assert.equal(a.apply_event(event({seq:a.snapshot().seq+1,payload:{...boundary,[field]:'🦊'.repeat(limit+1)}})),false,field+' over limit');
 }
});
test('clock rollback before expiry immediately clears presentation and cannot resurrect it', () => {
 const {adapter:a,time,frames}=setup(); assert.equal(a.apply_event(event()),true);
 time(START+100); a.tick(); time(START-60000); a.tick();
 assert.equal(frames.at(-1).caption,'Activity unavailable'); assert.equal(a.health(),'degraded');
 assert.equal(a.snapshot().state,'offline');
 time(START+101); a.tick(); assert.equal(a.snapshot().state,'offline');
 assert.equal(a.apply_event(event()),false); assert.equal(a.snapshot().state,'offline');
 assert.equal(a.apply_event(event({seq:2,observedAt:new Date(START+101).toISOString()})),true);
});
test('incoming event cannot bypass a newly detected backwards clock', () => {
 const {adapter:a,time,frames}=setup(); a.apply_event(event()); time(START-60000);
 const incoming=event({seq:2,observedAt:new Date(START-60000).toISOString()});
 assert.equal(a.apply_event(incoming),false); assert.equal(frames.at(-1).state,'offline');
 time(START-59000); assert.equal(a.apply_event(event({seq:3,observedAt:new Date(START-59000).toISOString()})),false);
 assert.equal(a.snapshot().seq,1);
});

test('non-string timestamps reject without throwing, mutation or TTL extension', () => {
 const {adapter:a,time,frames}=setup(); assert.equal(a.apply_event(event()),true);
 time(START+500); const before=a.snapshot(); const count=frames.length;
 const invalid=[{toString:null,valueOf:null},START,null,[new Date(START).toISOString()]];
 for (const method of ['apply_snapshot','apply_event']) {
   for (const observedAt of invalid) {
     assert.equal(a[method](event({seq:2,ttlMs:30000,observedAt})),false);
     assert.deepEqual(a.snapshot(),before); assert.equal(frames.length,count);
   }
 }
 time(START+1000); assert.equal(a.snapshot().state,'offline');
 assert.equal(a.snapshot().caption,'Activity unavailable'); assert.equal(a.snapshot().seq,1);
});
