// SPDX-License-Identifier: MIT
// Build actual downloadable projects and independent WASI reference outputs.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { join, relative } from 'node:path';
import { buildProject } from '../docs/assets/playground/project-export.js';
import { storeZip } from '../docs/assets/playground/zip-store.js';
import { render } from '../docs/assets/playground/renderer.js';
import { prepareExample } from '../docs/assets/playground/examples.js';
import { gradientFixtures, checkGradient } from './playground-fixtures/gradients.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const assets = join(root, 'docs/assets/playground');
const output = join(root, 'playground/project-verification');
await mkdir(output, { recursive: true });
const load = path => readFile(join(assets, path));
const hash = data => createHash('sha256').update(data).digest('hex');
const module = await WebAssembly.compile(await load('fullbleed.wasm'));
const fonts = Object.fromEntries(await Promise.all([
  'Inter-Variable.ttf', 'DMSerifDisplay-Regular.ttf', 'DMSerifDisplay-Italic.ttf', 'BebasNeue-Regular.ttf',
].map(async name => [name, await load(`fonts/${name}`)])));
const cases = [];
const fixtures = [['invoice', 1], ['report', 3], ['notice', 1], ['invoice-edited', 1]].map(([name, pages]) => ({ name, pages }));
fixtures.push(...gradientFixtures);
for (const fixture of fixtures) {
  const { name, pages } = fixture;
  const gradient = Boolean(fixture.probes);
  const example = gradient ? 'report' : name === 'invoice-edited' ? 'invoice' : name;
  let { html, css } = gradient ? fixture : prepareExample(example,
    await readFile(join(root, `docs/assets/showcase/${example}.html`), 'utf8'),
    await readFile(join(root, `docs/assets/showcase/${example}.css`), 'utf8'));
  if (name === 'invoice-edited') {
    html = html.replace('Maple &amp; Finch', 'Cedar &amp; Stone café') + '\n<!-- Saved UTF-8: München & <draft> 😀 -->\n';
    css = css.replaceAll('#17382e', '#17315a');
  }
  const snapshot = { name: example, html, css };
  const zip = await buildProject(snapshot, load);
  assert.deepEqual(zip, await buildProject(snapshot, load), `${name}: identical sources changed the ZIP`);
  await writeFile(join(output, `${name}.zip`), zip);
  const expected = join(output, `${name}-expected`);
  await mkdir(expected, { recursive: true });
  await writeFile(join(expected, 'input.html'), html);
  await writeFile(join(expected, 'style.css'), css);
  const result = await render(module, { ...fonts, 'input.html': Buffer.from(html), 'style.css': Buffer.from(css) });
  const inspection = JSON.parse(Buffer.from(result.outputs['result.json']).toString());
  assert.equal(inspection.pages, pages);
  assert.equal(inspection.missing_glyphs, 0, `${name}: missing glyphs`);
  const color_probes = gradient ? checkGradient(fixture, result.outputs['page-1.png']) : [];
  for (const [file, bytes] of Object.entries(result.outputs)) await writeFile(join(expected, file), bytes);
  cases.push({ name, pages, missing_glyphs: 0, color_probes, zip_sha256: hash(zip), pdf_sha256: hash(result.outputs['output.pdf']) });
}

for (const name of ['../escape', '/absolute', 'C:/drive', 'fonts/../escape', 'fonts\\escape', 'bad\0name']) {
  assert.throws(() => storeZip([{ name, bytes: new Uint8Array() }]), /filename/);
}
assert.throws(() => storeZip([{ name: 'same', bytes: new Uint8Array() }, { name: 'same', bytes: new Uint8Array() }]), /filename/);
const snapshot = { name: 'invoice', html: '<p>Saved text</p>', css: '' };
await assert.rejects(buildProject(snapshot, async path => {
  const bytes = await load(path);
  return path === 'fonts/Inter-Variable.ttf' ? bytes.subarray(1) : bytes;
}), /bundled fonts changed/);
await assert.rejects(buildProject(snapshot, async path => {
  if (path === 'project/render.py') throw new Error('Simulated asset download failure');
  return load(path);
}), /Simulated asset download failure/);
const recovered = await buildProject(snapshot, load); // A failed download must not poison a later attempt.
// Exercise the production fetch path with a versioned module, as used by the page.
const { buildProject: versionedBuild } = await import('../docs/assets/playground/project-export.js?v=cache-check');
const originalFetch = globalThis.fetch;
const fetched = [];
try {
  globalThis.fetch = async value => {
    const url = new URL(value);
    fetched.push(url);
    return new Response(await load(relative(assets, fileURLToPath(url))), { status: 200 });
  };
  assert.deepEqual(await versionedBuild(snapshot), recovered, 'Versioned asset URLs changed the project bytes');
  assert(fetched.length > 0 && fetched.every(url => url.search === '?v=cache-check'), 'Project assets lost their cache generation');
} finally {
  globalThis.fetch = originalFetch;
}
const result = { ok: true, cases, checks: ['ZIP replay is byte-identical', 'Unsafe and duplicate archive filenames are rejected',
  'Changed font bytes reject the export', 'Asset failure rejects the export and a subsequent attempt succeeds',
  'Project assets preserve the module URL cache generation'] };
await writeFile(join(output, 'export-verification.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result));
