// SPDX-License-Identifier: MIT
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { buildProject } from '../docs/assets/playground/project-export.js';
import { readProject, projectLimits } from '../docs/assets/playground/project-import.js';
import { storeZip } from '../docs/assets/playground/zip-store.js';

const encoder = new TextEncoder();
const decoder = new TextDecoder();
const load = path => readFile(new URL(`../docs/assets/playground/${path}`, import.meta.url));
const file = bytes => new File([bytes], 'saved-project.zip');
const source = { name: 'custom', html: '<h1>Café &amp; saved work</h1>\r\n', css: 'h1 { color: #17382e }\n', assets: [
  { name: 'café #1%.png', bytes: new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]) },
  { name: 'LICENSE.txt', bytes: encoder.encode('Synthetic test asset license.\n') },
  { name: 'brand.ttf', bytes: new Uint8Array(await load('fonts/Inter-Variable.ttf')) },
] };
const checks = [];
async function check(name, action) {
  await action(); checks.push(name); console.log(name + ': passed');
}
// Extract the known writer's output to create independently malformed test inputs.
function entries(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength), result = [];
  for (let at = 0; view.getUint32(at, true) === 0x04034b50;) {
    const size = view.getUint32(at + 18, true), length = view.getUint16(at + 26, true);
    result.push({ name: decoder.decode(bytes.subarray(at + 30, at + 30 + length)), bytes: bytes.slice(at + 30 + length, at + 30 + length + size) });
    at += 30 + length + size;
  }
  return result;
}
const original = await buildProject(source, load);
async function changed(action, pattern = /ZIP|project|filename|hash|asset|UTF-8|source|MiB|200 KB/i) {
  const files = entries(original);
  action(files);
  await assert.rejects(readProject(file(storeZip(files))), pattern);
}
function changeManifest(files, action) {
  const entry = files.find(item => item.name === 'project.json');
  const manifest = JSON.parse(decoder.decode(entry.bytes));
  action(manifest);
  entry.bytes = encoder.encode(JSON.stringify(manifest));
}

