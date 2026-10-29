/* Static, read-only implementation of PLAN §6.5. No transport or control plane. */
(function (root) {
  'use strict';
  const ASSET = 'furbomek-static-plate-v1';
  const MAX_BYTES = 8192;
  const text = (value, min, max) => {
    if (typeof value !== 'string') return false;
    const length = [...value].length; // Match the Python producer's Unicode codepoint bounds.
    return length >= min && length <= max;
  };
  const integer = value => Number.isSafeInteger(value) && value >= 0;

  function project(raw, now) {
    if (typeof raw !== 'string' || new TextEncoder().encode(raw).length > MAX_BYTES) return null;
    let event;
    try { event = JSON.parse(raw); } catch { return null; }
    if (!event || event.schemaVersion !== 'furbomek.character.v1' || event.kind !== 'agent.activity' ||
        event.source !== 'hermes-adapter' || event.audience !== 'public' || event.sensitivity !== 'public' ||
        !integer(event.seq) || !integer(event.ttlMs) || event.ttlMs < 1 || event.ttlMs > 30000 ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(event.observedAt)) return null;
    const at = Date.parse(event.observedAt);
    if (!Number.isFinite(at) || new Date(at).toISOString() !== event.observedAt || at > now || now >= at + event.ttlMs) return null;
    const p = event.payload;
    if (!p || !text(p.title, 1, 180) || !text(p.summary, 0, 180) || !text(p.status, 1, 24) || !text(p.tool, 1, 12)) return null;
    // Screen metadata, filenames, timeline and any future fields are never rendered.
    return {seq: event.seq, expires: at + event.ttlMs, title: p.title, summary: p.summary, status: p.status};
  }

  function createAdapter({render, now = Date.now, fixture = false}) {
    if (typeof render !== 'function') throw new TypeError('render is required');
    let loaded = false, visible = true, stopped = false, latest = null, lastSeq = -1, clockHighWater = -1;
    const capabilities = () => Object.freeze({version: 1, assets: [ASSET], formats: ['svg'], expressions: [], visemes: [], audio: false, capture: 'transparent-browser', transport: 'none'});
    const readClock = () => {
      const current = now();
      // Fail closed until wall time catches up; retaining the sequence prevents replay.
      if (!integer(current) || current < clockHighWater) { latest = null; return null; }
      clockHighWater = current;
      return current;
    };
    const snapshot = () => {
      const current = readClock();
      if (latest !== null && (current === null || current >= latest.expires)) latest = null;
      const fresh = latest !== null;
      return Object.freeze({asset: loaded ? ASSET : null, visible: visible && loaded && !stopped,
        fixture, state: stopped ? 'offline' : fresh ? 'present' : 'offline',
        title: fresh && !stopped ? latest.title : 'Furb-o-Mek',
        caption: fresh && !stopped ? latest.summary : 'Activity unavailable',
        status: fresh && !stopped ? latest.status : 'offline', seq: lastSeq});
    };
    const paint = () => { const state = snapshot(); render(state); return state; };
    function apply(raw) {
      if (stopped || !loaded) return false;
      const current = readClock();
      if (current === null) { paint(); return false; }
      const value = project(raw, current);
      if (!value || value.seq <= lastSeq) return false;
      latest = value; lastSeq = value.seq; paint(); return true;
    }
    return Object.freeze({
      capabilities,
      health: () => stopped || !loaded ? 'failed' : snapshot().state === 'offline' ? 'degraded' : 'ready',
      load_character: id => { if (stopped || id !== ASSET) return false; loaded = true; paint(); return true; },
      apply_snapshot: apply,
      apply_event: apply,
      set_visible: value => { if (stopped || typeof value !== 'boolean') return false; visible = value; paint(); return true; },
      snapshot,
      tick: paint,
      shutdown: () => { stopped = true; latest = null; paint(); }
    });
  }
  root.FurbomekStatic = Object.freeze({ASSET, createAdapter});
  if (typeof module !== 'undefined') module.exports = root.FurbomekStatic;
})(globalThis);
