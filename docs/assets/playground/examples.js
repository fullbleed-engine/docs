// SPDX-License-Identifier: MIT
export function prepareExample(name, html, css) {
  // The downloadable showcase notice uses a tagged profile; this browser adapter uses ordinary output.
  if (name === 'notice') {
    html = html.replace('FICTIONAL SERVICE NOTICE / TAGGED DOCUMENT EXAMPLE',
                        'FICTIONAL SERVICE NOTICE / DOCUMENT DESIGN EXAMPLE');
  }
  return { html, css };
}
