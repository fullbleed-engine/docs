# Generating Bank Statements

Bank statements are the canonical use case for Fullbleed's paginated context system. Each page needs running balances, transaction counts, and page-specific subtotals — all computed automatically.

## The Problem

Traditional PDF libraries force you to manually calculate which transactions land on which page, then compute per-page balances yourself. This means:

1. Pre-paginating your data (guessing line heights)
2. Calculating running totals manually
3. Injecting per-page headers/footers with the right numbers
4. Hoping nothing shifts when fonts change

Fullbleed does all of this in the engine. You provide flat HTML with data attributes, and the engine handles pagination math.

## Complete Example

```python
from fullbleed import PdfEngine
from datetime import date, timedelta
import random

# Generate realistic transaction data
transactions = []
balance = 5432.10
for i in range(75):
    d = date(2026, 2, 1) + timedelta(days=i % 28)
    is_credit = random.random() > 0.6
    amount = round(random.uniform(10, 500), 2)
    if not is_credit:
        amount = -amount
    balance += amount
    transactions.append({
        "date": d.strftime("%m/%d/%Y"),
        "desc": random.choice([
            "Direct Deposit - Payroll",
            "ACH Transfer",
            "Debit Card Purchase - Amazon",
            "ATM Withdrawal",
            "Utility Payment - Electric",
            "Online Transfer",
            "Check #1042",
            "Venmo Transfer",
            "Grocery Store",
            "Gas Station",
        ]),
        "amount": amount,
        "balance": round(balance, 2),
    })

# Build HTML
rows = []
for t in transactions:
    amt = t["amount"]
    debit = f"${abs(amt):,.2f}" if amt < 0 else ""
    credit = f"${amt:,.2f}" if amt >= 0 else ""
    rows.append(f"""
    <tr>
      <td>{t["date"]}</td>
      <td>{t["desc"]}</td>
      <td class="money" data-debit="{abs(amt) if amt < 0 else 0}">{debit}</td>
      <td class="money" data-credit="{amt if amt >= 0 else 0}">{credit}</td>
      <td class="money">${t["balance"]:,.2f}</td>
    </tr>
    """)

html = f"""
<style>
  body {{ font-family: 'Courier New', monospace; font-size: 9pt; }}
  .bank-header {{ margin-bottom: 16pt; }}
  .bank-name {{ font-size: 16pt; font-weight: bold; color: #003366; }}
  .account-info {{ display: flex; justify-content: space-between; margin-top: 8pt;
                   padding: 8pt; background: #f0f4f8; border: 1px solid #003366; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #003366; color: white; padding: 4pt 6pt; text-align: left;
       font-size: 8pt; text-transform: uppercase; }}
  td {{ padding: 3pt 6pt; border-bottom: 1px solid #e0e0e0; font-size: 8.5pt; }}
  .money {{ text-align: right; font-family: 'Courier New', monospace; }}
  tr:nth-child(even) {{ background: #fafafa; }}
</style>

<div class="bank-header">
  <div class="bank-name">First National Bank</div>
  <div class="account-info">
    <div>
      <strong>Account:</strong> ****4821<br>
      <strong>Type:</strong> Personal Checking
    </div>
    <div>
      <strong>Statement Period:</strong> Feb 1–28, 2026<br>
      <strong>Opening Balance:</strong> $5,432.10
    </div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Date</th>
      <th>Description</th>
      <th class="money">Debit</th>
      <th class="money">Credit</th>
      <th class="money">Balance</th>
    </tr>
  </thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>
"""

engine = PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.65in",
    document_title="Account Statement — Feb 2026",
    document_lang="en",
    pdf_profile="tagged",

    # Bank statement headers
    header_each="First National Bank — Account ****4821 — Page {page} of {pages}",
    header_font_size=7,
    header_color="#003366",
    header_y_from_top="0.3in",

    # Footers with per-page transaction summaries
    footer_each=(
        "Page {page} | "
        "Debits: ${sum:debit} ({count:debit}) | "
        "Credits: ${sum:credit} ({count:credit}) | "
        "Total Debits: ${total:debit} | "
        "Total Credits: ${total:credit}"
    ),
    footer_font_size=7,
    footer_color="#666666",
    footer_y_from_bottom="0.3in",

    # Track debits and credits per page
    paginated_context={
        "debit": "sum",
        "credit": "sum",
    },
)

pdf_bytes = engine.render(html)
with open("statement.pdf", "wb") as f:
    f.write(pdf_bytes)
```

## What the Footer Shows

On each page, you automatically get:

| Page | Debits | Credits | Running Debit Total | Running Credit Total |
|------|--------|---------|---------------------|----------------------|
| 1 | $1,247.33 (8) | $892.10 (5) | $1,247.33 | $892.10 |
| 2 | $2,103.55 (12) | $1,540.22 (7) | $3,350.88 | $2,432.32 |
| 3 | $987.41 (6) | $2,210.00 (4) | $4,338.29 | $4,642.32 |

No manual pagination math. The engine figures out what lands on each page and computes the aggregates.

## Multiple Data Aggregation Keys

You can track as many keys as you need:

```python
paginated_context={
    "debit": "sum",
    "credit": "sum",
    "fee": "sum",
    "interest": "sum:4",  # 4 decimal places for interest
}
```

Then reference them all in footers: `${sum:fee}`, `${total:interest}`, etc.

## Accessible Bank Statements

Financial institutions subject to ADA requirements can use `AccessibilityEngine` for tagged PDF/UA output:

```python
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(
    strict=False,
    document_title="Account Statement — Feb 2026",
    document_lang="en",
    footer_each="Page {page} of {pages} | Debits: ${sum:debit} | Credits: ${sum:credit}",
    paginated_context={"debit": "sum", "credit": "sum"},
)

results = engine.render_bundle(html)
# Tagged PDF with evidence of accessibility compliance
```

## Next Steps

- [Paginated Context →](../engine/paginated-context.md) — Full reference for data aggregation
- [Invoices →](invoices.md) — Similar pattern for invoice generation
- [Accessibility Engine →](../accessibility/engine.md) — Making financial documents compliant
