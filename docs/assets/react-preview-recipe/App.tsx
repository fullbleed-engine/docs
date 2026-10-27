// SPDX-License-Identifier: MIT
import { useMemo, useState } from 'react';
import { usePdfPreview } from './usePdfPreview';
import { Invoice } from './documents/Invoice';
import { sample } from './documents/data';

const assetBaseUrl = new URL('fullbleed/', new URL(import.meta.env.BASE_URL, location.href)).href;

function InvoiceEditor() {
  const [customer, setCustomer] = useState('Maple & Finch');
  const [paid, setPaid] = useState(false);
  const [auto, setAuto] = useState(true);
  const input = useMemo(() => customer.trim() ? {
    document: Invoice({ data: { ...sample, customer: customer.trim(), paid } }),
    previewDpi: 96, maxPages: 20, timeoutMs: 30_000,
  } : null, [customer, paid]);
  const pdf = usePdfPreview(input, assetBaseUrl, { auto });
  const pending = pdf.status === 'queued' || pdf.status === 'rendering';

  return <div className="workspace">
    <section className="controls" aria-label="Invoice fields">
      <h2>Change the details</h2>
      <label htmlFor="customer">Customer name</label>
      <input id="customer" value={customer} maxLength={100}
        onChange={event => setCustomer(event.target.value)} />
      <label className="auto-toggle">
        <input type="checkbox" checked={paid}
          onChange={event => setPaid(event.target.checked)} />Paid in full
      </label>
      <label className="auto-toggle">
        <input type="checkbox" checked={auto}
          onChange={event => setAuto(event.target.checked)} />Update automatically
      </label>
      <div className="actions">
        <button disabled={!input} onClick={() => void pdf.generate()}>Generate PDF</button>
        {pending && <button className="secondary" onClick={pdf.cancel}>Cancel</button>}
      </div>
      <p role="status" id="status">
        {!input ? 'Enter a customer name.' : pdf.error?.message ?? pdf.status}
      </p>
      <p className="sample-note">Fictional data. The sample rows and dates stay fixed.</p>
    </section>
    <section className="preview-panel" aria-label="PDF preview" aria-busy={pending}>
      <div className="preview-toolbar">
        <h2>The actual PDF</h2>
        {pdf.result && <a className="button" href={pdf.result.url}
          download="invoice.pdf">Download PDF</a>}
      </div>
      <div className="preview-area">
        {pdf.result?.previews.map((url, index) =>
          <img key={url} src={url} alt={`PDF page ${index + 1}`} />)}
      </div>
    </section>
  </div>;
}

export default function App() {
  const [open, setOpen] = useState(true);
  return <main>
    <div className="intro"><p className="eyebrow">REACT + TYPESCRIPT / FULLBLEED</p>
      <h1>A form edit.<br />A fresh PDF.</h1>
      <p className="lede">Reusable document components, local rendering, and a download that follows your changes.</p>
    </div>
    <div className="workspace-switch">
      <span>Invoice preview</span>
      <button className="text-button" onClick={() => setOpen(value => !value)}>
        {open ? 'Close editor' : 'Open editor'}
      </button>
    </div>
    {open && <InvoiceEditor />}
  </main>;
}
