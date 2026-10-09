<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Invoice {{ $invoice['number'] }}</title></head>
<body>
<header><div class="brand">F / B</div><div class="studio">NORTHLINE<br><span>DESIGN &amp; BUILD STUDIO</span></div><div class="edition">PROJECT ACCOUNTS<br>2026 / USD</div></header>
<div class="rule"></div>
<div class="hero"><div class="label">GOOD WORK. CLEAR NUMBERS.</div><h1>INVOICE</h1><div class="number">{{ $invoice['number'] }}</div></div>
<section class="details"><div class="client"><div class="label">PREPARED FOR</div><h2>{{ $invoice['customer'] }}</h2></div><div class="dates"><p><b>ISSUED</b> {{ $invoice['issued'] }}</p><p><b>DUE</b> {{ $invoice['due'] }}</p></div></section>
<table><thead><tr><th class="description">PROJECT / DELIVERABLE</th><th>QTY</th><th>RATE / USD</th><th>AMOUNT / USD</th></tr></thead><tbody>
@foreach ($invoice['items'] as $item)
<tr><td>{{ $item['description'] }}</td><td class="numeric">{{ $item['quantity'] }}</td><td class="numeric">{{ $item['unit_price'] }}</td><td class="numeric">{{ $item['amount'] }}</td></tr>
@endforeach
</tbody></table>
<section class="summary"><div class="note"><b>BUILT WITH CARE.</b><p>Thank you for making room for good work.<br>Please include the invoice number with your payment.</p></div><div class="amount"><div class="label">PROJECT TOTAL · USD</div><p class="{{ strlen($total) > 12 ? 'compact' : '' }}">{{ $total }}</p></div></section>
<footer><b>NORTHLINE / ACCOUNTS</b><span>Illustrative invoice · no tax calculation · synthetic data</span></footer>
</body></html>
