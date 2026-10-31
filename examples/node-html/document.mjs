// SPDX-License-Identifier: MIT
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);
const money = cents => '$' + (cents / 100).toFixed(2);
const read = (name, encoding) => readFile(new URL(name, import.meta.url), encoding);

export async function loadDocument(name) {
  if (!['short', 'long'].includes(name)) throw new Error('Choose short or long.');
  const records = JSON.parse(await read('./records.json', 'utf8'));
  const record = records[name];
  let total = 0;
  const rows = record.items.map(item => {
    if (!Number.isSafeInteger(item.quantity) || item.quantity <= 0 ||
        !Number.isSafeInteger(item.unitCents) || item.unitCents < 0) {
      throw new Error('Items need a positive integer quantity and nonnegative integer unitCents.');
    }
    const amount = item.quantity * item.unitCents;
    total += amount;
    if (!Number.isSafeInteger(amount) || !Number.isSafeInteger(total)) throw new Error('Amount exceeds the supported integer range.');
    return `<tr><td><strong>${escapeHtml(item.code)} · ${escapeHtml(item.name)}</strong>` +
      `<p class="detail">${escapeHtml(item.description)}</p></td>` +
      `<td class="number">${item.quantity}</td><td class="number">${money(item.unitCents)}</td>` +
      `<td class="number">${money(amount)}</td></tr>`;
  }).join('\n');
  const values = {
    css: await read('./print.css', 'utf8'), rows,
    reference: escapeHtml(record.reference), customer: escapeHtml(record.customer),
    address: record.address.map(escapeHtml).join('<br>'), date: escapeHtml(record.date),
    total: money(total), count: String(record.items.length),
  };
  const html = (await read('./template.html', 'utf8')).replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (!(key in values)) throw new Error('Unknown template field: ' + key);
    return values[key];
  });
  return {
    html, record, totalCents: total, inputSha256: digest(html),
    fonts: [
      { name: 'Brand-Regular.ttf', data: await read('./fonts/SourceSans3-Regular.ttf') },
      { name: 'Brand-Bold.ttf', data: await read('./fonts/SourceSans3-Bold.ttf') },
    ],
    assets: { 'logo.svg': await read('./assets/logo.svg') },
  };
}

export function selectedDocuments(value = 'all') {
  if (value === 'all') return ['short', 'long'];
  if (['short', 'long'].includes(value)) return [value];
  throw new Error('Choose short, long, or all.');
}
