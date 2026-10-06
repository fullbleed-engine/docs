import { writeFile } from 'node:fs/promises';
import { renderPdf } from 'fullbleed';

const result = await renderPdf({
  html: '<h1>Invoice NS-1042</h1><p>Consulting: USD 1,200.00</p>',
  css: '@page { size: A4; margin: 20mm } h1 { color: #175c52 }',
  previewDpi: 96,
});

await writeFile('invoice.pdf', result.pdf);
await writeFile('invoice.png', result.previews[0]);
console.log(`${result.pages} page; engine ${result.engineVersion}`);
