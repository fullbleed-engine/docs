// SPDX-License-Identifier: MIT
import { storeZip } from './zip-store.js';

const encoder = new TextEncoder();
const decoder = new TextDecoder();
const examples = new Set(['invoice', 'report', 'notice']);

async function fetchBytes(path) {
  let response;
  const url = new URL(path, import.meta.url);
  url.search = new URL(import.meta.url).search;
  try { response = await fetch(url); }
  catch { throw new Error('Could not load the project files. Check your connection and try Download project again.'); }
  if (!response.ok) throw new Error('Could not load the project files. Check your connection and try Download project again.');
  return new Uint8Array(await response.arrayBuffer());
}

async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

export async function buildProject({ name, html, css }, load = fetchBytes) {
  if (!examples.has(name) || typeof html !== 'string' || typeof css !== 'string') {
    throw new Error('Choose a playground example before downloading a project.');
  }
  const [buildBytes, fontBytes, runner, readme, license] = await Promise.all([
    load('build.json'), load('font-sources.json'), load('project/render.py'),
    load('project/README.txt'), load('project/LICENSE.txt'),
  ]);
  const version = JSON.parse(decoder.decode(buildBytes)).engine.version;
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Reload the playground to refresh the project version.');
  const fontSources = JSON.parse(decoder.decode(fontBytes));
  const fonts = await Promise.all(fontSources.files.map(async file => {
    if (!/^[A-Za-z0-9-]+\.(ttf|txt)$/.test(file.file)) throw new Error('Invalid bundled font filename.');
    const bytes = await load(`fonts/${file.file}`);
    if (bytes.length !== file.bytes || await sha256(bytes) !== file.sha256) {
      throw new Error('The bundled fonts changed during download. Reload the playground and try again.');
    }
    return { name: `fonts/${file.file}`, bytes };
  }));
  const files = [
    { name: 'input.html', bytes: encoder.encode(html) },
    { name: 'style.css', bytes: encoder.encode(css) },
    { name: 'render.py', bytes: runner },
    { name: 'requirements.txt', bytes: encoder.encode(`fullbleed==${version}\n`) },
    { name: 'README.txt', bytes: encoder.encode(decoder.decode(readme).replaceAll('{{ENGINE_VERSION}}', version)) },
    { name: 'LICENSE.txt', bytes: license },
    { name: 'fonts/font-sources.json', bytes: fontBytes },
    ...fonts,
  ];
  const manifest = {
    format: 1, source: 'https://docs.fullbleed.dev/playground/', example: name,
    engine: { name: 'fullbleed', version },
    files: await Promise.all(files.map(async file => ({ path: file.name, bytes: file.bytes.length, sha256: await sha256(file.bytes) }))),
  };
  files.push({ name: 'project.json', bytes: encoder.encode(JSON.stringify(manifest, null, 2) + '\n') });
  return storeZip(files);
}
