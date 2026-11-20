import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { existsSync } from 'node:fs';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { once } from 'node:events';
import { pathToFileURL } from 'node:url';
const evidence = process.env.STUDIO_EVIDENCE_DIR;
const skill = process.env.OMO_BROWSER_SKILL;
if (!evidence || !skill) throw new Error('Set STUDIO_EVIDENCE_DIR and OMO_BROWSER_SKILL');
await mkdir(evidence, { recursive: true });
const gateway = resolve('services/embodiment-gateway');
const token = randomBytes(32).toString('hex');
const child = spawn(join(gateway, '.venv/bin/python'), ['-m', 'tests.production_http_fixture_server'], { cwd: gateway, env: { ...process.env, TASK24_FIXTURE_BOOTSTRAP: token }, stdio: ['pipe', 'pipe', 'pipe'] });
let stderr = ''; child.stderr.on('data', data => { stderr += data.toString(); });
const lines = createInterface({ input: child.stdout });
async function line() { return Promise.race([once(lines, 'line').then(([value]) => value), once(child, 'exit').then(() => { throw new Error(`Fixture exited: ${stderr}`); })]); }
const origin = await line();
assert.match(origin, /^http:\/\/127\.0\.0\.1:\d+$/);
const { loadOmowright } = await import(pathToFileURL(join(skill, 'scripts/omowright.mjs')).href);
const { omowright } = await loadOmowright();
const profile = await mkdtemp(join(tmpdir(), 'owner-http-browser-'));
let browser;
const happy = []; const failure = []; const shots = []; const detects = [];
const detect = process.env.STUDIO_DETECT_MODULE ? await import(pathToFileURL(process.env.STUDIO_DETECT_MODULE).href) : null;
try {
  browser = await omowright.connectPipe({ browserPath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', browserArgs: ['--headless', '--no-first-run', `--user-data-dir=${profile}`], storageRoot: profile });
  const page = await browser.newTab(`${origin}/?mode=live`);
  const snapshot = async () => omowright.compactSnapshot(await page.snapshot());
  async function ref(kind, label) {
    const tree = await snapshot();
    const match = tree.split('\n').find(row => row.includes(`${kind} "`) && row.includes(label))?.match(/\[ref=(\w+)\]/);
    assert.ok(match, `Missing ${kind} ${label}\n${tree}`); return match[1];
  }
  async function click(label) { await page.locator(await ref('button', label)).click(); }
  async function fill(label, value) { await page.locator(await ref('textbox', label)).fill(value); }
  async function until(text) {
    await page.evaluate(text => new Promise((resolve, reject) => {
      if (document.body.innerText.includes(text)) { resolve(true); return; }
      const timeout = setTimeout(() => { observer.disconnect(); reject(new Error(`Missing ${text}`)); }, 15000);
      const observer = new MutationObserver(() => { if (document.body.innerText.includes(text)) { clearTimeout(timeout); observer.disconnect(); resolve(true); } });
      observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true });
    }), text);
  }
  async function control(command) { const ack = line(); child.stdin.write(`${command}\n`); assert.equal(await ack, 'updated'); }
  async function shot(name) { const path = join(evidence, `${name}.png`); await writeFile(path, await page.screenshot()); shots.push(path); }
  await shot('live-login');
  await fill('Local bootstrap credential', token);
  await click('Authenticate'); await until('Controller connected');
  assert.ok((await snapshot()).includes('Injected test fixture controller'));
  assert.equal(await page.evaluate(() => document.querySelector('input[type=password]') === null), true);
  await fill('Intensity · 0–100%', '37');
  await click('Preview effect'); await until('Controller receipt: previewed');
  await click('Apply effect'); await until('Controller receipt: applied');
  const observed = await page.evaluate(async () => { const response = await fetch('/api/production/status', { headers: { 'X-Owner-Request': '1' } }); return response.json(); });
  assert.equal(observed.revision, 1); assert.equal(observed.applied.intensity_percent, 37); assert.equal(observed.receipt.effective.intensity_percent, 37);
  happy.push({ scenario: 'Local owner login, preview and apply through real HTTP', observable: { revision: observed.revision, intensity_percent: observed.applied.intensity_percent, receipt_status: observed.receipt.status }, passed: true, scope: 'explicit injected controller, no live runtime' });
  await click('Save preset'); await until('Controller receipt: saved');
  await click('Reconnect'); await until('Controller connected');
  const saved = await page.evaluate(async () => { const response = await fetch('/api/production/status', { headers: { 'X-Owner-Request': '1' } }); return response.json(); });
  assert.equal(saved.saved.effect.intensity_percent, 37);
  happy.push({ scenario: 'Save and authenticated read-only reconnect', observable: { revision: saved.revision, saved_intensity: saved.saved.effect.intensity_percent }, passed: true });
  await fill('Point size · pixels', '2.1');
  await fill('View zoom', '1.2');
  await click('Preview visual settings'); await until('Controller receipt: previewed');
  await click('Apply visual settings'); await until('Controller receipt: applied');
  const visualState = await page.evaluate(async () => { const response = await fetch('/api/production/status', { headers: { 'X-Owner-Request': '1' } }); return response.json(); });
  assert.equal(visualState.visual.point_pixels, 2.1); assert.equal(visualState.visual.zoom, 1.2);
  await fill('Crop width', '.8');
  await click('Preview framing'); await until('Controller receipt: previewed');
  await click('Apply framing'); await until('Controller receipt: applied');
  await click('Save framing preset'); await until('Controller receipt: saved');
  const framed = await page.evaluate(async () => { const response = await fetch('/api/production/status', { headers: { 'X-Owner-Request': '1' } }); return response.json(); });
  assert.equal(framed.framing.shots[0].target.roi.width, .8);
  happy.push({ scenario: 'Advanced visual and framing drafts survive typed HTTP preview/apply/save', observable: { point_pixels: visualState.visual.point_pixels, zoom: visualState.visual.zoom, crop_width: framed.framing.shots[0].target.roi.width }, passed: true });
  for (const [width, height, theme] of [[1440, 900, 'light'], [1440, 900, 'dark'], [1920, 1080, 'light'], [1920, 1080, 'dark'], [320, 844, 'light'], [320, 844, 'dark'], [390, 844, 'light'], [390, 844, 'dark']]) {
    await page.setViewportSize({ width, height });
    await omowright.emulate(page, { width, height, deviceScaleFactor: width === 390 ? 3 : 1, mobile: width === 390, hasTouch: width === 390 });
    const current = await page.evaluate(() => document.querySelector('.app-shell')?.getAttribute('data-theme'));
    if (current !== theme) await click(`${theme === 'dark' ? 'Dark' : 'Light'} theme`);
    const size = await page.evaluate(() => ({ width: innerWidth, content: document.documentElement.scrollWidth }));
    assert.ok(size.content <= size.width, JSON.stringify(size));
    await page.evaluate(() => window.scrollTo(0, 0));
    if (detect) {
      const captured = await page.evaluate(`(${detect.collectPageSnapshot.toString()})(${JSON.stringify(detect.STYLE_PROPS)}, 5000)`);
      const findings = detect.lintSnapshot(captured, { config: { allowFonts: ['Ioskeley Mono', 'system-ui', 'sans-serif'] } });
      detects.push({ width, theme, findings });
      assert.equal(detect.hasFailures(findings), false, JSON.stringify(findings));
    }
    await shot(`live-${width}-${theme}`);
    for (const section of ['Visual settings', 'Framing settings']) {
      await page.evaluate(label => document.querySelector(`section[aria-label="${label}"]`)?.scrollIntoView(), section);
      await shot(`live-${width}-${theme}-${section.split(' ')[0]}`);
    }
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await shot(`live-${width}-${theme}-end`);
  }
  const noCsrf = await page.evaluate(async () => (await fetch('/api/production/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).status);
  assert.equal(noCsrf, 403);
  failure.push({ scenario: 'Browser cookie alone cannot mutate without CSRF', observable: { status: noCsrf }, passed: true });
  await click('Preview effect'); await until('Controller receipt: previewed');
  await control('override'); await click('Reconnect');
  assert.equal(await page.evaluate(() => Array.from(document.querySelectorAll('button')).find(button => button.textContent === 'Apply effect')?.disabled), true);
  failure.push({ scenario: 'External revision invalidates preview on refresh', observable: { apply_disabled: true }, passed: true });
  await control('held'); await click('Reconnect'); await until('Controller held');
  assert.equal(await page.evaluate(() => Array.from(document.querySelectorAll('button')).find(button => button.textContent === 'Apply effect')?.disabled), true);
  for (const label of ['Apply visual settings', 'Apply framing']) {
    assert.equal(await page.evaluate(label => Array.from(document.querySelectorAll('button')).find(button => button.textContent === label)?.disabled, label), true);
  }
  await click('Preview effect'); await until('Controller receipt: previewed');
  await shot('live-held'); failure.push({ scenario: 'Held controller permits typed preview and disables dispatch', observable: { apply_disabled: true, preview_accepted_without_dispatch: true }, passed: true });
  child.stdin.end('stop\n'); await once(child, 'exit');
  await click('Reconnect'); await until('Disconnected or invalid response');
  await shot('live-disconnected'); failure.push({ scenario: 'Server teardown shows disconnected and historical state', observable: { disconnected: true }, passed: true });
  await writeFile(join(evidence, 'detect.json'), JSON.stringify(detects, null, 2));
  await writeFile(join(evidence, 'happy-browser.json'), JSON.stringify({ passed: true, scenarios: happy, captures: shots }, null, 2));
  await writeFile(join(evidence, 'failure-browser.json'), JSON.stringify({ passed: true, scenarios: failure, captures: shots }, null, 2));
  console.log(JSON.stringify({ happy: happy.length, failure: failure.length, captures: shots.length, teardown: 'server stopped; browser closes in finally' }));
} finally {
  if (browser) await browser.close();
  if (child.exitCode === null) { child.stdin.end('stop\n'); await once(child, 'exit'); }
  lines.close(); await rm(profile, { recursive: true, force: true });
}

assert.equal(child.exitCode, 0);
assert.equal(existsSync(profile), false);
await writeFile(join(evidence, 'cleanup-live.json'), JSON.stringify({ serverExited: child.exitCode === 0, browserCloseCompleted: true, temporaryProfileRemoved: !existsSync(profile), source: 'awaited finally cleanup plus post-cleanup assertions' }, null, 2));
