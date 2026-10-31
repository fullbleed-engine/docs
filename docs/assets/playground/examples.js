// SPDX-License-Identifier: MIT
export function exampleSourcePath(name, extension) {
  if (!['invoice', 'report', 'notice'].includes(name) || !['html', 'css'].includes(extension)) {
    throw new Error('Unknown playground example source.');
  }
  return name === 'invoice' ? `./invoice.${extension}` : `../showcase/${name}.${extension}`;
}

export function prepareExample(name, html, css) {
  // The downloadable showcase notice uses a tagged profile; this browser adapter uses ordinary output.
  if (name === 'notice') {
    html = html.replace('FICTIONAL SERVICE NOTICE / TAGGED DOCUMENT EXAMPLE',
                        'FICTIONAL SERVICE NOTICE / DOCUMENT DESIGN EXAMPLE');
  }
  return { html, css };
}
