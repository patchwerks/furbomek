'use strict';
// Explicit separate fixture entrypoint. Never imported by the normal fallback.
(() => {
  function fixtureEvent(seq, summary, status) {
    return JSON.stringify({schemaVersion: 'furbomek.character.v1', kind: 'agent.activity', source: 'hermes-adapter',
      audience: 'public', sensitivity: 'public', seq, observedAt: new Date().toISOString(), ttlMs: 2500,
      payload: {title: 'Furb-o-Mek', summary, status, tool: 'AGENT'}});
  }
  FurbomekView.createView({document, window, fixture: true, onReady(avatar) {
    avatar.apply_event(fixtureEvent(1, 'Fixture: preparing a response', 'thinking'));
    const timer = window.setTimeout(() => avatar.apply_event(fixtureEvent(2, 'Fixture: response cancelled', 'interrupted')), 1500);
    window.addEventListener('pagehide', () => window.clearTimeout(timer), {once: true});
    // No further events: expiry returns to the honest offline state.
  }});
})();
