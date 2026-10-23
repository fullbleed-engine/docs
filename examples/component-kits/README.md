# Two component kits, one document

A runnable example for Fullbleed's opt-in Python component alpha. All data is
synthetic. Install Python 3.10 or later, then:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python report.py
```

Open `output/default.pdf` and `output/default.html`. The other three variants
change the billing brand, the impact brand, or just one displayed value. Each
variant also has unstyled HTML, separate native print source, a native PNG and
pagination diagnostics. No browser or third-party Python package is needed to
generate these files.

## The two kit contracts

`billing.py` exports `BillingPalette` and `billing_kit(palette)`. The returned
`Balance(label, amount, note)` component has concrete defaults, requires no theme,
and exposes the parts `label`, `amount` and `note`. Creating a new kit with a
different immutable palette does not change an earlier kit.

`impact.py` exports `Impact(label, value, note)` and `IMPACT_DEFAULTS`. Its parts
are `label`, `value` and `note`. Its required document tokens are:

| Token | Meaning | Default |
| --- | --- | --- |
| `impact.accent` | Main value color | `#19715e` |
| `impact.surface` | Card background | `#eaf5ef` |
| `impact.ink` | Label and note color | `#214d40` |

Supply all defaults with `Theme(IMPACT_DEFAULTS)`. Use `theme.with_values({...})`
to derive a theme. Call `node.required_tokens` or `document.required_tokens` to
inspect dependencies without reading the kit internals. A missing binding in a
styled export or PDF raises `AuthoringError` with code `theme.missing`.

Tokens are flat, document-wide names. A prefix is a convention, not automatic
scoping. Two components using `token("accent")` share the same binding. Mapping
merges and `Theme.with_values` use the later value for a repeated name; they do
not report a collision. Use distinct prefixes for distinct meanings. If two
instances of the same kit need different palettes, create separate concrete
kits, use the kit's advertised parts, or give a token-based kit an explicit
prefix parameter. There is no implicit per-instance theme in this example.

## Customization and exports

Kit defaults use `styled(...)`. Meaningful choices belong in ordinary function
arguments. Local changes use `node.with_style(...)` for the root and
`node.with_parts(value=style(...))` for a documented internal part. A root color
does not replace a child's explicitly defined color. None of these edits needs
generated selectors.

`document.to_html(include_styles=True)` embeds the styles. Passing `False`
removes generated CSS and inline styles, retaining content and literal classes
for an application's own stylesheet. The report owns its responsive screen
layout, with explicit print and screen rules. On the separate-CSS rendering
path, Fullbleed can apply screen rules when no print rule is present; keep the
example's print block when adding screen-only styling.
The report's grid columns are reusable `styled(Grid, ...)` defaults, so the
mobile stylesheet can override them. An explicit `Grid(columns=2)` is an
instance choice and takes precedence over an ordinary class rule.
The PDF uses bundled Inter; browser HTML uses a local Inter or its
sans-serif fallback. Browser layout is not a PDF pagination preview.

Both kit modules were authored for this example by the Fullbleed project. They
demonstrate separate dependencies and customization contracts; they do not
constitute independent author feedback or a component API stability promise.
