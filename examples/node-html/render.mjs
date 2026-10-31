// SPDX-License-Identifier: MIT
import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { renderPdf, version } from 'fullbleed';
import { digest, loadDocument, selectedDocuments } from './document.mjs';

const output = resolve(process.argv[3] ?? 'output/fullbleed');
await mkdir(output, { recursive: true });
const documents = [];
for (const name of selectedDocuments(process.argv[2])) {
  const input = await loadDocument(name);
  const result = await renderPdf({
    html: input.html, fonts: input.fonts, assets: input.assets,
    defaultStyles: false, previewDpi: 96, isolation: 'process',
  });
  const folder = join(output, name);
  await mkdir(folder, { recursive: true });
  await writeFile(join(folder, 'input.html'), input.html);
  await writeFile(join(folder, 'document.pdf'), result.pdf);
  for (let i = 0; i < result.previews.length; i++) {
    await writeFile(join(folder, `page-${i + 1}.png`), result.previews[i]);
  }
  documents.push({ name, pages: result.pages, missingGlyphs: result.missingGlyphs,
    engineVersion: result.engineVersion, inputSha256: input.inputSha256,
    pdfSha256: digest(result.pdf), previewSha256: result.previews.map(digest),
    totalCents: input.totalCents, items: input.record.items.length });
}
const record = { packageVersion: version, node: process.version, documents };
await writeFile(join(output, 'render.json'), JSON.stringify(record, null, 2) + '\n');
console.log(JSON.stringify(record));
