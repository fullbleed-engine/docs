// Verify real rendering across the native and WASI builds of the released crate.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { render } from '../docs/assets/playground/renderer.js';
import { prepareExample } from '../docs/assets/playground/examples.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const engine = join(root, 'playground/engine');
const assets = join(root, 'docs/assets/playground');
const evidence = join(root, 'playground/verification');
await mkdir(evidence, { recursive: true });
const build = spawnSync('cargo', ['build', '--release', '--locked'], { cwd: engine, stdio: 'inherit' });
assert.equal(build.status, 0, 'Native wrapper build failed');
const exe = join(engine, 'target/release', process.platform === 'win32' ? 'fullbleed-playground.exe' : 'fullbleed-playground');
const wasmBytes = await readFile(join(assets, 'fullbleed.wasm'));
const module = await WebAssembly.compile(wasmBytes);
const imports = WebAssembly.Module.imports(module);
assert(imports.every(item => item.module === 'wasi_snapshot_preview1'), 'Unexpected host capabilities');
assert(imports.every(item => !item.name.startsWith('sock_')), 'Unexpected socket import');
// Inspect the actual module's declared memory ceiling, not just its build settings.
let cursor = 8, memoryMaximum;
const leb = () => {
  let value = 0, shift = 0, byte;
  do { byte = wasmBytes[cursor++]; value += (byte & 127) * 2 ** shift; shift += 7; } while (byte & 128);
  return value;
};
while (cursor < wasmBytes.length) {
  const section = wasmBytes[cursor++], length = leb(), end = cursor + length;
  if (section === 5) {
    assert.equal(leb(), 1, 'Expected one bounded linear memory');
    const flags = leb(); leb();
    assert.equal(flags, 1, 'Expected an explicit unshared memory maximum');
    memoryMaximum = leb() * 65536;
  }
  cursor = end;
}
assert.equal(memoryMaximum, 268435456, 'WASM memory limit missing or incorrect');
const hash = data => createHash('sha256').update(data).digest('hex');
const fonts = Object.fromEntries(await Promise.all(['Inter-Variable.ttf', 'DMSerifDisplay-Regular.ttf', 'DMSerifDisplay-Italic.ttf', 'BebasNeue-Regular.ttf']
  .map(async name => [name, await readFile(join(assets, 'fonts', name))])));
const report = { engine: '2.5.0', platform: process.platform, node: process.version, wasm_sha256: hash(wasmBytes), wasm_memory_maximum: memoryMaximum, fixtures: [], checks: ['Module declares a 256 MiB memory ceiling and no socket imports'] };

async function fixture(name, html, css, expectedPages) {
  const files = { ...fonts, 'input.html': Buffer.from(html), 'style.css': Buffer.from(css) };
  // Retain the exact prepared inputs for other language bindings to replay.
  await writeFile(join(evidence, `${name}.html`), html);
  await writeFile(join(evidence, `${name}.css`), css);
  const nativeDir = await mkdtemp(join(evidence, `${name}-native-`));
  for (const [file, data] of Object.entries(files)) await writeFile(join(nativeDir, file), data);
  const native = spawnSync(exe, [], { cwd: nativeDir, encoding: 'utf-8', timeout: 30000 });
  assert.equal(native.status, 0, native.stderr);
  const result = await render(module, files);
  const info = JSON.parse(new TextDecoder().decode(result.outputs['result.json']));
  assert.equal(info.pages, expectedPages, `${name} page count`);
  assert.equal(info.missing_glyphs, 0, `${name} glyph coverage`);
  const hashes = {};
  for (const [file, data] of Object.entries(result.outputs)) {
    const nativeBytes = await readFile(join(nativeDir, file));
    assert.equal(hash(data), hash(nativeBytes), `${name}/${file}: native/WASI mismatch`);
    hashes[file] = hash(data);
  }
  const pdf = result.outputs['output.pdf'];
  assert.equal(new TextDecoder().decode(pdf.slice(0, 5)), '%PDF-');
  const rerun = await render(module, files);
  assert.equal(hash(pdf), hash(rerun.outputs['output.pdf']), `${name}: nondeterministic rerender`);
  report.fixtures.push({ name, pages: expectedPages, missing_glyphs: 0, native_wasi_equal: true, repeat_equal: true, hashes,
    source_files: { html: `${name}.html`, css: `${name}.css`, html_sha256: hash(Buffer.from(html)), css_sha256: hash(Buffer.from(css)) } });
  return { files, pdfHash: hash(pdf), memory: result.memory };
}

let invoice;
for (const [name, pages] of [['invoice', 1], ['report', 3], ['notice', 1]]) {
  const { html, css } = prepareExample(name,
    await readFile(join(root, `docs/assets/showcase/${name}.html`), 'utf-8'),
    await readFile(join(root, `docs/assets/showcase/${name}.css`), 'utf-8'));
  const result = await fixture(name, html, css, pages);
  if (name === 'invoice') {
    invoice = { ...result, html, css };
    const edited = await fixture('invoice-edited', html.replace('Maple &amp; Finch', 'Cedar &amp; Stone'), css.replaceAll('#17382e', '#17315a'), 1);
    assert.notEqual(edited.pdfHash, result.pdfHash, 'Editing source did not change the PDF');
    report.checks.push('Text and palette edits change output and preserve native/WASI equality');
  }
}
await assert.rejects(render(module, { ...fonts, 'input.html': Buffer.from('x'.repeat(200001)), 'style.css': Buffer.from('') }), /200 KB/);
report.checks.push('Oversized source rejected by the Rust adapter');
await assert.rejects(render(module, { ...fonts, 'input.html': Buffer.from('<div>Page</div>'.repeat(7)), 'style.css': Buffer.from('@page {size:A4} div{break-after:page}') }), /1 to 6 pages/);
report.checks.push('Seven-page document rejected by the Rust adapter');
const recovery = await render(module, invoice.files);
assert.equal(hash(recovery.outputs['output.pdf']), invoice.pdfHash, 'A failed render contaminated the next job');
report.checks.push('A valid render after failures reproduces the original PDF');
report.ok = true;
const output = JSON.stringify(report, null, 2) + '\n';
await writeFile(join(evidence, 'verification.json'), output);
await writeFile(join(assets, 'verification.json'), output);
console.log(JSON.stringify({ ok: true, fixtures: report.fixtures.map(f => ({name:f.name, pages:f.pages})), checks: report.checks }));
