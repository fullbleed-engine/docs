// SPDX-License-Identifier: MIT
import { exampleSourcePath, prepareExample } from './examples.js?v=page-fonts-2548';

const assetGeneration = new URL(import.meta.url).search;
const { buildProject } = await import(`./project-export.js${assetGeneration}`);
const { readProject } = await import(`./project-import.js${assetGeneration}`);
const { readSelection, validateSource } = await import(`./local-files.js${assetGeneration}`);
const engineVersion = '2.5.51';

const el = id => document.getElementById(`pg-${id}`);
const html = el('html'), css = el('css'), picker = el('example');
const projectLanguage = el('project-language');
const originals = new Map(), edits = new Map();
const savedSources = new Map();
let current = 'invoice', worker = null, deadline = null, pageIndex = 0, pages = [], pdfUrl = null;
let renderedSource = null;
let localAssets = [], assetVersion = 0;
let savedAssets = localAssets;
const loadFailureMessage = 'The rendering engine could not load. Check your connection, then choose Render PDF again.';
const narrowWorkspace = window.matchMedia('(max-width: 850px)');
let workspaceView = 'preview';

function selectView(name) {
  workspaceView = name;
  for (const view of ['source', 'preview']) {
    el(`view-${view}`).setAttribute('aria-pressed', String(view === name));
  }
  el('editor').hidden = narrowWorkspace.matches && name !== 'source';
  el('output').hidden = narrowWorkspace.matches && name !== 'preview';
}

function resizeWorkspace() {
  const focused = document.activeElement;
  // Keep a focused editor or preview control available across a breakpoint.
  if (el('editor').contains(focused)) workspaceView = 'source';
  else if (el('output').contains(focused)) workspaceView = 'preview';
  el('view').hidden = !narrowWorkspace.matches;
  el('tools').open = !narrowWorkspace.matches || el('tools').contains(focused);
  selectView(workspaceView);
  if (!narrowWorkspace.matches && el('view').contains(focused)) {
    el(workspaceView === 'source' ? 'editor' : 'output').focus({ preventScroll: true });
  }
}

for (const view of ['source', 'preview']) el(`view-${view}`).addEventListener('click', () => selectView(view));
narrowWorkspace.addEventListener('change', resizeWorkspace);
resizeWorkspace();

function status(message, error = false) {
  el('status').textContent = message;
  el('status').dataset.error = String(error);
}

function changedSinceRender() {
  return !renderedSource || renderedSource.html !== html.value || renderedSource.css !== css.value
    || renderedSource.assetVersion !== assetVersion;
}

function beforeUnload(event) {
  event.preventDefault();
  event.returnValue = true;
}

// Textareas normalize CRLF and CR to LF without a user edit.
const sourceValue = value => value.replace(/\r\n?/g, '\n');

function sourceSaves(name) {
  return savedSources.get(name) || {
    html: new Set([sourceValue(originals.get(name).html)]),
    css: new Set([sourceValue(originals.get(name).css)]),
  };
}

function rememberSource(name, source) {
  const saved = sourceSaves(name);
  for (const [language, value] of Object.entries(source)) saved[language].add(sourceValue(value));
  savedSources.set(name, saved);
}

function updateLeaveGuard() {
  const changedAssets = localAssets.length !== savedAssets.length
    || localAssets.some((asset, index) => asset !== savedAssets[index]);
  const changedSource = [...originals].some(([name, original]) => {
    const source = name === current
      ? { html: html.value, css: css.value }
      : edits.get(name) || original;
    const saved = sourceSaves(name);
    return !saved.html.has(sourceValue(source.html)) || !saved.css.has(sourceValue(source.css));
  });
  if (changedAssets || changedSource) window.addEventListener('beforeunload', beforeUnload);
  else window.removeEventListener('beforeunload', beforeUnload);
}

function setDownload(enabled) {
  const link = el('download');
  link.setAttribute('aria-disabled', String(!enabled));
  if (enabled && pdfUrl) { link.href = pdfUrl; link.download = `fullbleed-${current}.pdf`; }
  else link.removeAttribute('href');
}

function clearOutput() {
  for (const url of pages) URL.revokeObjectURL(url);
  pages = [];
  if (pdfUrl) URL.revokeObjectURL(pdfUrl);
  pdfUrl = null;
  renderedSource = null;
  el('preview').hidden = true;
  el('preview').removeAttribute('src');
  el('placeholder').hidden = false;
  el('placeholder').textContent = 'Render your document to see it here.';
  el('page-count').textContent = '—';
  el('result').textContent = `Fullbleed ${engineVersion}`;
  el('previous').disabled = el('next').disabled = true;
  setDownload(false);
}

