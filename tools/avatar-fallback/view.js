'use strict';
const stage = document.querySelector('#avatar');
const fixture = document.body.dataset.fixture === 'true';
const avatar = FurbomekStatic.createAdapter({fixture, render(state) {
  stage.hidden = !state.visible;
  document.querySelector('#title').textContent = state.title;
  document.querySelector('#caption').textContent = state.caption;
  document.querySelector('#status').textContent = state.status;
  document.querySelector('#mode').textContent = state.fixture ? 'FIXTURE · NOT LIVE' : 'STATIC FALLBACK';
  stage.dataset.state = state.state;
}});
const asset = document.querySelector('#character');
asset.addEventListener('error', () => avatar.shutdown());
asset.addEventListener('load', () => avatar.load_character(FurbomekStatic.ASSET));
if (asset.complete && asset.naturalWidth > 0) avatar.load_character(FurbomekStatic.ASSET);
let timer = setInterval(() => avatar.tick(), 100);
window.FurbomekAvatar = avatar;
window.addEventListener('pagehide', () => { clearInterval(timer); timer = null; avatar.shutdown(); }, {once: true});
