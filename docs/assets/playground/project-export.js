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

export async function buildProject({ name, html, css, language = 'python' }, load = fetchBytes) {
  if (!examples.has(name) || typeof html !== 'string' || typeof css !== 'string') {
    throw new Error('Choose a playground example before downloading a project.');
  }
  if (!['python', 'node'].includes(language)) throw new Error('Choose Python or Node.js for your project.');
  const node = language === 'node';
  const [buildBytes, fontBytes, runner, readme, license] = await Promise.all([
    load('build.json'), load('font-sources.json'), load(node ? 'project/node/render.mjs' : 'project/render.py'),
    load(node ? 'project/node/README.txt' : 'project/README.txt'), load('project/LICENSE.txt'),
  ]);
  const version = JSON.parse(decoder.decode(buildBytes)).engine.version;
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error('Reload the playground to refresh the project version.');
  let packageVersion;
  const dependencies = node ? await Promise.all(['package.json', 'package-lock.json'].map(async name => ({
    name, bytes: await load('project/node/' + name),
  }))) : [{ name: 'requirements.txt', bytes: encoder.encode(`fullbleed==${version}\n`) }];
  if (node) {
    const pkg = JSON.parse(decoder.decode(dependencies[0].bytes));
    const lock = JSON.parse(decoder.decode(dependencies[1].bytes));
    packageVersion = pkg.dependencies?.fullbleed;
    if (!/^\d+\.\d+\.\d+$/.test(packageVersion) || pkg.fullbleed?.engineVersion !== version
        || lock.packages?.['']?.dependencies?.fullbleed !== packageVersion
        || lock.packages?.['node_modules/fullbleed']?.version !== packageVersion) {
      throw new Error('Reload the playground to refresh the Node.js project version.');
    }
  }
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
    { name: node ? 'render.mjs' : 'render.py', bytes: runner },
    ...dependencies,
    { name: 'README.txt', bytes: encoder.encode(decoder.decode(readme).replaceAll('{{ENGINE_VERSION}}', version).replaceAll('{{PACKAGE_VERSION}}', packageVersion ?? '')) },
    { name: 'LICENSE.txt', bytes: license },
    { name: 'fonts/font-sources.json', bytes: fontBytes },
    ...fonts,
  ];
  const manifest = {
    format: 1, source: 'https://docs.fullbleed.dev/playground/', example: name,
    engine: { name: 'fullbleed', version },
    files: await Promise.all(files.map(async file => ({ path: file.name, bytes: file.bytes.length, sha256: await sha256(file.bytes) }))),
  };
  if (node) manifest.runtime = { name: 'node', minimumVersion: '22', package: { name: 'fullbleed', version: packageVersion } };
  files.push({ name: 'project.json', bytes: encoder.encode(JSON.stringify(manifest, null, 2) + '\n') });
  return storeZip(files);
}
