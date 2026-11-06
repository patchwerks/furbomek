/* Called only by the existing offline browser qualification worker. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
module.exports = async function runBuilder(page, evidence) {
  const id = name => page.getByTestId(name);
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'pack-builder-'));
  const cli = path.resolve(__dirname, '../../../tools/presentation-pack/cli.mjs');
  const command = (...args) => spawnSync(process.execPath, [cli, ...args], { encoding: 'utf8', timeout: 10000 });
  try {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.emulateMedia({ colorScheme: 'light' });
    // Track the real browser APIs, while preserving their behavior.
    await page.evaluate(() => {
      window.__builderUrls = [];
      window.__builderRevoked = [];
      const create = URL.createObjectURL.bind(URL), revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = blob => { const url = create(blob); window.__builderUrls.push(url); return url; };
      URL.revokeObjectURL = url => { window.__builderRevoked.push(url); return revoke(url); };
    });
    await id('build-mode').click();
    assert.equal(await id('pack-id').inputValue(), 'reaction-example', 'entry edits current pack');
    await id('preset-neutral').click();
    assert.equal(await page.locator('.cue-row').count(), 1);
    await id('preset-curious').click();
    assert.equal(await id('cue-1').locator('select').inputValue(), 'curious');
    await id('preset-acknowledge').click();
    assert.equal(await id('cue-1').locator('select').inputValue(), 'acknowledge');
    await id('edit-current').click();
    assert.equal(await id('pack-id').inputValue(), 'reaction-example');
    assert.equal(await id('cue-0').locator('input').isDisabled(), true);
    assert.equal(await id('cue-0').locator('select').isDisabled(), true);
    assert.equal(await id('cue-0').getByRole('button').count(), 0);
    await id('pack-id').fill('browser-authored');
    await id('pack-version').fill('1.2.3');
    await id('pack-duration').fill('5000');
    await id('cue-1').locator('input').fill('2000');
    await id('cue-2').locator('input').fill('2000');
    await id('cue-3').locator('input').fill('1000');
    await id('play-pause').click();
    await page.waitForFunction(() => Number(document.querySelector('[data-testid="position-ms"]').textContent) > 0);
    await id('pack-version').fill('1.2.4');
    assert.equal(await id('playback-state').textContent(), 'paused');
    assert.equal(await id('position-ms').textContent(), '0');
    await page.screenshot({ animations: 'disabled', path: path.join(evidence, 'builder-light.png'), fullPage: true });
    await id('pack-id').fill('../invalid');
    assert.equal(await id('export-pack').isDisabled(), true);
    assert.equal(await id('play-pause').isDisabled(), true);
    assert.equal(await id('event-list').count(), 0, 'invalid draft removes stale events');
    assert.equal(await id('pack-name').count(), 0, 'invalid draft removes stale identity');
    assert.match(await id('builder-error').textContent(), /packId/);
    await page.screenshot({ animations: 'disabled', path: path.join(evidence, 'builder-error.png'), fullPage: true });
    await id('pack-id').fill('browser-authored');
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.screenshot({ animations: 'disabled', path: path.join(evidence, 'builder-dark.png'), fullPage: true });
    const downloadPromise = page.waitForEvent('download');
    await id('export-pack').click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), 'browser-authored.json');
    const file = path.join(scratch, download.suggestedFilename());
    await download.saveAs(file);
    assert.equal(await download.failure(), null);
    const actual = fs.readFileSync(file), data = JSON.parse(actual.toString('utf8'));
    assert.deepEqual(data.events.map(event => [event.seq, event.atMs, event.value]), [[1, 0, 'neutral'], [2, 1000, 'neutral'], [3, 2000, 'curious'], [4, 2000, 'acknowledge']]);
    assert.equal(data.packVersion, '1.2.4');
    assert.equal(data.durationMs, 5000);
    assert.equal(Object.keys(data).length, 7);
    await page.waitForFunction(() => window.__builderUrls.length === 1 && window.__builderRevoked.includes(window.__builderUrls[0]));
    const validate = command('validate', file, '--json');
    assert.equal(validate.status, 0, validate.stderr || validate.stdout);
    const template = command('template', file, '--author', 'Browser test contributor', '--license', 'MIT');
    assert.equal(template.status, 0, template.stderr);
    const metadata = path.join(scratch, 'companion.json');
    fs.writeFileSync(metadata, template.stdout);
    const matched = command('validate', file, '--metadata', metadata, '--json');
    assert.equal(matched.status, 0, matched.stderr || matched.stdout);
    fs.appendFileSync(file, ' ');
    assert.equal(command('validate', file, '--metadata', metadata, '--json').status, 1, 'same parsed pack with changed exact bytes rejects old digest');
    fs.writeFileSync(file, actual);
    await id('preview-mode').click();
    await id('import-file').setInputFiles(file);
    await page.waitForFunction(() => document.querySelector('[data-testid="pack-name"]')?.textContent === 'browser-authored.json');
    assert.equal(await id('play-pause').isEnabled(), true);
    await id('build-mode').click();
    await id('preset-neutral').click();
    for (let i = 1; i < 64; i++) await id('add-cue').click();
    assert.equal(await page.locator('.cue-row').count(), 64);
    assert.equal(await id('add-cue').isDisabled(), true);
    await page.getByRole('button', { name: 'Remove cue 64', exact: true }).click();
    assert.equal(await id('add-cue').isEnabled(), true);
    const accessibilityCases = await checkBuilderAccessibility(page);
    await id('preset-curious').click();
    await page.setViewportSize({ width: 390, height: 844 });
    await id('pack-id').focus();
    await page.keyboard.press('Tab');
    assert.equal(await id('pack-version').evaluate(element => document.activeElement === element && element.matches(':focus-visible')), true);
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.type('2.0.0');
    await page.keyboard.press('Tab');
    assert.equal(await id('pack-duration').evaluate(element => document.activeElement === element), true);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'builder has no mobile horizontal overflow');
    await page.screenshot({ animations: 'disabled', path: path.join(evidence, 'builder-mobile.png'), fullPage: true });
    await id('pack-duration').fill('1');
    assert.equal(await id('export-pack').isDisabled(), true);
    await id('preview-mode').click();
    assert.equal(await id('play-pause').isDisabled(), true, 'leaving invalid draft cannot restore stale authority');
    return ['builder-presets', 'builder-edit-current', 'builder-locked-reset', 'builder-valid-edit-pauses', 'builder-invalid-clears', 'builder-real-download', 'builder-reimport', 'builder-cli-metadata-roundtrip', 'builder-exact-byte-tamper', 'builder-url-revocation', 'builder-cue-cap-removal', 'builder-keyboard-mobile', ...accessibilityCases];
  } finally { fs.rmSync(scratch, { recursive: true, force: true }); }
};


async function checkBuilderAccessibility(page) {
  const id = name => page.getByTestId(name);
  const time = index => id(`cue-${index}`).locator('input');
  const value = index => id(`cue-${index}`).locator('select');
  const focused = locator => locator.evaluate(element => document.activeElement === element);
  // Reach controls only through native Tab. No scripted focus or click fallback.
  const tabTo = async (locator, direction = 'Tab') => {
    for (let i = 0; i < 40; i++) {
      if (await focused(locator)) return;
      await page.keyboard.press(direction);
    }
    assert.fail(`Native ${direction} could not reach builder control`);
  };
  await id('preset-neutral').click();
  await id('pack-duration').fill('5000');
  await tabTo(id('add-cue'));
  await page.keyboard.press('Enter');
  assert.equal(await focused(time(1)), true, 'added cue receives time focus');
  // Replace the value using native editing so append-vs-selection is immaterial.
  await page.keyboard.press('ControlOrMeta+A');
  await page.keyboard.type('1200');
  await tabTo(id('add-cue'));
  await page.keyboard.press('Space');
  assert.equal(await focused(time(2)), true, 'Space adds and focuses new cue');
  await page.keyboard.press('ControlOrMeta+A');
  await page.keyboard.type('2200');
  await page.keyboard.press('Tab');
  assert.equal(await focused(value(2)), true);
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  assert.equal(await value(2).inputValue(), 'acknowledge');
  // Removing another row must preserve this exact surviving DOM node and focus.
  await page.keyboard.press('Shift+Tab');
  await value(2).evaluate(element => { window.__survivingCueValue = element; });
  await id('cue-1').getByRole('button').evaluate(element => element.click());
  assert.equal(await value(1).evaluate(element => element === window.__survivingCueValue && document.activeElement === element), true);
  assert.equal(await value(1).inputValue(), 'acknowledge');
  assert.equal(await time(1).inputValue(), '2200');
  await tabTo(id('add-cue'));
  await page.keyboard.press('Enter');
  await tabTo(id('cue-1').getByRole('button'), 'Shift+Tab');
  await page.keyboard.press('Enter');
  assert.equal(await focused(time(1)), true, 'delete focuses next surviving editable cue');
  await tabTo(id('add-cue'));
  await page.keyboard.press('Enter');
  await tabTo(id('cue-2').getByRole('button'));
  await page.keyboard.press('Space');
  assert.equal(await focused(time(1)), true, 'delete last editable cue focuses previous');
  await tabTo(id('cue-1').getByRole('button'));
  await page.keyboard.press('Enter');
  assert.equal(await focused(id('add-cue')), true, 'delete only editable cue focuses Add');
  await page.keyboard.press('Enter');
  const associations = await page.locator('.builder input, .builder select').evaluateAll(elements => elements.map(element => ({
    id: element.id, labels: Array.from(element.labels || []).map(label => label.textContent.trim()),
    descriptions: (element.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean).map(id => ({ id, present: !!document.getElementById(id) })),
  })));
  for (const field of associations) {
    assert.ok(field.id && field.labels.length === 1 && field.labels[0], `explicit label: ${JSON.stringify(field)}`);
    assert.ok(field.descriptions.some(item => item.id === 'builder-error'), `error association: ${field.id}`);
    assert.ok(field.descriptions.every(item => item.present), `description target: ${field.id}`);
  }
  await page.evaluate(associations => { window.__builderAccessibility = { associations, reflow: [] }; }, associations);
  const alert = id('builder-error'), status = page.locator('.builder [role="status"]');
  assert.equal(await alert.getAttribute('role'), 'alert');
  assert.equal(await alert.getAttribute('aria-atomic'), 'true');
  assert.equal(await status.getAttribute('aria-atomic'), 'true');
  await page.evaluate(() => {
    window.__builderLive = { alert: document.querySelector('[data-testid="builder-error"]'), status: document.querySelector('.builder [role="status"]'), mutations: [] };
    window.__builderLive.observer = new MutationObserver(records => {
      for (const record of records) {
        const live = window.__builderLive;
        const region = record.target === live.alert || live.alert.contains(record.target) ? 'alert' : 'status';
        if (live.mutations.length < 20) live.mutations.push({ region, text: live[region].textContent });
      }
    });
    for (const region of ['alert', 'status']) window.__builderLive.observer.observe(window.__builderLive[region], { childList: true, characterData: true, subtree: true });
  });
  await id('pack-id').fill('../invalid');
  await page.waitForFunction(() => window.__builderLive.mutations.some(item => item.region === 'alert' && /packId/.test(item.text)));
  assert.equal(await status.textContent(), '');
  await id('pack-id').fill('accessible-draft');
  await page.waitForFunction(() => window.__builderLive.mutations.some(item => item.region === 'status' && /Valid draft/.test(item.text)));
  assert.equal(await alert.textContent(), '');
  assert.equal(await page.evaluate(() => window.__builderLive.alert === document.querySelector('[data-testid="builder-error"]') && window.__builderLive.status === document.querySelector('.builder [role="status"]')), true, 'live region nodes persist through validation');
  await page.evaluate(() => { window.__builderLive.observer.disconnect(); window.__builderAccessibility.liveMutations = window.__builderLive.mutations; });
  // CSS viewport equivalents for 1280px at 200%/400%, not actual browser zoom.
  for (const width of [640, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const reflow = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
    await page.evaluate(result => window.__builderAccessibility.reflow.push(result), reflow);
    assert.ok(reflow.scrollWidth <= reflow.width, `reflow at ${width} CSS px`);
    const controls = [time(1), value(1), id('add-cue'), id('export-pack')];
    for (let index = 0; index < controls.length; index++) {
      const locator = controls[index];
      await tabTo(locator, width === 320 && index === 0 ? 'Shift+Tab' : 'Tab');
      assert.equal(await locator.evaluate(element => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.left >= 0 && rect.right <= innerWidth && element.matches(':focus-visible');
      }), true, `visible usable keyboard control at ${width} CSS px`);
    }
  }
  return ['builder-keyboard-add-focus', 'builder-remove-other-retains-identity', 'builder-keyboard-delete-next', 'builder-keyboard-delete-previous', 'builder-keyboard-delete-add', 'builder-field-label-associations', 'builder-alert-status-mutations', 'builder-reflow-200-percent-equivalent', 'builder-reflow-400-percent-equivalent'];
}
