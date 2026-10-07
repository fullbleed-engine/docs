// SPDX-License-Identifier: MIT
import assert from 'node:assert/strict';
import { decodePng } from './png.mjs';

export const standardFontFaces = [
  'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique',
  'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic',
  'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique',
];

export const standardFontFixture = {
  name: 'standard-fonts', pages: 1,
  html: standardFontFaces.map(face => `<p style="font-family:&quot;${face}&quot;">${face} preview</p>`).join(''),
  css: '@page { size: A5; margin: 15mm } body { color: #111; font-size: 14pt } p { margin: 0 0 6pt; line-height: 1.3 }',
};

// Each line needs real ink. Equality between native and WASI blank images is insufficient.
export function checkStandardFonts(bytes) {
  const image = decodePng(Buffer.from(bytes));
  assert.equal(image.width, 559);
  assert.equal(image.height, 794);
  const top = 15 * 96 / 25.4, line = (14 * 1.3 + 6) * 96 / 72;
  return standardFontFaces.map((face, index) => {
    const firstY = Math.floor(top + index * line), lastY = Math.floor(top + (index + 1) * line);
    let inkPixels = 0;
    for (let y = firstY; y < lastY; y++) {
      for (let x = 0; x < image.width; x++) {
        const [r, g, b, a] = image.pixel(x, y);
        if (a > 0 && Math.min(r, g, b) < 245) inkPixels++;
      }
    }
    assert(inkPixels > 200, `${face}: preview text is missing (${inkPixels} ink pixels)`);
    return { face, firstY, lastY, inkPixels };
  });
}
