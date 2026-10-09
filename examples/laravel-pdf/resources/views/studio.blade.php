<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fullbleed Queue Studio</title><link rel="stylesheet" href="/studio.css"></head>
<body><header><a href="/" class="brand">FULLBLEED<span> / QUEUE STUDIO</span></a><span class="badge">LARAVEL + BLADE</span></header>
<main><section class="intro"><p class="eyebrow">FROM BUSINESS EVENT TO FINISHED DOCUMENT</p><h1>Your invoices.<br><em>Already in motion.</em></h1><p>A request goes in. A worker takes care of the PDF. Try the sample, then connect the same endpoint to your application.</p></section>
<div class="workspace"><section class="panel"><div class="step">01 / SUBMIT A DOCUMENT</div>
<form id="invoice-form"><label for="key">Service key</label><input id="key" type="password" autocomplete="off" required minlength="32" placeholder="Your PDF_API_KEY">
<p class="help">Used for this request and download. Kept only in this page.</p>
<label for="invoice">Invoice JSON</label><textarea id="invoice" spellcheck="false" rows="17" required></textarea>
<button type="submit" id="submit">Queue sample invoice <span>↗</span></button></form></section>
<section class="panel output"><div class="step">02 / FOLLOW THE WORK</div><div id="state" class="state" aria-live="polite">Ready when you are.</div>
<p id="detail">The PDF uses your Blade template, print CSS and bundled fonts. Start the queue worker before submitting.</p>
<ol class="timeline"><li id="accepted">Accepted by the API</li><li id="rendered">Rendered by the worker</li><li id="downloaded">Private PDF ready</li></ol>
<button id="download" hidden>Download PDF <span>↓</span></button>
<div class="artifact"><div class="artifact-brand">NORTHLINE / STUDIO</div><div class="artifact-title">INVOICE</div><div class="artifact-line"></div><div class="artifact-lines"><i></i><i></i><i></i></div><div class="artifact-total">BUILT WITH FULLBLEED</div></div>
<p class="help">Edit <code>resources/views/invoice.blade.php</code> and <code>renderer/invoice.css</code> to make the document your own.</p></section></div>
<footer>Fullbleed / MIT licensed <a href="https://docs.fullbleed.dev/guides/laravel-pdf/">Integration guide ↗</a></footer></main>
<script>window.sampleInvoice = {{ Illuminate\Support\Js::from(json_decode(file_get_contents(base_path('sample.json')), true)) }};</script>
<script src="/studio.js"></script></body></html>
