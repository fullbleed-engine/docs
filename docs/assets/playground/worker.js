// SPDX-License-Identifier: MIT
import { render } from './renderer.js';

async function bytes(path) {
  let response;
  const url = new URL(path, import.meta.url);
  url.search = new URL(import.meta.url).search;
  try { response = await fetch(url); }
  catch { throw new Error('Could not load the engine or fonts. Check your connection and render again.'); }
  if (!response.ok) throw new Error(`Could not load a playground asset (${response.status}). Please retry.`);
  return new Uint8Array(await response.arrayBuffer());
}

self.onmessage = async ({ data }) => {
  try {
    const encoder = new TextEncoder();
    const html = encoder.encode(data.html);
    const css = encoder.encode(data.css);
    if (html.length + css.length > 200000) throw new Error('This playground accepts up to 200 KB of HTML and CSS combined.');
    self.postMessage({ type: 'progress', message: 'Loading the engine and fonts…' });
    const names = ['Inter-Variable.ttf', 'DMSerifDisplay-Regular.ttf', 'DMSerifDisplay-Italic.ttf', 'BebasNeue-Regular.ttf'];
    const [wasm, fonts] = await Promise.all([
      bytes('fullbleed.wasm'),
      Promise.all(names.map(async name => [name, await bytes(`fonts/${name}`)])),
    ]);
    const module = await WebAssembly.compile(wasm);
    self.postMessage({ type: 'progress', message: 'Rendering your PDF…' });
    const started = performance.now();
    const result = await render(module, { 'input.html': html, 'style.css': css, ...Object.fromEntries(fonts) });
    const report = JSON.parse(new TextDecoder().decode(result.outputs['result.json']));
    const pdf = result.outputs['output.pdf'];
    const pages = Object.entries(result.outputs).filter(([name]) => /^page-\d+\.png$/.test(name))
      .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([, data]) => data);
    self.postMessage({ type: 'complete', pdf, pages, report, elapsed: performance.now() - started }, [pdf.buffer, ...pages.map(p => p.buffer)]);
  } catch (error) {
    const message = error instanceof WebAssembly.RuntimeError || error instanceof RangeError
      ? 'This document exceeded the browser demo’s limits. Try fewer pages or a smaller page size, or render it locally.'
      : error.message || String(error);
    self.postMessage({ type: 'error', message });
  }
};
