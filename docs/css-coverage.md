# CSS Coverage

Fullbleed implements a CSS rendering engine in Rust. It supports the most commonly used CSS properties for document layout, with a focus on print-oriented features.

## Supported Properties

### Layout

| Property | Support | Notes |
|----------|---------|-------|
| `display` | ✅ `block`, `inline`, `inline-block`, `flex`, `none` | No `grid` yet |
| `position` | ✅ `static`, `relative`, `absolute` | No `fixed`, `sticky` |
| `width`, `height` | ✅ | Including `min-*`, `max-*` |
| `margin` | ✅ | All sides, auto centering |
| `padding` | ✅ | All sides |
| `float` | ✅ `left`, `right` | Basic float layout |
| `clear` | ✅ | `left`, `right`, `both` |
| `overflow` | ✅ `visible`, `hidden` | No scroll |
| `box-sizing` | ✅ | `content-box`, `border-box` |

### Flexbox

| Property | Support | Notes |
|----------|---------|-------|
| `display: flex` | ✅ | |
| `flex-direction` | ✅ | `row`, `column`, `row-reverse`, `column-reverse` |
| `justify-content` | ✅ | All standard values |
| `align-items` | ✅ | All standard values |
| `flex-wrap` | ✅ | `nowrap`, `wrap` |
| `flex-grow`, `flex-shrink` | ✅ | |
| `flex-basis` | ✅ | |
| `gap` | ✅ | |
| `order` | ✅ | |

### Typography

| Property | Support | Notes |
|----------|---------|-------|
| `font-family` | ✅ | With font embedding |
| `font-size` | ✅ | `px`, `pt`, `em`, `rem`, `%` |
| `font-weight` | ✅ | Numeric and named |
| `font-style` | ✅ | `normal`, `italic`, `oblique` |
| `line-height` | ✅ | |
| `text-align` | ✅ | `left`, `right`, `center`, `justify` |
| `text-decoration` | ✅ | `underline`, `overline`, `line-through` |
| `text-transform` | ✅ | `uppercase`, `lowercase`, `capitalize` |
| `letter-spacing` | ✅ | |
| `word-spacing` | ✅ | |
| `white-space` | ✅ | `normal`, `nowrap`, `pre`, `pre-wrap` |
| `text-indent` | ✅ | |
| `vertical-align` | ✅ | |

### Colors & Backgrounds

| Property | Support | Notes |
|----------|---------|-------|
| `color` | ✅ | Hex, RGB, named colors |
| `background-color` | ✅ | |
| `background-image` | ✅ | `url()`, gradients (limited) |
| `opacity` | ✅ | |

### Borders

| Property | Support | Notes |
|----------|---------|-------|
| `border` | ✅ | All shorthand and longhand |
| `border-width` | ✅ | Per side |
| `border-style` | ✅ | `solid`, `dashed`, `dotted`, `none` |
| `border-color` | ✅ | |
| `border-radius` | ✅ | |
| `border-collapse` | ✅ | For tables |
| `border-spacing` | ✅ | |

### Tables

| Property | Support | Notes |
|----------|---------|-------|
| `table-layout` | ✅ | `auto`, `fixed` |
| `border-collapse` | ✅ | |
| `border-spacing` | ✅ | |
| `caption-side` | ✅ | |

### Lists

| Property | Support | Notes |
|----------|---------|-------|
| `list-style-type` | ✅ | `disc`, `circle`, `square`, `decimal`, `none`, etc. |
| `list-style-position` | ✅ | `inside`, `outside` |

### Print

| Property | Support | Notes |
|----------|---------|-------|
| `page-break-before` | ✅ | `always`, `auto` |
| `page-break-after` | ✅ | `always`, `auto` |
| `page-break-inside` | ⚠️ | `avoid` may not always be respected |
| `break-before` | ✅ | `page`, `auto` |
| `break-after` | ✅ | `page`, `auto` |
| `break-inside` | ⚠️ | `avoid` may not always be respected |

### Units

| Unit | Support |
|------|---------|
| `px` | ✅ (96 DPI) |
| `pt` | ✅ (1/72 inch) |
| `in` | ✅ |
| `cm` | ✅ |
| `mm` | ✅ |
| `em` | ✅ |
| `rem` | ✅ |
| `%` | ✅ |
| `vw`, `vh` | ❌ (no viewport concept) |

## Not Supported

These CSS features are **not available**:

- `display: grid` — Use flexbox or table layout instead
- `position: fixed` / `position: sticky` — Use headers/footers engine params instead
- CSS `@page` margin boxes — Use `header_each` / `footer_each` engine params
- CSS `@media` queries — Single output format (print)
- CSS animations / transitions — Static output
- `calc()` — Not yet implemented
- CSS variables (`var()`) — Not yet implemented
- `transform` — Not yet implemented

## Tips for Best Results

1. **Use `page-break-before: always`** for explicit page breaks (more reliable than `break-inside: avoid`)
2. **Use flexbox** for layout — it's well-supported and handles most document layouts
3. **Use tables** for tabular data — Fullbleed's table layout is solid
4. **Avoid CSS Grid** — rewrite with flexbox
5. **Set explicit widths** on table columns for predictable layout
6. **Use pt/in** for print dimensions, `px` for screen-like content

## Next Steps

- [PdfEngine API →](engine/pdf-engine.md) — Engine parameters that complement CSS
- [Headers & Footers →](engine/headers-footers.md) — Replacing CSS @page features
- [Comparison Guide →](guides/comparison.md) — CSS support vs. other tools