function finish() {
  clearTimeout(deadline);
  if (worker) worker.terminate();
  worker = null;
  el('render').disabled = false;
  el('cancel').hidden = true;
  document.querySelector('.pg-output').setAttribute('aria-busy', 'false');
}

function showPage(index) {
  pageIndex = index;
  el('preview').src = pages[index];
  el('preview').alt = `Fullbleed-generated PDF preview, page ${index + 1} of ${pages.length}. Download the PDF or read its HTML source for the document content.`;
  el('preview').hidden = false;
  el('placeholder').hidden = true;
  el('page-count').textContent = `${index + 1} / ${pages.length}`;
  el('previous').disabled = index === 0;
  el('next').disabled = index === pages.length - 1;
}

function fail(message) {
  finish();
  status(message, true);
  if (!pages.length) el('placeholder').textContent = 'Your edits and local files are still here.';
}

function startRender({ preview = false } = {}) {
  if (worker) finish();
  const source = { html: html.value, css: css.value, assets: localAssets, assetVersion };
  if (new TextEncoder().encode(source.html + source.css).length > 200000) {
    status('This playground accepts up to 200 KB of HTML and CSS combined.', true);
    return;
  }
  if (typeof Worker === 'undefined' || typeof WebAssembly === 'undefined') {
    status('This browser cannot run the playground. Use the Python quickstart below.', true);
    return;
  }
  if (preview && narrowWorkspace.matches) {
    selectView('preview');
    el('tools').open = false;
  }
  setDownload(false);
  el('render').disabled = true;
  el('cancel').hidden = false;
  document.querySelector('.pg-output').setAttribute('aria-busy', 'true');
  status('Loading the engine and fonts…');
  try {
    const workerUrl = new URL('./worker.js', import.meta.url);
    workerUrl.search = assetGeneration;
    worker = new Worker(workerUrl, { type: 'module' });
    // Asset downloads have a separate allowance from the 30-second render limit.
    deadline = setTimeout(() => fail('The engine download took too long. Check your connection, then choose Render PDF again.'), 90000);
    worker.onerror = () => fail(loadFailureMessage);
    worker.onmessage = ({ data }) => {
      if (data.type === 'progress') {
        status(data.message);
        if (data.message === 'Rendering your PDF…') {
          clearTimeout(deadline);
          deadline = setTimeout(() => fail('Rendering stopped after 30 seconds. Simplify this document or render it locally.'), 30000);
        }
        return;
      }
      if (data.type === 'error') { fail(data.phase === 'loading' ? loadFailureMessage : data.message); return; }
      if (data.type !== 'complete') return;
      clearOutput();
      pdfUrl = URL.createObjectURL(new Blob([data.pdf], { type: 'application/pdf' }));
      pages = data.pages.map(bytes => URL.createObjectURL(new Blob([bytes], { type: 'image/png' })));
      renderedSource = source;
      showPage(0);
      const count = data.report.pages;
      el('result').textContent = `${count} ${count === 1 ? 'page' : 'pages'} · ${(data.pdf.length / 1024).toFixed(0)} KB · Fullbleed ${data.report.engine}`;
      finish();
      setDownload(!changedSinceRender());
      if (changedSinceRender()) status('Source changed during rendering. Render again to update the PDF.');
      else if (data.report.missing_glyphs) status(`PDF created, but ${data.report.missing_glyphs} character(s) have no glyph in the available fonts. Review the output before using it.`, true);
      else status('Your PDF is ready.');
    };
    worker.postMessage(source);
  } catch (error) { fail(error.message); }
}

function selectTab(language, focus = false) {
  for (const name of ['html', 'css']) {
    const active = language === name;
    el(`${name}-tab`).setAttribute('aria-selected', String(active));
    el(`${name}-tab`).tabIndex = active ? 0 : -1;
    el(`${name}-panel`).hidden = !active;
  }
  if (focus) el(`${language}-tab`).focus();
}

