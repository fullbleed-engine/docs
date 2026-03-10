# Component Styling

Fullbleed UI components support inline styles, CSS classes, and external stylesheets.

## Inline Styles

Every component accepts a `style` prop for inline CSS:

```python
Card(
    "Highlighted content",
    style="background: #fefcbf; border: 2px solid #d69e2e; padding: 16pt;",
)
```

## CSS Classes

Use `className` to reference styles from an external stylesheet:

```python
Card(
    "Styled card",
    className="revenue-card",
)
```

```css
/* styles/report.css */
.revenue-card {
    background: linear-gradient(135deg, #e6f7ff 0%, #bae7ff 100%);
    border-left: 4px solid #1890ff;
    padding: 16pt;
    border-radius: 4pt;
}
```

## External Stylesheets

Include CSS in your HTML or reference vendored stylesheets:

```python
from fullbleed import PdfEngine

css = """
<style>
  .header { font-size: 24pt; color: #1a365d; font-weight: bold; }
  .metric { font-size: 18pt; text-align: center; padding: 12pt; }
  .positive { color: #38a169; }
  .negative { color: #e53e3e; }
</style>
"""

html = css + document.to_html()  # Prepend CSS to component HTML
engine = PdfEngine(margin="0.85in")
pdf = engine.render(html)
```

## Responsive-Like Patterns

While Fullbleed doesn't support CSS media queries (there's no viewport), you can control layout at the Python level:

```python
def build_layout(columns=3):
    """Switch between 2-column and 3-column layouts programmatically."""
    cards = [Card(f"Item {i}") for i in range(6)]

    if columns == 3:
        return Stack(
            Row(*cards[:3], gap="12pt"),
            Row(*cards[3:], gap="12pt"),
        )
    else:
        return Stack(
            Row(*cards[:2], gap="12pt"),
            Row(*cards[2:4], gap="12pt"),
            Row(*cards[4:], gap="12pt"),
        )
```

## Typography Utilities

```python
Text("Title", size="24pt", weight="bold", color="#1a365d")
Text("Subtitle", size="14pt", weight="600", color="#4a5568")
Text("Body text", size="10pt", color="#2d3748")
Text("Caption", size="8pt", color="#718096", style="font-style: italic;")
```

## Best Practices

1. **Use inline styles** for one-off overrides
2. **Use CSS classes** for reusable styles across components
3. **Use external stylesheets** for design system consistency
4. **Keep styles simple** — Fullbleed supports print-oriented CSS; avoid web-specific features
5. **Use `pt` or `in`** for sizing — these are print units and render predictably

## Next Steps

- [Primitives →](primitives.md) — All available components
- [Accessibility Components →](accessibility.md) — ARIA-aware components
- [CSS Coverage →](../css-coverage.md) — Supported CSS properties
