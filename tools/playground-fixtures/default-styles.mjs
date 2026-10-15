// SPDX-License-Identifier: MIT
// Exercise inherited fonts and cascade rules without adding adapter CSS.
export const defaultStyleFixtures = [
  ['default', ''],
  ['html-inheritance', 'html { font-family: "DM Serif Display"; }'],
  ['body-explicit', 'body { font-family: "DM Serif Display"; }'],
  ['universal', '* { font-family: "DM Serif Display"; }'],
  ['low-specificity', ':where(body) { font-family: "DM Serif Display"; }'],
  ['layered-body', '@layer design { body { font-family: "DM Serif Display"; } }'],
].map(([name, rules]) => ({
  name: 'styles-' + name, pages: 1,
  html: '<html><body><p>Faithful export: same template, same type.</p></body></html>',
  css: '@page { size: 360px 120px; margin: 12px; } p { font-size: 20px; } ' + rules,
}));
