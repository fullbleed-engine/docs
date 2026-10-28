// SPDX-License-Identifier: MIT
// File imports must be atomic, bounded before reading, and portable in both ZIPs.
import assert from 'node:assert/strict';
import { readSelection, validateAssets, validateName, validateSource, limits } from '../docs/assets/playground/local-files.js';
import { buildProject } from '../docs/assets/playground/project-export.js';
import { readFile } from 'node:fs/promises';

const checks = [];
const bytes = value => new TextEncoder().encode(value);
const file = (name, value) => new File([typeof value === 'string' ? bytes(value) : value], name);
const png = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);
const old = [{ name: 'existing.svg', bytes: bytes('<svg/>') }];
const imported = await readSelection([file('café.html', '<h1>Café</h1>'), file('theme.css', 'h1 { color: teal }'),
  file('café #1%.png', png), file('LICENSE.txt', 'Local test license')], old);
assert.equal(imported.html, '<h1>Café</h1>');
assert.equal(imported.css, 'h1 { color: teal }');
assert.deepEqual(imported.assets.map(a => a.name), ['café #1%.png', 'LICENSE.txt']);
assert.deepEqual(old, [{ name: 'existing.svg', bytes: bytes('<svg/>') }]);
checks.push('UTF-8 sources and portable asset names are imported without mutating existing assets');

for (const name of ['../x.png', 'assets/x.png', 'x\\a.png', 'CON.txt', 'nul.png', 'x:stream.png', '.hidden.svg', 'trailing.svg ', 'a\n.svg', 'x'.repeat(121) + '.png']) {
  assert.throws(() => validateName(name), /filename/);
}
for (const assets of [
  [{ name: 'photo.png', bytes: png }, { name: 'PHOTO.PNG', bytes: png }],
  [{ name: 'café.png', bytes: png }, { name: 'cafe\u0301.png', bytes: png }],
]) assert.throws(() => validateAssets(assets), /already present/);
checks.push('Unsafe names and case/Unicode-equivalent duplicates are rejected');

for (const files of [[file('one.html', ''), file('two.htm', '')], [file('one.css', ''), file('two.css', '')],
  [file('a.exe', 'text')], [file('bad.html', new Uint8Array([0xff]))], [file('bad.png', 'not a PNG')],
  [file('bad.jpg', 'not a JPEG')], [file('bad.svg', '<html/>')], [file('bad.ttf', 'not a font')],
  [file('empty.svg', '')], [file('bad.otf', 'not a font')], [file('bad.txt', new Uint8Array([0xff]))],
  [file('new.html', '<h1>Changed</h1>'), file('existing.svg', '<svg/>')]]) {
  await assert.rejects(readSelection(files, old));
  assert.equal(old.length, 1);
  assert.deepEqual(old[0].bytes, bytes('<svg/>'));
}
checks.push('Invalid selections reject the whole import');

let reads = 0;
const unopened = (name, size) => ({ name, size, async arrayBuffer() { reads++; throw new Error('Must not read'); } });
await assert.rejects(readSelection([unopened('large.png', limits.file + 1)]), /8 MiB/);
await assert.rejects(readSelection([unopened('large.html', limits.source + 1)]), /200 KB/);
await assert.rejects(readSelection([1, 2, 3].map(n => unopened(`${n}.png`, limits.file))), /20 MiB/);
await assert.rejects(readSelection(Array.from({ length: 17 }, (_, n) => unopened(`${n}.png`, 8))), /16 local/);
assert.equal(reads, 0);
await assert.rejects(readSelection([{ name: 'partial.html', size: 5, arrayBuffer: async () => bytes('x').buffer }]), /read all/);
assert.throws(() => validateSource('é'.repeat(limits.source / 2), 'x'), /200 KB/);
checks.push('Combined/count/per-file limits are enforced before reading and source limit counts UTF-8 bytes');

const load = path => readFile(new URL('../docs/assets/playground/' + path, import.meta.url));
const original = { name: 'custom', html: '<p>Snapshot</p>', css: '', assets: [{ name: 'license.txt', bytes: bytes('Original') }] };
const expected = await buildProject(original, load);
let release;
const pause = new Promise(resolve => { release = resolve; });
const pending = buildProject(original, async path => { await pause; return load(path); });
original.assets[0].bytes.fill(88);
original.assets.push({ name: 'other.txt', bytes: bytes('Later') });
release();
assert.deepEqual(await pending, expected);
// Local projects deliberately support sources above the browser render ceiling.
await buildProject({ name: 'custom', html: 'x'.repeat(limits.source + 1), css: '' }, load);
checks.push('Project export snapshots asset bytes before awaiting downloads and retains large-source local export');
console.log(JSON.stringify({ ok: true, checks }, null, 2));
