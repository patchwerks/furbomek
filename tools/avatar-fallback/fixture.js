'use strict';
// Explicit separate fixture entrypoint. Never imported by the normal fallback.
function fixtureEvent(seq, summary, status) {
  return JSON.stringify({schemaVersion: 'furbomek.character.v1', kind: 'agent.activity', source: 'hermes-adapter',
    audience: 'public', sensitivity: 'public', seq, observedAt: new Date().toISOString(), ttlMs: 2500,
    payload: {title: 'Furb-o-Mek', summary, status, tool: 'AGENT'}});
}
function runFixture() {
  window.FurbomekAvatar.apply_event(fixtureEvent(1, 'Fixture: preparing a response', 'thinking'));
  setTimeout(() => window.FurbomekAvatar.apply_event(fixtureEvent(2, 'Fixture: response cancelled', 'interrupted')), 1500);
  // No further events: after expiry the unchanged character shows honest offline state.
}
if (document.querySelector('#character').complete) runFixture();
else document.querySelector('#character').addEventListener('load', runFixture, {once: true});
