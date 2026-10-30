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
  'http://localhost:3500/proxy/playht/voices': [{id: 'fixture-voice', name: 'Offline fixture', voice_engine: 'PlayHT2.0'}],
  'http://localhost:3500/proxy/playht/stream': {error_id: 'OUT_OF_CREDITS'},
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
      if (message.type() === 'error' && !(message.location().url === 'http://localhost:3500/proxy/playht/stream' && message.text().includes('403'))) consoleErrors.push(message.text());
    });
    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== 'https://fixture.invalid') {
        const key = url.origin + url.pathname;
        if (key in providerFixtures) {
          const creditFixture = key.endsWith('/playht/stream');
          assert.equal(route.request().method(), creditFixture ? 'POST' : 'GET');
          const headers = route.request().headers();
          for (const name of ['authorization', 'xi-api-key', 'x-user-id']) {
            if (name in headers) assert.equal(headers[name].replace(/^Bearer\s*/, ''), '',
              'fixture credentials must be blank');
          }
          fixtures.push({method: route.request().method(), url: key});
          return route.fulfill({status: creditFixture ? 403 : 200, contentType: 'application/json',
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
        close() {}
        async suspend() {}
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
    // BModal activates its focus trap after the enter transition, later than
    // visibility. Interacting earlier changes the trap's captured return target.
    const waitForSettingsFocus = () => page.waitForFunction(() =>
      document.activeElement === document.querySelector('#settings-modal'));
    const waitForReturnedFocus = () => page.waitForFunction(() =>
      [...document.querySelectorAll('button')].some(button =>
        button.textContent.trim() === 'Settings' && button === document.activeElement));
    const number = page.locator('#settings-modal input[type="number"]').first();
    for (const value of ['900', '1200']) {
      await settings.click();
      await modal.waitFor({state: 'visible'});
    await waitForSettingsFocus();
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
      await waitForReturnedFocus();
      focusReturned.push(await settings.evaluate(element => element === document.activeElement));
    }
    // Repeated provider configuration edits must reach the parent's provider
    // watcher, not merely persist in localStorage. All requests stay local fixtures.
    await settings.click();
    await modal.waitFor({state: 'visible'});
    await waitForSettingsFocus();
    await page.getByRole('tab', {name: '11labs', exact: true}).click();
    const stability = page.locator('#settings-modal input[type="number"]:visible').first();
    for (const value of ['0.6', '0.7']) {
      const before = fixtures.filter(item => item.url.endsWith('/elevenlabs/voices')).length;
      await stability.fill(value);
      await page.waitForFunction(expected =>
        JSON.parse(localStorage.getItem('settings')).elevenlabs.stability === expected, Number(value));
      await page.waitForTimeout(300);
      assert(fixtures.filter(item => item.url.endsWith('/elevenlabs/voices')).length > before,
        'each provider settings edit must refresh fixture voices');
    }
    const screenshots = process.env.SCREENSHOT_DIRECTORY;
    if (screenshots) fs.mkdirSync(screenshots, {recursive: true});
    for (const width of [1280, 390]) {
      await page.setViewportSize({width, height: 844});
      await page.getByRole('tab', {name: 'Deepgram', exact: true}).click();
      await page.waitForTimeout(400);
      await number.waitFor({state: 'visible'});
      if (screenshots) await page.screenshot({path: path.join(screenshots, `settings-${width}.png`)});
      const footerButton = modal.locator('.modal-footer button').last();
      await footerButton.scrollIntoViewIfNeeded();
      const footerBox = await footerButton.boundingBox();
      assert(footerBox && footerBox.y >= 0 && footerBox.y + footerBox.height <= 844,
        'modal footer must be reachable inside viewport');
      if (screenshots) await page.screenshot({path: path.join(screenshots, `settings-${width}-bottom.png`)});
      await page.locator('#settings-modal .btn-close').scrollIntoViewIfNeeded();
      await page.locator('#settings-modal .btn-close').focus();
      await page.keyboard.press('Tab');
      assert(await modal.evaluate(element => element.contains(document.activeElement)),
        'keyboard focus must stay inside settings modal');
    }
    await page.keyboard.press('Escape');
    await modal.waitFor({state: 'hidden'});
    await page.waitForTimeout(400);
    await waitForReturnedFocus();
    const escapeFocus = await settings.evaluate(element => ({returned: element === document.activeElement,
      activeTag: document.activeElement?.tagName, activeText: document.activeElement?.textContent?.slice(0, 60)}));
    await settings.focus();
    await page.keyboard.press('Enter');
    await modal.waitFor({state: 'visible'});
    await waitForSettingsFocus();
    await page.locator('#settings-modal .btn-close').focus();
    await page.keyboard.press('Enter');
    await modal.waitFor({state: 'hidden'});
    await waitForReturnedFocus();
    // Synthetic provider error only: the request never leaves route interception.
    await page.setViewportSize({width: 1280, height: 844});
    const fixtureVoice = page.locator('select').filter({has: page.locator('option', {hasText: 'Offline fixture'})});
    await fixtureVoice.selectOption({label: 'Offline fixture'});
    await toggle.click(); // Return to the original bot input mode.
    const warning = page.locator('#warning-modal');
    for (const width of [1280, 390]) {
      await page.setViewportSize({width, height: 844});
      await page.getByPlaceholder('Write your message here...').fill('Offline warning fixture.');
      await send.click();
      await warning.waitFor({state: 'visible'});
      await page.waitForTimeout(400);
      assert(await warning.getByText('PlayHT API is out of credits.', {exact: false}).isVisible());
      const warningBox = await warning.locator('.modal-dialog').boundingBox();
      assert(warningBox && warningBox.width <= width, 'warning default size fits viewport');
      if (width === 1280) assert(warningBox.width <= 500, 'warning uses default medium width');
      await page.mouse.click(2, 2);
      assert(await warning.isVisible(), 'warning backdrop dismissal stays disabled');
      if (screenshots) await page.screenshot({path: path.join(screenshots, `warning-${width}.png`)});
      await page.keyboard.press('Escape');
      await warning.waitFor({state: 'hidden'});
    }
    assert.equal(fixtures.filter(item => item.url.endsWith('/playht/stream')).length, 2);
    assert.deepEqual(externalRequests, []);
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(missingAssets, []);
    assert.deepEqual(consoleErrors, []);
    console.log(JSON.stringify({result: 'PASS',
      checks: ['SPA mount', 'blank-provider send guards', 'message input', 'USER/bot toggle',
        'modal open/close/reopen', 'all four tabs', 'backdrop dismissal disabled', 'repeated persisted form edits',
        'repeated provider watcher callbacks', 'desktop/mobile modal and reachable footer', 'synthetic out-of-credits warning default size/backdrop/Escape/reopen', 'keyboard open/close/Escape and transition-settled focus return'],
      unmockedExternalRequests: externalRequests, localProviderFixtures: fixtures,
      pageErrors, consoleErrors, missingAssets, focusReturned, escapeFocus}));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