for (const language of ['python', 'node']) {
  await check(language + ' source, Unicode names, fonts and licenses survive export/import/export', async () => {
    const bytes = await buildProject({ ...source, language }, load);
    const restored = await readProject(file(bytes));
    assert.equal(restored.html, source.html);
    assert.equal(restored.css, source.css);
    assert.equal(restored.language, language);
    assert.deepEqual(restored.assets, source.assets);
    assert.deepEqual(await buildProject({ ...restored, name: 'custom' }, load), bytes);
  });
}
await check('empty CSS and no assets are supported', async () => {
  const restored = await readProject(file(await buildProject({ name: 'invoice', html: '<h1>Hello</h1>', css: '' }, load)));
  assert.equal(restored.css, ''); assert.deepEqual(restored.assets, []);
});
await check('leading Unicode byte-order marks in authored source are preserved', async () => {
  const input = { name: 'custom', html: '\ufeff<p>Saved source</p>\r\n', css: '\ufeffp { color: green; }' };
  const restored = await readProject(file(await buildProject(input, load)));
  assert.equal(restored.html, input.html); assert.equal(restored.css, input.css);
});
await check('older engine metadata is returned for an explicit preview notice', async () => {
  const files = entries(original);
  changeManifest(files, manifest => { manifest.engine.version = '2.5.0'; });
  assert.equal((await readProject(file(storeZip(files)))).engineVersion, '2.5.0');
});
await check('oversized and invalid sizes are rejected before reading the file', async () => {
  for (const size of [projectLimits.bytes + 1, -1, NaN, Infinity, 1.5, 21]) {
    let read = false;
    await assert.rejects(readProject({ size, arrayBuffer: () => { read = true; throw new Error('must not read'); } }), /24 MiB/);
    assert.equal(read, false);
  }
});
await check('partial reads are rejected', () => assert.rejects(readProject({ size: original.length, arrayBuffer: async () => original.slice(1).buffer }), /whole project/));
await check('HTML/CSS above the browser cap still exports but cannot be reopened', async () => {
  const bytes = await buildProject({ name: 'custom', html: 'é'.repeat(100001), css: '' }, load);
  await assert.rejects(readProject(file(bytes)), /200 KB/);
});
await check('damaged entry data is rejected by CRC', async () => {
  const bytes = original.slice(); bytes[40] ^= 1;
  await assert.rejects(readProject(file(bytes)), /damaged/);
});
await check('changed source with a fresh CRC still fails the saved SHA-256', () => changed(files => {
  files[0].bytes = encoder.encode('<h1>changed</h1>');
}, /saved hashes/));
await check('invalid UTF-8 filenames are rejected', async () => {
  const bytes = original.slice(), view = new DataView(bytes.buffer);
  const directory = view.getUint32(bytes.length - 6, true);
  bytes[30] = 0xff; bytes[directory + 46] = 0xff;
  await assert.rejects(readProject(file(bytes)), /UTF-8/);
});
for (const [name, modify] of [
  ['compressed entry', (v, d) => v.setUint16(d + 10, 8, true)],
  ['encrypted entry', (v, d) => v.setUint16(d + 8, 0x801, true)],
  ['data descriptor', (v, d) => v.setUint16(d + 8, 0x808, true)],
  ['multivolume archive', (v, d, end) => v.setUint16(end + 4, 1, true)],
  ['too many entries', (v, d, end) => v.setUint16(end + 10, 65, true)],
  ['oversized entry', (v, d) => v.setUint32(d + 24, 0xffffffff, true)],
  ['extra ZIP fields', (v, d) => v.setUint16(d + 30, 1, true)],
  ['symlink entry', (v, d) => v.setUint32(d + 38, 0o120777 << 16, true)],
  ['overlapping entry offsets', (v, d) => v.setUint32(d + 42, 1, true)],
  ['mismatched local filename', v => v.setUint8(30, 120)],
  ['mismatched local size', v => v.setUint32(18, 0, true)],
]) {
  await check(name + ' is rejected', async () => {
    const bytes = original.slice(), view = new DataView(bytes.buffer), end = bytes.length - 22;
    modify(view, view.getUint32(end + 16, true), end);
    await assert.rejects(readProject(file(bytes)), /ZIP/);
  });
}
await check('truncated and appended archives are rejected', async () => {
  for (const bytes of [original.slice(0, -1), original.slice(0, 100), new Uint8Array([...original, 0])]) {
    await assert.rejects(readProject(file(bytes)), /ZIP/);
  }
});
await check('unknown manifest version is rejected', () => changed(files => changeManifest(files, m => { m.format = 2; })));
await check('non-project manifest is rejected', () => changed(files => changeManifest(files, m => { m.source = 'https://example.com/'; })));
await check('missing manifest is rejected', () => changed(files => { files.splice(files.findIndex(f => f.name === 'project.json'), 1); }));
await check('malformed metadata is rejected', () => changed(files => { files.find(f => f.name === 'project.json').bytes = encoder.encode('{'); }));
await check('unknown runtime is rejected', () => changed(files => changeManifest(files, m => { m.runtime = { name: 'other' }; })));
await check('duplicate manifest entries are rejected', () => changed(files => changeManifest(files, m => { m.files[1] = m.files[0]; })));
await check('unlisted ZIP entry is rejected', () => changed(files => { files.push({ name: 'extra.txt', bytes: encoder.encode('extra') }); }));
await check('case-equivalent entry names are rejected', () => changed(files => { files.push({ name: 'INPUT.HTML', bytes: encoder.encode('extra') }); }));
await check('normalization-equivalent entry names are rejected', () => changed(files => { files.push({ name: 'assets/cafe\u0301 #1%.png', bytes: source.assets[0].bytes }); }));
await check('asset manifest omissions are rejected', () => changed(files => changeManifest(files, m => { m.localAssets.pop(); })));
await check('inconsistent asset font flags are rejected', () => changed(files => changeManifest(files, m => { m.localAssets[0].font = true; })));
await check('duplicate asset paths are rejected', () => changed(files => changeManifest(files, m => { m.localAssets.push(m.localAssets[0]); })));
await check('unsafe filenames cannot enter the archive', () => {
  for (const name of ['../bad.txt', '/bad.txt', 'assets/../bad.txt']) assert.throws(() => storeZip([{ name, bytes: encoder.encode('x') }]), /filename/);
});
await check('reserved filenames in an otherwise valid ZIP are rejected', () => changed(files => { files.push({ name: 'CON.txt', bytes: encoder.encode('x') }); }));
console.log(JSON.stringify({ passed: checks.length, checks }));
