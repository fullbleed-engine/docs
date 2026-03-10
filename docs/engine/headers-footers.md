# Headers & Footers

Fullbleed has **built-in header and footer support** — no CSS `@page` margin-box hacks or JavaScript injection required. Headers and footers support dynamic placeholders for page numbers, running totals, and custom data.

## Text Headers & Footers

The simplest approach — plain text with placeholders:

```python
engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",

    # Footer on every page
    footer_each="Page {page} of {pages}",
    footer_x="0.5in",
    footer_y_from_bottom="0.3in",
    footer_font_name="Helvetica",
    footer_font_size=9.0,
    footer_color="#666666",
)
```

### Per-Page Control

You can set different headers/footers for the first page, middle pages, and last page:

```python
engine = fullbleed.PdfEngine(
    # ...page geometry...

    # Header: nothing on first page, "Continued" on subsequent pages
    header_first=None,
    header_each="Statement Continued — Page {page} of {pages}",
    header_last="Statement Continued — Final Page",

    header_x="0.5in",
    header_y_from_top="0.3in",
    header_font_name="Inter",
    header_font_size=9.0,
    header_color="#5a6d84",

    # Footer: always show page numbers
    footer_each="Page {page} of {pages}",
    footer_x="0.5in",
    footer_y_from_bottom="0.3in",
)
```

### Text Header/Footer Parameters

| Parameter | Description |
|-----------|-------------|
| `header_first` | Header text for page 1 only |
| `header_each` | Header text for pages 2 through N-1 |
| `header_last` | Header text for the last page |
| `header_x` | Horizontal position (length string) |
| `header_y_from_top` | Distance from top of page |
| `header_font_name` | Font family name |
| `header_font_size` | Font size (float) |
| `header_color` | Text color (hex string) |

Footer parameters follow the same pattern: `footer_first`, `footer_each`, `footer_last`, `footer_x`, `footer_y_from_bottom`, etc.

## HTML Headers & Footers

For complex headers with styling, images, or multi-column layouts, use HTML headers:

```python
engine = fullbleed.PdfEngine(
    # ...page geometry...

    header_html_each="""
    <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px;">
        <div style="font-weight: bold; color: #2d3748;">Acme Corp</div>
        <div style="color: #718096;">Statement — Page {page} of {pages}</div>
    </div>
    """,
    header_html_x="0.75in",
    header_html_y_from_top="0.3in",
    header_html_width="7in",
    header_html_height="0.5in",
)
```

### HTML Header/Footer Parameters

| Parameter | Description |
|-----------|-------------|
| `header_html_first` | HTML header for page 1 |
| `header_html_each` | HTML header for pages 2+ |
| `header_html_last` | HTML header for last page |
| `header_html_x` | Left offset |
| `header_html_y_from_top` | Top offset |
| `header_html_width` | Render width |
| `header_html_height` | Render height |

## Placeholders

All headers and footers (text and HTML) support these placeholders:

| Placeholder | Description |
|-------------|-------------|
| `{page}` | Current page number |
| `{pages}` | Total page count |
| `{sum:key}` | Per-page sum for a paginated context key |
| `{total:key}` | Document-wide total for a paginated context key |
| `{count:key}` | Per-page count of occurrences |
| `{total_count:key}` | Document-wide count |
| `{every:key}` | All values on current page |
| `{total_every:key}` | All values in document |

See [Paginated Context →](paginated-context.md) for details on setting up data aggregation.

## Example: Bank Statement

```python
engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.85in",

    # No header on first page (has its own design), "Continued" on the rest
    header_each="Statement Continued - Page {page} of {pages}",
    header_x="0.5in",
    header_y_from_top="0.16in",
    header_font_name="Inter",
    header_font_size=9.0,
    header_color="#5a6d84",

    # Running totals per page
    paginated_context={"tx.amount": "sum"},

    footer_each="Page {page} of {pages}  |  Running Total: ${sum:tx.amount}",
    footer_last="Page {page} of {pages}  |  Grand Total: ${total:tx.amount}",
    footer_x="0.5in",
    footer_y_from_bottom="0.16in",
    footer_font_name="Inter",
    footer_font_size=8.0,
    footer_color="#5a6d84",
)
```

## See Also

- [Paginated Context →](paginated-context.md) — Running totals and per-page data
- [Page Margins →](page-margins.md) — Different margins per page
