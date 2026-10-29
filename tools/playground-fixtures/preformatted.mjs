// SPDX-License-Identifier: MIT
// The unchanged explicit-font inputs qualified against the released bindings.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const source = await readFile(new URL('./preformatted-whitespace-2.5.41.json', import.meta.url));
const inputs = JSON.parse(source);
const reference = JSON.parse(await readFile(new URL('./preformatted-2.5.41-reference.json', import.meta.url)));
assert.equal(hash(source), reference.inputSha256);
assert.equal(inputs.cases.length, 17);
assert.deepEqual(Object.keys(reference.pages).sort(), inputs.cases.map(item => item.name).sort());
export const preformattedAssets = await Promise.all(['NotoSans-Regular.ttf', 'NotoSans-OFL.txt'].map(async name => ({
  name, bytes: await readFile(new URL('./fonts/' + name, import.meta.url)),
})));
assert.equal(hash(preformattedAssets[0].bytes), inputs.fontSha256);
export const preformattedFiles = {
  ...Object.fromEntries(preformattedAssets.map(item => ['assets/' + item.name, item.bytes])),
  'local-fonts.txt': Buffer.from('assets/NotoSans-Regular.ttf\n'),
};
export const preformattedFixtures = inputs.cases.map(item => {
  assert.equal(hash(Buffer.from(item.html)), item.htmlSha256);
  assert.equal(hash(Buffer.from(item.css)), item.cssSha256);
  return { ...item, name: 'preformatted-' + item.name, pages: reference.pages[item.name], assets: preformattedAssets };
});
