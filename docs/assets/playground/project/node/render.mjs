// SPDX-License-Identifier: MIT
// Render your saved playground source. All paths are relative to this project.
import { readFile, writeFile, mkdir, readdir, unlink } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { renderPdf, version, engineVersion } from 'fullbleed';

const file = name => new URL(name, import.meta.url);
const manifest = JSON.parse(await readFile(file('project.json'), 'utf8'));
if (version !== manifest.runtime.package.version || engineVersion !== manifest.engine.version) {
  throw new Error('The installed Fullbleed version differs from this project. Run npm ci --ignore-scripts.');
}
const fontNames = ['Inter-Variable.ttf', 'DMSerifDisplay-Regular.ttf', 'DMSerifDisplay-Italic.ttf', 'BebasNeue-Regular.ttf'];
const result = await renderPdf({
  html: await readFile(file('input.html'), 'utf8'),
  css: await readFile(file('style.css'), 'utf8'),
  fonts: await Promise.all(fontNames.map(name => readFile(file('fonts/' + name)))),
  defaultStyles: false,
  previewDpi: 96,
});
await mkdir(file('output/preview/'), { recursive: true });
await writeFile(file('output/document.pdf'), result.pdf);
// Remove only this runner's generated page images after a successful render.
for (const name of await readdir(file('output/preview/'))) {
  if (/^page-[1-9]\d*\.png$/.test(name)) await unlink(file('output/preview/' + name));
}
const previews = [];
for (const [i, bytes] of result.previews.entries()) {
  const path = file(`output/preview/page-${i + 1}.png`);
  await writeFile(path, bytes);
  previews.push(fileURLToPath(path));
}
const report = {
  package: version, engine: engineVersion, pdf: fileURLToPath(file('output/document.pdf')),
  pages: result.pages, missingGlyphs: result.missingGlyphs, previews,
  sha256: createHash('sha256').update(result.pdf).digest('hex'),
};
await writeFile(file('output/render.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