function saveText(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a');
  link.href = url; link.download = name;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function showAssets() {
  const list = el('assets');
  list.replaceChildren();
  el('asset-count').textContent = `${localAssets.length} local ${localAssets.length === 1 ? 'asset' : 'assets'}`;
  el('asset-help').hidden = localAssets.length === 0;
  for (const asset of localAssets) {
    const row = document.createElement('li'), name = document.createElement('code'), remove = document.createElement('button');
    name.textContent = `assets/${asset.name}`;
    remove.textContent = 'Remove';
    remove.setAttribute('aria-label', `Remove ${asset.name}`);
    remove.addEventListener('click', () => {
      localAssets = localAssets.filter(item => item !== asset);
      assetVersion++;
      showAssets();
      updateLeaveGuard();
      setDownload(!changedSinceRender());
      status('Asset removed. Render again to update the PDF.');
      el('open-files').focus();
    });
    row.append(name, remove);
    list.append(row);
  }
}

el('open-files').addEventListener('click', () => el('files').click());
el('files').addEventListener('change', async () => {
  const files = Array.from(el('files').files);
  if (!files.length) return;
  const snapshot = { current, html: html.value, css: css.value, assetVersion };
  el('open-files').disabled = true;
  el('open-project').disabled = true;
  status('Opening selected files on your device…');
  try {
    const selected = await readSelection(files, localAssets);
    if (current !== snapshot.current || html.value !== snapshot.html || css.value !== snapshot.css || assetVersion !== snapshot.assetVersion) {
      throw new Error('Your document changed while the files were opening. Choose the files again to apply them.');
    }
    const hasSource = selected.html !== null || selected.css !== null;
    const nextHtml = selected.html ?? html.value;
    const nextCss = selected.css ?? (selected.html !== null ? '' : css.value);
    if (hasSource) validateSource(nextHtml, nextCss);
    if (worker) finish();
    if (hasSource) {
      const previousSaved = sourceSaves(current);
      edits.set(current, { html: html.value, css: css.value });
      current = 'custom';
      originals.set(current, { html: nextHtml, css: nextCss });
      // A CSS-only import must not mark retained, edited HTML as saved.
      savedSources.set(current, {
        html: selected.html !== null ? new Set([sourceValue(nextHtml)]) : new Set(previousSaved.html),
        css: new Set([sourceValue(nextCss)]),
      });
      edits.delete(current);
      if (!picker.querySelector('option[value="custom"]')) picker.add(new Option('Your document', 'custom'));
      picker.value = current;
      html.value = nextHtml; css.value = nextCss;
      el('reset').textContent = 'Reset document';
      selectTab(selected.html !== null ? 'html' : 'css');
      selectView('source');
    }
    localAssets = [...localAssets, ...selected.assets];
    assetVersion++;
    showAssets();
    updateLeaveGuard();
    clearOutput();
    status('Files opened locally. Use assets/filename for images and font files, then Render PDF.');
  } catch (error) {
    status(error.message || 'Could not open the selected files.', true);
  } finally {
    el('files').value = '';
    el('open-files').disabled = false;
    el('open-project').disabled = false;
  }
});

el('open-project').addEventListener('click', () => el('project-file').click());
el('project-file').addEventListener('change', async () => {
  const file = el('project-file').files[0];
  if (!file) return;
  const snapshot = { current, html: html.value, css: css.value, assetVersion, language: projectLanguage.value };
  el('open-project').disabled = el('open-files').disabled = true;
  status('Checking the saved project on your device…');
  try {
    const project = await readProject(file);
    if (current !== snapshot.current || html.value !== snapshot.html || css.value !== snapshot.css
        || assetVersion !== snapshot.assetVersion || projectLanguage.value !== snapshot.language) {
      throw new Error('Your document changed while the project was opening. Choose the ZIP again to apply it.');
    }
    if (worker) finish();
    edits.set(current, { html: html.value, css: css.value });
    current = 'custom';
    originals.set(current, { html: project.html, css: project.css });
    savedSources.delete(current);
    edits.delete(current);
    if (!picker.querySelector('option[value="custom"]')) picker.add(new Option('Your document', 'custom'));
    picker.value = current;
    html.value = project.html; css.value = project.css;
    projectLanguage.value = project.language;
    localAssets = project.assets;
    savedAssets = localAssets;
    assetVersion++;
    el('reset').textContent = 'Reset document';
    el('project-status').hidden = true;
    selectTab('html');
    selectView('source');
    showAssets();
    updateLeaveGuard();
    clearOutput();
    const versionNote = project.engineVersion === engineVersion ? ''
      : ` This project was saved with Fullbleed ${project.engineVersion}; this playground uses ${engineVersion}.`;
    status(`Project opened locally.${versionNote} Choose Render PDF to preview with this playground’s engine and bundled fonts.`);
  } catch (error) {
    status(error.message || 'Could not open the saved project.', true);
  } finally {
    el('project-file').value = '';
    el('open-project').disabled = el('open-files').disabled = false;
  }
});

for (const language of ['html', 'css']) {
  el(`${language}-tab`).addEventListener('click', () => selectTab(language));
  el(`${language}-tab`).addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 'html' : event.key === 'End' ? 'css' : language === 'html' ? 'css' : 'html';
    selectTab(next, true);
  });
  el(language).addEventListener('input', () => {
    edits.set(current, { html: html.value, css: css.value });
    updateLeaveGuard();
    setDownload(!changedSinceRender());
    if (!worker) status(changedSinceRender() ? 'You have changes. Render to update the PDF.' : 'Your PDF matches the current source.');
  });
  el(language).addEventListener('keydown', event => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault(); if (!worker) startRender();
    }
  });
  el(`save-${language}`).addEventListener('click', event => {
    event.preventDefault();
    saveText(`fullbleed-${current}.${language}`, el(language).value, language === 'html' ? 'text/html;charset=utf-8' : 'text/css;charset=utf-8');
    rememberSource(current, { [language]: el(language).value });
    updateLeaveGuard();
  });
}
el('render').addEventListener('click', () => startRender({ preview: true }));
el('cancel').addEventListener('click', () => { finish(); status('Rendering canceled. Your source is still here.'); setDownload(!changedSinceRender()); });
el('previous').addEventListener('click', () => showPage(pageIndex - 1));
el('next').addEventListener('click', () => showPage(pageIndex + 1));
el('project').addEventListener('click', async () => {
  const button = el('project'), message = el('project-status');
  // Capture edits before downloading assets, even if the user keeps typing or switches examples.
  const snapshot = { name: current, html: html.value, css: css.value, language: projectLanguage?.value ?? 'python', assets: localAssets, assetVersion };
  button.disabled = true;
  button.textContent = 'Preparing project…';
  message.hidden = false;
  message.dataset.error = 'false';
  message.textContent = `Preparing your HTML, CSS, fonts, and ${snapshot.language === 'node' ? 'Node.js' : 'Python'} renderer…`;
  try {
    const bytes = await buildProject(snapshot);
    saveText(`fullbleed-${snapshot.name}-${snapshot.language === 'node' ? 'node-' : ''}project.zip`, bytes, 'application/zip');
    rememberSource(snapshot.name, { html: snapshot.html, css: snapshot.css });
    savedAssets = snapshot.assets;
    updateLeaveGuard();
    const newerEdits = current !== snapshot.name || html.value !== snapshot.html || css.value !== snapshot.css
      || assetVersion !== snapshot.assetVersion || (projectLanguage?.value ?? 'python') !== snapshot.language;
    message.textContent = newerEdits
      ? 'Project downloaded with the source and language from when you clicked. Download again to include newer changes.'
      : 'Project downloaded. Reopen it here with Open saved project, or extract the ZIP and follow its README to render locally.';
  } catch (error) {
    message.textContent = error.message || 'Could not download the project. Try again.';
    message.dataset.error = 'true';
  } finally {
    button.disabled = false;
    button.textContent = 'Download project';
  }
});
el('reset').addEventListener('click', () => {
  if (worker) finish();
  edits.delete(current);
  html.value = originals.get(current).html; css.value = originals.get(current).css;
  updateLeaveGuard();
  clearOutput(); startRender();
});
picker.addEventListener('change', () => {
  if (worker) finish();
  edits.set(current, { html: html.value, css: css.value });
  current = picker.value;
  el('reset').textContent = current === 'custom' ? 'Reset document' : 'Reset example';
  const source = edits.get(current) || originals.get(current);
  html.value = source.html; css.value = source.css;
  updateLeaveGuard();
  clearOutput(); startRender();
});
window.addEventListener('pagehide', () => { if (worker) finish(); });

try {
  await Promise.all(['invoice', 'report', 'notice'].map(async name => {
    const parts = await Promise.all(['html', 'css'].map(async extension => {
      const response = await fetch(new URL(exampleSourcePath(name, extension), import.meta.url));
      if (!response.ok) throw new Error('Could not load the examples. Reload this page to try again.');
      return response.text();
    }));
    originals.set(name, prepareExample(name, parts[0], parts[1]));
  }));
  const hashExample = location.hash.slice(1);
  if (originals.has(hashExample)) current = hashExample;
  picker.value = current;
  html.value = originals.get(current).html; css.value = originals.get(current).css;
  for (const control of [html, css, picker, el('reset'), el('render'), el('project'), el('open-files'), el('open-project'), projectLanguage].filter(Boolean)) control.disabled = false;
  for (const language of ['html', 'css']) { el(`save-${language}`).href = '#'; el(`save-${language}`).setAttribute('aria-disabled', 'false'); }
  startRender();
} catch (error) { status(error.message, true); document.querySelector('.pg-output').setAttribute('aria-busy', 'false'); }
