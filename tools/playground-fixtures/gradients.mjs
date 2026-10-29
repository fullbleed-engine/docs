// SPDX-License-Identifier: MIT
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { decodePng } from './png.mjs';

const fixture = (name, gradient, probes, backdrop = 'white') => ({
  name,
  pages: 1,
  html: '<div></div>',
  css: `@page {size:100pt 100pt;margin:0} body {margin:0;background:${backdrop}} div {width:100pt;height:100pt;background:${gradient}}`,
  probes,
});

const radialInputs = JSON.parse(readFileSync(new URL('./radial-gradient-endpoints-2.5.43.json', import.meta.url), 'utf8'));
assert.equal(radialInputs.schema, 'fullbleed.radial_gradient_endpoints.v1');
assert.equal(radialInputs.referenceVersion, '2.5.43');
assert.equal(radialInputs.cases.length, 12);
assert.equal(radialInputs.cases.filter(item => item.affected).length, 9);
export const radialEndpointFixtures = radialInputs.cases.map(item => {
  assert.equal(createHash('sha256').update(item.html + '\0' + item.css).digest('hex'), item.inputSha256);
  return {
    name: 'radial-endpoint-' + item.name, pages: 1, html: item.html, css: item.css,
    probes: item.probes.map(([x, y]) => [x, y, item.expected]), tolerance: 1,
    referencePdfSha256: item.candidatePdfSha256,
  };
});

export const gradientFixtures = [
  fixture('linear-gradient', 'linear-gradient(90deg,red,blue)', [[25, 50, [190, 0, 65]], [75, 50, [62, 0, 193]]]),
  fixture('translucent-gradient', 'linear-gradient(90deg,rgba(255,0,0,.5),rgba(0,0,255,.5))', [[25, 50, [95, 128, 33]], [75, 50, [31, 128, 97]]], '#00ff00'),
  fixture('hard-radial-gradient', 'radial-gradient(circle 40pt at 50pt 50pt,red 0%,red 50%,blue 50%,blue 100%)', [[60, 50, [255, 0, 0]], [80, 50, [0, 0, 255]]]),
  ...radialEndpointFixtures,
];

// Probe interior colors from the finalized PDF, rather than comparing two blank previews.
export function checkGradient(fixture, bytes, dpi = 96) {
  const image = decodePng(Buffer.from(bytes));
  assert.equal(image.width, Math.round(100 * dpi / 72));
  assert.equal(image.height, Math.round(100 * dpi / 72));
  return fixture.probes.map(([xPt, yPt, expected]) => {
    const x = Math.floor(xPt * dpi / 72), y = Math.floor(yPt * dpi / 72);
    const actual = image.pixel(x, y);
    assert.equal(actual[3], 255, `${fixture.name}: preview opacity`);
    assert(expected.every((value, channel) => Math.abs(value - actual[channel]) <= (fixture.tolerance ?? 3)),
      `${fixture.name} (${x},${y}): ${actual}, expected ${expected}`);
    return { x, y, actual, expected, tolerance: fixture.tolerance ?? 3 };
  });
}
