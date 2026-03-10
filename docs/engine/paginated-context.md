# Paginated Context

Paginated context lets you aggregate data across pages — running totals, subtotals, counts, and collected values — and display them in headers, footers, and watermarks.

This is a feature unique to Fullbleed. No other HTML-to-PDF engine offers built-in per-page data aggregation.

## How It Works

1. **Declare keys** in the engine configuration with an aggregation operation
2. **Annotate elements** in your HTML with `data-ctx-{key}` attributes
3. **Use placeholders** in headers/footers to display aggregated values

## Setup

```python
engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",

    # Declare what to track
    paginated_context={
        "items.amount": "sum",        # Sum amounts per page
        "items.quantity": "count",     # Count items per page
    },

    # Use in footers
    footer_each="Subtotal: ${sum:items.amount} | Items on page: {count:items.quantity}",
    footer_last="Grand Total: ${total:items.amount} | Total items: {total_count:items.quantity}",
    footer_x="0.5in",
    footer_y_from_bottom="0.3in",
)
```

## Aggregation Operations

| Operation | Description | Placeholder (per-page) | Placeholder (total) |
|-----------|-------------|----------------------|---------------------|
| `"sum"` | Sum numeric values | `{sum:key}` | `{total:key}` |
| `"sum:<scale>"` | Sum with decimal scale | `{sum:key}` | `{total:key}` |
| `"count"` | Count occurrences | `{count:key}` | `{total_count:key}` |
| `"every"` | Collect all values | `{every:key}` | `{total_every:key}` |

### Decimal Scale

For financial documents, control decimal precision:

```python
paginated_context={
    "tx.amount": "sum",      # Default: 2 decimal places (cents)
    "tax.rate": "sum:4",     # 4 decimal places
}
```

## HTML Annotation

Mark elements in your HTML with data attributes that match your context keys:

```html
<table>
  <tr>
    <td>Widget A</td>
    <td data-ctx-items.amount="25.00">$25.00</td>
  </tr>
  <tr>
    <td>Widget B</td>
    <td data-ctx-items.amount="42.00">$42.00</td>
  </tr>
  <tr>
    <td>Consulting</td>
    <td data-ctx-items.amount="150.00">$150.00</td>
  </tr>
</table>
```

When this content spans multiple pages, Fullbleed automatically tracks which values land on which page and computes per-page subtotals.

## Real-World Example: Bank Statement

```python
engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.85in",

    paginated_context={
        "tx.amount": "sum",
        "tx.deposit": "sum",
        "tx.withdrawal": "sum",
    },

    header_each="Statement Continued - Page {page} of {pages}",
    header_x="0.5in",
    header_y_from_top="0.16in",

    footer_each=(
        "Page {page} of {pages}  |  "
        "Deposits: ${sum:tx.deposit}  |  "
        "Withdrawals: ${sum:tx.withdrawal}  |  "
        "Net: ${sum:tx.amount}"
    ),
    footer_last=(
        "Page {page} of {pages}  |  "
        "Total Deposits: ${total:tx.deposit}  |  "
        "Total Withdrawals: ${total:tx.withdrawal}  |  "
        "Net: ${total:tx.amount}"
    ),
    footer_x="0.5in",
    footer_y_from_bottom="0.16in",
)
```

## Accessing Page Data Programmatically

Use `render_pdf_with_page_data` to get the aggregated data as a Python dict:

```python
pdf_bytes, page_data = engine.render_pdf_with_page_data(html, css)

# page_data structure:
# {
#     "pages": {
#         1: {"tx.amount": 1250.00, "tx.deposit": 2000.00, "tx.withdrawal": 750.00},
#         2: {"tx.amount": -340.00, ...},
#     },
#     "totals": {"tx.amount": 910.00, "tx.deposit": 3500.00, "tx.withdrawal": 2590.00}
# }
```

This is useful for generating summary data, validation, or feeding into downstream systems.
