'use strict';
// Pure view factory: no live renderer instance is published on window.
(function (root) {
  function createView({document, window, fixture = false, onReady = () => {}}) {
    const stage = document.querySelector('#avatar');
    const avatar = root.FurbomekStatic.createAdapter({fixture, render(state) {
      stage.hidden = !state.visible;
      document.querySelector('#title').textContent = state.title;
      document.querySelector('#caption').textContent = state.caption;
      document.querySelector('#status').textContent = state.status;
      document.querySelector('#mode').textContent = state.fixture ? 'FIXTURE · NOT LIVE' : 'STATIC FALLBACK';
      stage.dataset.state = state.state;
    }});
    const asset = document.querySelector('#character');
    let loaded = false;
    const load = () => {
      if (!loaded && avatar.load_character(root.FurbomekStatic.ASSET)) {
        loaded = true;
        onReady(avatar);
      }
    };
    asset.addEventListener('error', () => avatar.shutdown());
    asset.addEventListener('load', load, {once: true});
    if (asset.complete && asset.naturalWidth > 0) load();
    const timer = window.setInterval(() => avatar.tick(), 100);
    window.addEventListener('pagehide', () => { window.clearInterval(timer); avatar.shutdown(); }, {once: true});
  }
  root.FurbomekView = Object.freeze({createView});
})(globalThis);
