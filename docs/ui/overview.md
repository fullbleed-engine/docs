# UI Component System

Fullbleed includes a React-like component system for building document structures in Python. Components are composable, reusable building blocks that emit semantic HTML.

## When to Use Components vs. Raw HTML

| Approach | Best For |
|----------|----------|
| **Raw HTML** | Simple documents, one-off renders, HTML you already have |
| **Components** | Reusable templates, complex layouts, teams building many document types |

You can mix both approaches — components emit HTML, so they compose naturally with raw HTML strings.

## Basic Usage

```python
from fullbleed.ui import Stack, Row, Card, Table

# Components are nested via positional arguments
# Props are keyword arguments
doc = Stack(
    Card(
        "Welcome to the Report",
        style="padding: 24pt; background: #f0f4f8;"
    ),
    Row(
        Card("Revenue: $4.2M", style="flex: 1;"),
        Card("Expenses: $3.1M", style="flex: 1;"),
        Card("Profit: $1.1M", style="flex: 1;"),
        gap="16pt",
    ),
)
```

## Core Components

### Layout

| Component | Description |
|-----------|-------------|
| `Stack` | Vertical layout (flexbox column) |
| `Row` | Horizontal layout (flexbox row) |
| `Card` | Bordered box with padding |
| `Spacer` | Fixed-height spacing element |

### Content

| Component | Description |
|-----------|-------------|
| `Table` | HTML table with headers and rows |
| `Text` | Styled text block |
| `Image` | Image with alt text |

### The `@Document` Decorator

The `@Document` decorator compiles a component tree into a `DocumentArtifact`:

```python
from fullbleed.ui import Document, Stack, Card

@Document(title="My Report", lang="en")
def my_report(data):
    return Stack(
        Card(f"Report for {data['name']}"),
        Card(f"Period: {data['period']}"),
    )

# Build the document
artifact = my_report(data={"name": "Acme Corp", "period": "Q4 2025"})

# Get HTML
html = artifact.to_html()

# Render to PDF
from fullbleed import PdfEngine
engine = PdfEngine(margin="0.85in")
pdf = engine.render(html)
```

## Component Patterns

### Children are Positional Arguments

```python
# ✅ Correct — children are positional
Stack(
    Card("First"),
    Card("Second"),
    Card("Third"),
)

# ❌ Wrong — not a builder/callable pattern
Stack().add(Card("First")).add(Card("Second"))
```

### Props are Keyword Arguments

```python
Card(
    "Content here",
    style="background: #f0f4f8;",
    className="highlight",
)
```

### Nested Composition

```python
Stack(
    Row(
        Stack(
            Card("Left column, top"),
            Card("Left column, bottom"),
        ),
        Stack(
            Card("Right column, top"),
            Card("Right column, bottom"),
        ),
    ),
)
```

## Next Steps

- [Primitives →](primitives.md) — All available components
- [Styling →](style.md) — Component styling options
- [Accessibility Components →](accessibility.md) — ARIA-aware components
