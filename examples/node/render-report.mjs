// SPDX-License-Identifier: MIT
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { renderPdf } from 'fullbleed';

const html = await readFile(new URL('./report.html', import.meta.url), 'utf8');
const css = await readFile(new URL('./report.css', import.meta.url), 'utf8');
const result = await renderPdf({ html, css, previewDpi: 96 });
const output = resolve(process.argv[2] ?? 'output/report');
await mkdir(output, { recursive: true });
await writeFile(join(output, 'report.pdf'), result.pdf);
for (let i = 0; i < result.previews.length; i++) await writeFile(join(output, `page-${i + 1}.png`), result.previews[i]);
console.log(JSON.stringify({ pdf: join(output, 'report.pdf'), pages: result.pages, missingGlyphs: result.missingGlyphs, engine: result.engineVersion }));
