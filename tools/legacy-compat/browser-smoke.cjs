// Run inside a worker that denies external network and device access.
// Playwright is external test tooling, not an application dependency.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const providerFixtures = {
  'https://api.openai.com/v1/assistants': {object: 'list', data: [], has_more: false},
  'http://localhost:3500/proxy/elevenlabs/voices': {voices: []},
  'http://localhost:3500/proxy/elevenlabs/subscription': {character_count: 0, character_limit: 1},
  'http://localhost:3500/proxy/playht/voices': [],
  'http://localhost:3500/proxy/playht/cloned-voices': [],
};

(async () => {
  const [htmlFile, publicDirectory] = process.argv.slice(2);
  assert(htmlFile && publicDirectory, 'usage: browser-smoke.cjs rendered.html public-directory');
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE ? {executablePath: process.env.CHROMIUM_EXECUTABLE} : {}),
    args: ['--disable-gpu', '--disable-background-networking'],
  });
  try {
    const page = await browser.newPage({serviceWorkers: 'block', viewport: {width: 1280, height: 720}});
    const pageErrors = [], externalRequests = [], fixtures = [], missingAssets = [], consoleErrors = [];
    const focusReturned = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== 'https://fixture.invalid') {
        const key = url.origin + url.pathname;
        if (key in providerFixtures) {
          assert.equal(route.request().method(), 'GET');
          const headers = route.request().headers();
          for (const name of ['authorization', 'xi-api-key', 'x-user-id']) {
            if (name in headers) assert.equal(headers[name].replace(/^Bearer\s*/, ''), '',
              'fixture credentials must be blank');
          }
          fixtures.push({method: route.request().method(), url: key});
          return route.fulfill({status: 200, contentType: 'application/json',
            body: JSON.stringify(providerFixtures[key])});
        }
        externalRequests.push(url.origin);
        return route.abort();
      }
      const target = url.pathname === '/' ? htmlFile : path.join(publicDirectory, url.pathname);
      if (!fs.existsSync(target)) {
        missingAssets.push(url.pathname);
        return route.fulfill({status: 404, body: 'Not found'});
      }
      const contentTypes = {'.html': 'text/html', '.js': 'text/javascript',
        '.css': 'text/css', '.json': 'application/json'};
      return route.fulfill({status: 200,
        contentType: contentTypes[path.extname(target)] || 'application/octet-stream',
        body: fs.readFileSync(target)});
    });
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
      Object.defineProperty(navigator, 'mediaDevices', {value: {
        getUserMedia: async () => new MediaStream(), enumerateDevices: async () => [],
      }});
      window.AudioContext = class {
        createMediaStreamSource() { return {connect() {}}; }
        createAnalyser() { return {frequencyBinCount: 128, getByteFrequencyData(data) {data.fill(0);}}; }
      };
      window.WebSocket = class { constructor() {throw Error('WebSocket blocked');} };
    });
    await page.goto('https://fixture.invalid/');
    const settings = page.getByRole('button', {name: 'Settings', exact: true});
    await settings.waitFor();
    const send = page.getByRole('button', {name: 'Send', exact: true});
    assert(await send.isDisabled());
    await page.getByPlaceholder('Write your message here...').fill('offline fixture');
    assert(await send.isDisabled());
    const toggle = page.locator('.toggle-button');
    const previousMode = await toggle.textContent();
    await toggle.click();
    assert.notEqual(await toggle.textContent(), previousMode);
    assert(await send.isDisabled());

    const modal = page.locator('#settings-modal');
    const number = page.locator('#settings-modal input[type="number"]').first();
    for (const value of ['900', '1200']) {
      await settings.click();
      await modal.waitFor({state: 'visible'});
      for (const name of ['OpenAI', 'Deepgram', '11labs', 'Play.ht']) {
        const tab = page.getByRole('tab', {name, exact: true});
        await tab.click();
        assert.equal(await tab.getAttribute('aria-selected'), 'true');
      }
      const dialog = await modal.locator('.modal-dialog').boundingBox();
      assert(dialog && (5 < dialog.x || 5 < dialog.y), 'backdrop point must be outside dialog');
      await page.mouse.click(5, 5);
      await page.waitForTimeout(400);
      assert(await modal.isVisible(), 'noCloseOnBackdrop must remain effective');
      await page.getByRole('tab', {name: 'Deepgram', exact: true}).click();
      if (value === '1200') assert.equal(await number.inputValue(), '900');
      await number.fill(value);
      await page.waitForFunction(expected =>
        JSON.parse(localStorage.getItem('settings')).deepgram.utterance === expected, Number(value));
      await page.locator('#settings-modal .btn-close').click();
      await modal.waitFor({state: 'hidden'});
      focusReturned.push(await settings.evaluate(element => element === document.activeElement));
    }
    assert.deepEqual(externalRequests, []);
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(missingAssets, []);
    assert.deepEqual(consoleErrors, []);
    console.log(JSON.stringify({result: 'PASS',
      checks: ['SPA mount', 'blank-provider send guards', 'message input', 'USER/bot toggle',
        'modal open/close/reopen', 'all four tabs', 'backdrop dismissal disabled', 'repeated persisted form edits'],
      unmockedExternalRequests: externalRequests, localProviderFixtures: fixtures,
      pageErrors, consoleErrors, missingAssets, focusReturned}));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
