# UI Primitives

The core layout and content components available in `fullbleed.ui`.

## Layout Components

### Stack

Vertical layout container (flexbox column).

```python
from fullbleed.ui import Stack

Stack(
    "First item",
    "Second item",
    "Third item",
    gap="12pt",
    style="padding: 16pt;",
)
```

| Prop | Type | Description |
|------|------|-------------|
| `gap` | `str` | Space between children |
| `style` | `str` | Inline CSS |
| `className` | `str` | CSS class name |

### Row

Horizontal layout container (flexbox row).

```python
from fullbleed.ui import Row

Row(
    Card("Left"),
    Card("Center"),
    Card("Right"),
    gap="16pt",
    justify="space-between",
    align="center",
)
```

| Prop | Type | Description |
|------|------|-------------|
| `gap` | `str` | Space between children |
| `justify` | `str` | `justify-content` value |
| `align` | `str` | `align-items` value |
| `wrap` | `bool` | Enable flex-wrap |

### Card

Bordered container with padding.

```python
from fullbleed.ui import Card

Card(
    "Card content",
    style="background: #f7fafc; border-radius: 4pt;",
)
```

### Spacer

Fixed-height vertical space.

```python
from fullbleed.ui import Spacer

Stack(
    "Above",
    Spacer(height="24pt"),
    "Below",
)
```

## Content Components

### Table

HTML table from structured data.

```python
from fullbleed.ui import Table

Table(
    headers=["Region", "Revenue", "Growth"],
    rows=[
        ["North America", "$4.2M", "+15%"],
        ["Europe", "$2.8M", "+8%"],
        ["Asia Pacific", "$1.9M", "+22%"],
    ],
    caption="Q4 2025 Revenue by Region",
)
```

| Prop | Type | Description |
|------|------|-------------|
| `headers` | `list[str]` | Column headers |
| `rows` | `list[list[str]]` | Table data |
| `caption` | `str` | Table caption |

### Text

Styled text block.

```python
from fullbleed.ui import Text

Text(
    "Important notice",
    size="14pt",
    weight="bold",
    color="#1a365d",
)
```

### Image

Image with alt text.

```python
from fullbleed.ui import Image

Image(
    src="logo.png",
    alt="Company Logo",
    width="200pt",
)
```

## Composing Components

All components accept children as positional arguments and compose freely:

```python
from fullbleed.ui import Stack, Row, Card, Table, Text, Spacer

document = Stack(
    Text("Quarterly Report", size="24pt", weight="bold"),
    Spacer(height="16pt"),
    Row(
        Card(
            Text("Revenue", weight="bold"),
            Text("$4.2M", size="18pt"),
        ),
        Card(
            Text("Expenses", weight="bold"),
            Text("$3.1M", size="18pt"),
        ),
        gap="16pt",
    ),
    Spacer(height="24pt"),
    Table(
        headers=["Month", "Revenue", "Expenses"],
        rows=[
            ["October", "$1.4M", "$1.0M"],
            ["November", "$1.3M", "$1.1M"],
            ["December", "$1.5M", "$1.0M"],
        ],
        caption="Monthly Breakdown",
    ),
)
```

## Next Steps

- [Styling →](style.md) — Advanced styling options
- [Accessibility Components →](accessibility.md) — ARIA-aware semantic components
- [Component Overview →](overview.md) — Architecture and patterns
