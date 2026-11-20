import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as wait } from 'node:timers/promises';

const profile = await mkdtemp(join(tmpdir(), 'furbomek-browser-'));
const chrome = spawn('/usr/bin/google-chrome', [
  ...(process.argv.includes('--headed') ? [] : ['--headless=new']),
  '--remote-debugging-address=127.0.0.1',
  '--remote-debugging-port=0',
  `--user-data-dir=${profile}`,
  '--window-size=960,540',
  '--no-first-run',
  '--no-default-browser-check',
  'about:blank',
], { stdio: 'ignore' });
const exited = once(chrome, 'exit');
let running = true;
let socket;
for (const signal of ['SIGINT', 'SIGTERM', 'SIGHUP']) {
  process.once(signal, () => { running = false; });
}
process.stdout.on('error', () => { running = false; });

const expires = Date.now() + 360_000;
const publicSite = page => page.type === 'page' && /^https:\/\/(www\.)?x\.com(?:\/|$)/.test(page.url);
let nextId = 0;

function command(method, params) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const activeSocket = socket;
    function finish(error, result) {
      clearTimeout(timer);
      activeSocket.removeEventListener('message', receive);
      if (error) reject(error);
      else resolve(result);
    }
    function receive(event) {
      const response = JSON.parse(event.data);
      if (response.id !== id) return;
      finish(response.error ? new Error(response.error.message) : null, response.result);
    }
    const timer = setTimeout(() => finish(new Error('Dedicated browser did not answer')), 3000);
    activeSocket.addEventListener('message', receive);
    activeSocket.send(JSON.stringify({ id, method, params }));
  });
}

try {
  let port;
  for (let attempt = 0; attempt < 60 && running; attempt++) {
    try {
      const manifest = await readFile(join(profile, 'DevToolsActivePort'), 'utf8');
      port = Number(manifest.split('\n')[0]);
      if (port > 0 && port < 65536) break;
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
    await wait(100);
  }
  if (!port || !running) throw new Error('Dedicated Chrome startup failed');
  process.stdout.write(`READY ${port}\n`);
  const list = async () => {
    const response = await fetch(`http://127.0.0.1:${port}/json/list`, {
      signal: AbortSignal.timeout(1800),
    });
    if (!response.ok) throw new Error('Could not read the dedicated tab list');
    return response.json();
  };
  let selected;
  while (running && Date.now() < expires) {
    const page = (await list()).find(publicSite);
    if (!page) {
      await wait(250);
      continue;
    }
    if (page.id !== selected || socket?.readyState !== WebSocket.OPEN) {
      socket?.close();
      socket = new WebSocket(page.webSocketDebuggerUrl);
      await new Promise((resolve, reject) => {
        socket.addEventListener('open', resolve, { once: true });
        socket.addEventListener('error', reject, { once: true });
      });
      await command('Emulation.setDeviceMetricsOverride', {
        width: 960, height: 540, deviceScaleFactor: 1, mobile: false,
      });
      selected = page.id;
    }
    const screenshot = await command('Page.captureScreenshot', {
      format: 'jpeg', quality: 76, fromSurface: true,
    });
    if ((await list()).some(current => current.id === selected && publicSite(current))) {
      if (!process.stdout.write(`${screenshot.data}\n`)) await once(process.stdout, 'drain');
    }
    await wait(100);
  }
} finally {
  socket?.close();
  if (chrome.exitCode === null) chrome.kill('SIGTERM');
  await Promise.race([exited, wait(2500)]);
  if (chrome.exitCode === null) chrome.kill('SIGKILL');
  await rm(profile, { recursive: true, force: true });
}
