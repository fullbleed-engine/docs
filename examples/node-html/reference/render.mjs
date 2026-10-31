// SPDX-License-Identifier: MIT
import { createServer } from 'node:http';
import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer';
import { digest, loadDocument, selectedDocuments } from '../document.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = resolve(process.argv[3] ?? join(root, 'output/chromium'));
await mkdir(output, { recursive: true });
const browser = await puppeteer.launch({
  headless: true,
  ...(process.env.FULLBLEED_CHROME_PATH ? { executablePath: process.env.FULLBLEED_CHROME_PATH } : {}),
  // This override is for an isolated CI runner rendering these trusted fixtures.
  ...(process.env.FULLBLEED_REFERENCE_NO_SANDBOX === '1' ? { args: ['--no-sandbox'] } : {}),
});
const documents = [];
try {
  for (const name of selectedDocuments(process.argv[2])) {
    const input = await loadDocument(name);
    const files = new Map([
      ['/document', ['text/html; charset=utf-8', Buffer.from(input.html)]],
      ...input.fonts.map(font => ['/' + font.name, ['font/ttf', font.data]]),
      ['/assets/logo.svg', ['image/svg+xml', input.assets['logo.svg']]],
    ]);
    const requests = [];
    const server = createServer((request, response) => {
      const file = files.get(request.url);
      if (request.method !== 'GET' || !file) { response.writeHead(404); response.end(); return; }
      response.writeHead(200, { 'Content-Type': file[0] }); response.end(file[1]);
    });
    await new Promise((accept, reject) => {
      server.once('error', reject); server.listen(0, '127.0.0.1', accept);
    });
    const origin = `http://127.0.0.1:${server.address().port}`;
    const page = await browser.newPage();
    try {
      await page.setRequestInterception(true);
      page.on('request', request => {
        const allowed = request.url().startsWith(origin + '/') && request.method() === 'GET';
        requests.push({ path: allowed ? request.url().slice(origin.length) : 'blocked-external-request', allowed });
        void (allowed ? request.continue() : request.abort());
      });
      await page.goto(origin + '/document', { waitUntil: 'networkidle0' });
      await page.evaluate(() => document.fonts.ready);
      const loaded = await page.evaluate(() => ({
        font: document.fonts.check('400 12px "Source Sans 3"') && document.fonts.check('700 12px "Source Sans 3"'),
        images: [...document.images].every(image => image.complete && image.naturalWidth > 0),
      }));
      if (!loaded.font || !loaded.images || requests.some(r => !r.allowed)) throw new Error('Reference assets failed to load locally.');
      const pdf = await page.pdf({ printBackground: true, preferCSSPageSize: true, tagged: false, outline: false });
      const folder = join(output, name);
      await mkdir(folder, { recursive: true });
      await writeFile(join(folder, 'input.html'), input.html);
      await writeFile(join(folder, 'document.pdf'), pdf);
      documents.push({ name, inputSha256: input.inputSha256, pdfSha256: digest(pdf),
        totalCents: input.totalCents, items: input.record.items.length, assetsLoaded: loaded, requests });
    } finally {
      await page.close();
      await new Promise((accept, reject) => {
        server.close(error => error ? reject(error) : accept());
        // Rendering is finished. Release unused browser connections as well;
        // Node 22's server.close() can otherwise keep waiting on preconnections.
        server.closeAllConnections();
      });
    }
  }
  const record = { node: process.version, browserVersion: await browser.version(), documents };
  await writeFile(join(output, 'render.json'), JSON.stringify(record, null, 2) + '\n');
  console.log(JSON.stringify(record));
} finally {
  await browser.close();
}
