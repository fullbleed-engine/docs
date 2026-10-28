// SPDX-License-Identifier: MIT
// Selected files remain in tab memory and the worker's virtual filesystem.
export const limits = Object.freeze({ source: 200000, file: 8 * 1024 * 1024, assets: 20 * 1024 * 1024, count: 16 });
const sourceExtensions = new Set(['html', 'htm', 'css']);
const assetExtensions = new Set(['png', 'jpg', 'jpeg', 'svg', 'ttf', 'otf', 'txt']);
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });

export const assetKey = name => name.normalize('NFC').toLowerCase();
export const isFont = name => /\.(ttf|otf)$/i.test(name);

export function validateName(name) {
  if (typeof name !== 'string' || !name || name.length > 120 || /^[. ]|[. ]$/.test(name)
      || /[<>:"/\\|?*\x00-\x1f\x7f]/.test(name)
      || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) {
    throw new Error('Use a filename of up to 120 characters without folders or reserved filename characters.');
  }
  return name.split('.').at(-1).toLowerCase();
}

function text(bytes, name) {
  try { return decoder.decode(bytes); }
  catch { throw new Error(`${name} must be a UTF-8 text file.`); }
}

function validateAsset(asset) {
  const ext = validateName(asset.name);
  if (!assetExtensions.has(ext)) throw new Error('Choose PNG, JPEG, SVG, TTF, OTF, or TXT assets.');
  const bytes = asset.bytes;
  if (!(bytes instanceof Uint8Array) || !bytes.length || bytes.length > limits.file) {
    throw new Error(`Each asset must contain data and be no larger than 8 MiB: ${asset.name}`);
  }
  const starts = values => values.every((value, i) => bytes[i] === value);
  if (ext === 'png' && !starts([137, 80, 78, 71, 13, 10, 26, 10])) throw new Error(`${asset.name} is not a PNG file.`);
  if (['jpg', 'jpeg'].includes(ext) && !starts([255, 216, 255])) throw new Error(`${asset.name} is not a JPEG file.`);
  if (ext === 'ttf' && !starts([0, 1, 0, 0]) && !starts([116, 114, 117, 101])) throw new Error(`${asset.name} is not a TrueType font.`);
  if (ext === 'otf' && !starts([79, 84, 84, 79])) throw new Error(`${asset.name} is not an OpenType font.`);
  if (ext === 'svg' && !/<svg(?:\s|\/?>)/i.test(text(bytes, asset.name))) throw new Error(`${asset.name} is not an SVG file.`);
  if (ext === 'txt') text(bytes, asset.name);
}

export function validateAssets(assets = []) {
  if (!Array.isArray(assets) || assets.length > limits.count) throw new Error('This playground accepts up to 16 local assets.');
  let size = 0;
  const names = new Set();
  for (const asset of assets) {
    validateAsset(asset);
    const key = assetKey(asset.name);
    if (names.has(key)) throw new Error(`An asset named ${asset.name} is already present. Remove it before adding its replacement.`);
    names.add(key);
    size += asset.bytes.length;
  }
  if (size > limits.assets) throw new Error('Local assets must total no more than 20 MiB.');
  return assets;
}

export function validateSource(html, css) {
  if (typeof html !== 'string' || typeof css !== 'string' || encoder.encode(html + css).length > limits.source) {
    throw new Error('This playground accepts up to 200 KB of HTML and CSS combined.');
  }
}

// Validate the entire selection before the UI changes any source or asset state.
export async function readSelection(files, currentAssets = []) {
  if (!files.length || files.length > limits.count + 2) throw new Error('Choose one HTML file, one CSS file, and up to 16 assets.');
  const selected = [];
  let html = null, css = null;
  let assetCount = currentAssets.length, assetBytes = currentAssets.reduce((sum, asset) => sum + asset.bytes.length, 0);
  const sourceTypes = new Set();
  for (const file of files) {
    const ext = validateName(file.name);
    const kind = ext === 'htm' ? 'html' : ext;
    if (!sourceExtensions.has(ext) && !assetExtensions.has(ext)) throw new Error(`Unsupported file: ${file.name}`);
    const cap = sourceExtensions.has(ext) ? limits.source : limits.file;
    if (!Number.isSafeInteger(file.size) || file.size < 0 || file.size > cap) {
      throw new Error(`${file.name} exceeds the ${sourceExtensions.has(ext) ? '200 KB source' : '8 MiB asset'} limit.`);
    }
    if (sourceExtensions.has(ext)) {
      if (sourceTypes.has(kind)) throw new Error('Choose at most one HTML file and one CSS file at a time.');
      sourceTypes.add(kind);
    } else {
      assetCount++;
      assetBytes += file.size;
    }
    selected.push({ file, kind });
  }
  if (assetCount > limits.count) throw new Error('This playground accepts up to 16 local assets.');
  if (assetBytes > limits.assets) throw new Error('Local assets must total no more than 20 MiB.');
  const added = [];
  for (const { file, kind } of selected) {
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (bytes.length !== file.size) throw new Error(`Could not read all of ${file.name}. Choose the file again.`);
    if (kind === 'html') html = text(bytes, file.name);
    else if (kind === 'css') css = text(bytes, file.name);
    else added.push({ name: file.name, bytes });
  }
  validateAssets([...currentAssets, ...added]);
  return { html, css, assets: added };
}
