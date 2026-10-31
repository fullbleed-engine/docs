// SPDX-License-Identifier: MIT
// Read only the stored, single-volume ZIP format produced by Download project.
// ZIP fields: https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
const generation = new URL(import.meta.url).search;
const { crc32 } = await import(`./zip-store.js${generation}`);
const { assetKey, isFont, validateName, validateAssets, validateSource } = await import(`./local-files.js${generation}`);
const decoder = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true });
export const projectLimits = Object.freeze({ bytes: 24 * 1024 * 1024, entries: 64, metadata: 128 * 1024 });
const invalidZip = 'Choose an unchanged ZIP from Download project. For extracted or edited files, use Open local files.';
const invalidManifest = 'This ZIP does not contain a supported playground project. Use Open local files for individual files.';
const require = (condition, message = invalidZip) => { if (!condition) throw new Error(message); };

function utf8(bytes, name) {
  try { return decoder.decode(bytes); }
  catch { throw new Error(`${name} must be UTF-8 text.`); }
}

function metadata(bytes, name) {
  require(bytes && bytes.length <= projectLimits.metadata, invalidManifest);
  try { return JSON.parse(utf8(bytes, name)); }
  catch { throw new Error(`${name} is not valid project metadata.`); }
}

async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}

function storedFiles(bytes) {
  require(bytes.length >= 22);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const u16 = offset => view.getUint16(offset, true);
  const u32 = offset => view.getUint32(offset, true);
  const end = bytes.length - 22;
  require(u32(end) === 0x06054b50 && u16(end + 4) === 0 && u16(end + 6) === 0 && u16(end + 20) === 0);
  const count = u16(end + 10), start = u32(end + 16);
  require(count > 0 && count <= projectLimits.entries && u16(end + 8) === count);
  require(start + u32(end + 12) === end);
  const files = new Map(), keys = new Set();
  let directory = start, local = 0;
  for (let index = 0; index < count; index++) {
    require(directory + 46 <= end && u32(directory) === 0x02014b50);
    // Reject compression, encryption, data descriptors, ZIP64 and extra records.
    require(u16(directory + 6) === 20 && u16(directory + 8) === 0x800 && u16(directory + 10) === 0);
    const size = u32(directory + 24), length = u16(directory + 28), crc = u32(directory + 16);
    require(u32(directory + 20) === size && length > 0 && length <= 512);
    require(u16(directory + 30) === 0 && u16(directory + 32) === 0 && u16(directory + 34) === 0);
    require((u32(directory + 38) >>> 16 & 0xf000) === 0x8000 && u32(directory + 42) === local);
    require(directory + 46 + length <= end && local + 30 + length + size <= start);
    const name = utf8(bytes.subarray(directory + 46, directory + 46 + length), 'ZIP filename');
    require(name.split('/').length <= 2);
    for (const part of name.split('/')) validateName(part);
    require(!keys.has(assetKey(name)));
    keys.add(assetKey(name));
    require(u32(local) === 0x04034b50 && u16(local + 4) === 20 && u16(local + 6) === 0x800 && u16(local + 8) === 0);
    require(u32(local + 14) === crc && u32(local + 18) === size && u32(local + 22) === size);
    require(u16(local + 26) === length && u16(local + 28) === 0);
    for (let i = 0; i < length; i++) require(bytes[local + 30 + i] === bytes[directory + 46 + i]);
    const content = bytes.subarray(local + 30 + length, local + 30 + length + size);
    require(crc32(content) === crc, 'A file in this project is damaged. Choose the original downloaded ZIP.');
    files.set(name, content);
    local += 30 + length + size;
    directory += 46 + length;
  }
  require(local === start && directory === end);
  return files;
}

export async function readProject(file) {
  require(file && Number.isSafeInteger(file.size) && file.size >= 22 && file.size <= projectLimits.bytes,
    'Choose a playground project ZIP no larger than 24 MiB. Larger projects can still be rendered locally.');
  const bytes = new Uint8Array(await file.arrayBuffer());
  require(bytes.length === file.size, 'Could not read the whole project. Choose the file again.');
  const files = storedFiles(bytes);
  const manifest = metadata(files.get('project.json'), 'project.json');
  require(manifest?.format === 1 && manifest.source === 'https://docs.fullbleed.dev/playground/'
    && ['invoice', 'report', 'notice', 'custom'].includes(manifest.example)
    && manifest.engine?.name === 'fullbleed' && /^\d{1,5}\.\d{1,5}\.\d{1,5}$/.test(manifest.engine.version), invalidManifest);
  const node = manifest.runtime !== undefined;
  require(!node || (manifest.runtime?.name === 'node' && manifest.runtime.package?.name === 'fullbleed'
    && /^\d{1,5}\.\d{1,5}\.\d{1,5}$/.test(manifest.runtime.package.version)), invalidManifest);
  require(Array.isArray(manifest.files) && manifest.files.length === files.size - 1, invalidManifest);
  const recorded = new Set();
  for (const entry of manifest.files) {
    require(entry && typeof entry.path === 'string' && entry.path !== 'project.json' && files.has(entry.path)
      && !recorded.has(entry.path) && Number.isSafeInteger(entry.bytes) && /^[a-f0-9]{64}$/.test(entry.sha256), invalidManifest);
    const content = files.get(entry.path);
    require(content.length === entry.bytes && await sha256(content) === entry.sha256,
      'Project files no longer match their saved hashes. Use the original ZIP, or Open local files for edited source.');
    recorded.add(entry.path);
  }
  const expected = new Set(['project.json', 'input.html', 'style.css', 'README.txt', 'LICENSE.txt', 'fonts/font-sources.json',
    ...(node ? ['render.mjs', 'package.json', 'package-lock.json'] : ['render.py', 'requirements.txt'])]);
  const fonts = metadata(files.get('fonts/font-sources.json'), 'fonts/font-sources.json');
  require(Array.isArray(fonts?.files) && fonts.files.length > 0 && fonts.files.length <= 32, invalidManifest);
  for (const font of fonts.files) {
    require(font && typeof font.file === 'string' && /^[A-Za-z0-9-]+\.(ttf|txt)$/.test(font.file), invalidManifest);
    const path = `fonts/${font.file}`, content = files.get(path);
    require(!expected.has(path) && content && content.length === font.bytes && await sha256(content) === font.sha256, invalidManifest);
    expected.add(path);
  }
  require(manifest.localAssets === undefined || Array.isArray(manifest.localAssets), invalidManifest);
  const assets = [];
  for (const asset of manifest.localAssets ?? []) {
    require(asset && typeof asset.path === 'string' && asset.path.startsWith('assets/') && files.has(asset.path)
      && !expected.has(asset.path) && asset.font === isFont(asset.path), invalidManifest);
    expected.add(asset.path);
    assets.push({ name: asset.path.slice(7), bytes: files.get(asset.path) });
  }
  require(expected.size === files.size && [...expected].every(path => files.has(path)), invalidManifest);
  const html = utf8(files.get('input.html'), 'input.html'), css = utf8(files.get('style.css'), 'style.css');
  validateSource(html, css);
  validateAssets(assets);
  // Only source and custom assets enter the editor. No archived code is executed.
  return { html, css, language: node ? 'node' : 'python', engineVersion: manifest.engine.version,
    assets: assets.map(asset => ({ name: asset.name, bytes: asset.bytes.slice() })) };
}
