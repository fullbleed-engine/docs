'use strict';
const el = id => document.getElementById(id);
el('invoice').value = JSON.stringify(window.sampleInvoice, null, 2);
let documentStatus = null;
let requestKey = null;
let previousInput = null;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {
    Accept: 'application/json', Authorization: `Bearer ${el('key').value}`,
    ...options.headers,
  }});
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.message || `Request failed (${response.status}).`);
  }
  return response;
}
el('invoice-form').addEventListener('submit', async event => {
  event.preventDefault();
  el('submit').disabled = true;
  el('download').hidden = true;
  for (const id of ['accepted', 'rendered', 'downloaded']) el(id).classList.remove('done');
  try {
    const body = JSON.stringify(JSON.parse(el('invoice').value));
    // A retry of unchanged data reuses its key, even after a network failure.
    if (body !== previousInput) { previousInput = body; requestKey = crypto.randomUUID(); }
    documentStatus = await (await api('/api/documents', {method: 'POST',
      headers: {'Content-Type': 'application/json', 'Idempotency-Key': requestKey}, body})).json();
    el('accepted').classList.add('done');
    for (let attempt = 0; attempt < 90; attempt++) {
      el('state').textContent = documentStatus.state === 'processing' ? 'Putting ink to paper.' : 'In the queue.';
      el('detail').textContent = `Document ${documentStatus.id}. Waiting for the queue worker.`;
      if (documentStatus.state === 'ready') {
        el('state').textContent = 'Your invoice is ready.';
        el('detail').textContent = `Private download available until ${new Date(documentStatus.expires_at).toLocaleString()}.`;
        el('rendered').classList.add('done'); el('downloaded').classList.add('done');
        el('download').hidden = false;
        return;
      }
      if (documentStatus.state === 'failed') throw new Error('Rendering failed after retries. Check the worker installation and template, then use Laravel queue:retry.');
      await pause(1500);
      documentStatus = await (await api(documentStatus.status_url)).json();
    }
    throw new Error('Still waiting for the worker. Start php artisan queue:work --queue=pdf, then submit unchanged data to check the same document.');
  } catch (error) {
    el('state').textContent = 'Needs your attention.';
    el('detail').textContent = error.message;
  } finally { el('submit').disabled = false; }
});
el('download').addEventListener('click', async () => {
  el('download').disabled = true;
  try {
    const response = await api(documentStatus.download_url);
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${documentStatus.id}.pdf`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { el('detail').textContent = error.message; }
  finally { el('download').disabled = false; }
});
