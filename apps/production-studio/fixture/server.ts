import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { z } from 'zod';
import { writeSchema } from '../src/model.ts';
import { FixtureError } from './semantic.ts';
import { openStore } from './store.ts';
const dist = new URL('../dist/', import.meta.url).pathname;
export async function startFixture(file: string, port = 0) {
  const store = await openStore(file);
  const server = createServer(async (req, res) => {
    const host = `127.0.0.1:${port}`;
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Content-Security-Policy', "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'");
    try {
      if (req.headers.host !== host) throw new FixtureError(403, 'Loopback host required');
      const url = new URL(req.url ?? '/', `http://${host}`);
      if (url.pathname.startsWith('/fixture/')) {
        res.setHeader('Content-Type', 'application/json');
        if (req.method === 'GET' && url.pathname === '/fixture/state') { res.end(JSON.stringify(store.read())); return; }
        if (req.method !== 'POST') throw new FixtureError(405, 'POST required');
        if (req.headers.origin !== `http://${host}` || req.headers['content-type'] !== 'application/json') throw new FixtureError(403, 'Same-origin JSON required');
        let data = '';
        for await (const chunk of req) { data += String(chunk); if (Buffer.byteLength(data) > 65536) throw new FixtureError(413, 'Request exceeds fixture limit'); }
        const body = writeSchema.parse(JSON.parse(data));
        const result = await store.mutate(url.pathname.slice('/fixture/'.length), body);
        res.end(JSON.stringify(result)); return;
      }
      if (req.method !== 'GET') throw new FixtureError(405, 'GET required');
      const path = resolve(dist, url.pathname === '/' ? 'index.html' : `.${url.pathname}`);
      if (!path.startsWith(dist)) throw new FixtureError(403, 'Path refused');
      const content = await readFile(path);
      res.setHeader('Content-Type', ({ '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.ttf':'font/ttf' }[extname(path)] ?? 'application/octet-stream'));
      res.end(content);
    } catch (error) {
      if (error instanceof FixtureError) { res.statusCode = error.status; res.end(JSON.stringify({ error: error.message })); }
      else if (error instanceof z.ZodError || error instanceof SyntaxError) { res.statusCode = 422; res.end(JSON.stringify({ error: 'Invalid typed fixture input' })); }
      else if (error instanceof Error && 'code' in error && error.code === 'ENOENT') { res.statusCode = 404; res.end('Not found'); }
      else { res.statusCode = 500; res.end(JSON.stringify({ error: 'Fixture operation failed' })); console.error(error); }
    }
  });
  await new Promise<void>((accept, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => { server.off('error', reject); accept(); });
  });
  const address = server.address();
  if (!address || typeof address === 'string') throw new FixtureError(500, 'Missing loopback address');
  port = address.port;
  return { url: `http://127.0.0.1:${port}/?mode=fixture`, close: () => new Promise<void>((accept, reject) => { server.close(error => error ? reject(error) : accept()); server.closeAllConnections(); }) };
}
