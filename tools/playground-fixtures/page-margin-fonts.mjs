// Reviewed page-font comparisons adapted to the real local-asset/export path.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
export const pageFontSource = JSON.parse(readFileSync(new URL('./page-margin-fonts-2.5.48.json', import.meta.url), 'utf8'));
assert.equal(pageFontSource.cases.length, 8);
const assets = pageFontSource.fonts.map(font => {
  const bytes = readFileSync(new URL(font.path, root));
  assert.equal(createHash('sha256').update(bytes).digest('hex'), font.sha256);
  return { name: font.name, bytes };
});
for (const [name, path] of [
  ['Body-OFL.txt', 'tools/playground-fixtures/fonts/NotoSans-OFL.txt'],
  ['Display-OFL.txt', 'docs/assets/playground/fonts/DMSerifDisplay-OFL.txt'],
]) assets.push({ name, bytes: readFileSync(new URL(path, root)) });
export const pageFontFiles = {
  ...Object.fromEntries(assets.map(asset => ['assets/' + asset.name, asset.bytes])),
  'local-fonts.txt': Buffer.from(pageFontSource.fonts.map(font => 'assets/' + font.name).join('\n')),
};
export const pageFontFixtures = pageFontSource.cases.flatMap(specimen => ['control', 'alias'].map(kind => ({
  name: `page-font-${specimen.name}-${kind}`, html: specimen.html, css: specimen[kind + 'Css'],
  pages: specimen.footerFaces.length, assets,
})));
