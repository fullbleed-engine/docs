// SPDX-License-Identifier: MIT
import { buildProject } from './project-export.js';
import { prepareExample } from './examples.js';

const el = id => document.getElementById(`pg-${id}`);
const html = el('html'), css = el('css'), picker = el('example');
const originals = new Map(), edits = new Map();
let current = 'invoice', worker = null, deadline = null, pageIndex = 0, pages = [], pdfUrl = null;
let renderedSource = null;

function status(message, error = false) {
  el('status').textContent = message;
  el('status').dataset.error = String(error);
}

function changedSinceRender() {
  return !renderedSource || renderedSource.html !== html.value || renderedSource.css !== css.value;
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
  el('result').textContent = 'Fullbleed 2.5.5';
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
  if (!pages.length) el('placeholder').textContent = 'Adjust your source, then render again.';
}

function startRender() {
  if (worker) finish();
  const source = { html: html.value, css: css.value };
  if (new TextEncoder().encode(source.html + source.css).length > 200000) {
    status('This playground accepts up to 200 KB of HTML and CSS combined.', true);
    return;
  }
  if (typeof Worker === 'undefined' || typeof WebAssembly === 'undefined') {
    status('This browser cannot run the playground. Use the Python quickstart below.', true);
    return;
  }
  setDownload(false);
  el('render').disabled = true;
  el('cancel').hidden = false;
  document.querySelector('.pg-output').setAttribute('aria-busy', 'true');
  status('Loading the engine and fonts…');
  try {
    worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
    // Asset downloads have a separate allowance from the 30-second render limit.
    deadline = setTimeout(() => fail('The engine download took too long. Check your connection and retry.'), 90000);
    worker.onerror = () => fail('The playground could not start. Reload this page or use the Python quickstart below.');
    worker.onmessage = ({ data }) => {
      if (data.type === 'progress') {
        status(data.message);
        if (data.message === 'Rendering your PDF…') {
          clearTimeout(deadline);
          deadline = setTimeout(() => fail('Rendering stopped after 30 seconds. Simplify this document or render it locally.'), 30000);
        }
        return;
      }
      if (data.type === 'error') { fail(data.message); return; }
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
      else if (data.report.missing_glyphs) status(`PDF created, but ${data.report.missing_glyphs} character(s) have no glyph in the bundled fonts. Review the output before using it.`, true);
      else status('Your PDF is ready. Change the design, or download it and keep building.');
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
  });
}
el('render').addEventListener('click', startRender);
el('cancel').addEventListener('click', () => { finish(); status('Rendering canceled. Your source is still here.'); setDownload(!changedSinceRender()); });
el('previous').addEventListener('click', () => showPage(pageIndex - 1));
el('next').addEventListener('click', () => showPage(pageIndex + 1));
el('project').addEventListener('click', async () => {
  const button = el('project'), message = el('project-status');
  // Capture edits before downloading assets, even if the user keeps typing or switches examples.
  const snapshot = { name: current, html: html.value, css: css.value };
  button.disabled = true;
  button.textContent = 'Preparing project…';
  message.hidden = false;
  message.dataset.error = 'false';
  message.textContent = 'Preparing your HTML, CSS, fonts, and Python renderer…';
  try {
    const bytes = await buildProject(snapshot);
    saveText(`fullbleed-${snapshot.name}-project.zip`, bytes, 'application/zip');
    const newerEdits = current !== snapshot.name || html.value !== snapshot.html || css.value !== snapshot.css;
    message.textContent = newerEdits
      ? 'Project downloaded with the source from when you clicked. Download again to include newer edits.'
      : 'Project downloaded. Extract the ZIP and follow its README to render locally.';
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
  clearOutput(); startRender();
});
picker.addEventListener('change', () => {
  if (worker) finish();
  edits.set(current, { html: html.value, css: css.value });
  current = picker.value;
  const source = edits.get(current) || originals.get(current);
  html.value = source.html; css.value = source.css;
  clearOutput(); startRender();
});
window.addEventListener('pagehide', () => { if (worker) finish(); });

try {
  await Promise.all(['invoice', 'report', 'notice'].map(async name => {
    const parts = await Promise.all(['html', 'css'].map(async extension => {
      const response = await fetch(new URL(`../showcase/${name}.${extension}`, import.meta.url));
      if (!response.ok) throw new Error('Could not load the examples. Reload this page to try again.');
      return response.text();
    }));
    originals.set(name, prepareExample(name, parts[0], parts[1]));
  }));
  const hashExample = location.hash.slice(1);
  if (originals.has(hashExample)) current = hashExample;
  picker.value = current;
  html.value = originals.get(current).html; css.value = originals.get(current).css;
  for (const control of [html, css, picker, el('reset'), el('render'), el('project')]) control.disabled = false;
  for (const language of ['html', 'css']) { el(`save-${language}`).href = '#'; el(`save-${language}`).setAttribute('aria-disabled', 'false'); }
  startRender();
} catch (error) { status(error.message, true); document.querySelector('.pg-output').setAttribute('aria-busy', 'false'); }
