'use strict';
// Test-only opt-in page; exercises the same view factory without a global instance.
(() => {
  globalThis.FurbomekView.createView({document, window, fixture: true, onReady(avatar) {
    avatar.apply_event(JSON.stringify({schemaVersion: 'furbomek.character.v1', kind: 'agent.activity', source: 'hermes-adapter',
      audience: 'public', sensitivity: 'public', seq: 1, observedAt: new Date().toISOString(), ttlMs: 2500,
      payload: {title: 'Furb-o-Mek', summary: '<img src=x onerror=alert(1)>', status: 'idle', tool: 'AGENT'}}));
  }});
})();
