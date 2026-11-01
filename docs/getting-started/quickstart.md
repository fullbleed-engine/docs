---
title: Generate PDFs in Python with HTML/CSS or components
description: Create your first PDF from HTML/CSS or Python components. Copy either complete example, use bundled fonts, and render the same invoice.
search:
  boost: 2
---
# Create your first PDF in Python

Prefer to try it before setting up Python? [Open the browser playground](../playground.md)
to edit HTML/CSS and download a PDF or runnable project. Use the
[invoice notebook](notebook.md) to work with Python data in Colab.

Choose **HTML/CSS** to bring a template, or **Python components** to compose
a document with functions. Both examples below use the stable API, embed
the bundled Inter font, and write the same one-page invoice.

Install Fullbleed in your Python environment. If you need an isolated environment,
follow the [virtual environment setup](installation.md#use-a-virtual-environment)
first.

```bash
python -m pip install fullbleed
```

Choose one tab and save its complete example as `hello.py`. These examples are
checked with Fullbleed **2.5.51**.

=== "HTML/CSS"

    ```python
    from importlib.resources import files
    from pathlib import Path
    import fullbleed

    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    engine = fullbleed.PdfEngine(font_files=[str(font)])
    html = '<h1 class="invoice-title">Invoice INV-1042</h1><p>Consulting: USD 1,200.00</p>'
    css = """
    @page { size: A4; margin: 20mm; }
    body { font-family: Inter; color: #203a36; }
    .invoice-title { color: #175c52; }
    """
    pdf = engine.render_pdf(html, css)
    Path("invoice.pdf").write_bytes(pdf)
    ```

=== "Python components"

    ```python
    from importlib.resources import files
    from pathlib import Path
    import fullbleed
    from fullbleed.ui import Document, Heading, Paragraph

    @Document(
        title="Invoice INV-1042",
        styles={
            "@page": {"size": "A4", "margin": "20mm"},
            "body": {"font_family": "Inter", "color": "#203a36"},
            ".invoice-title": {"color": "#175c52"},
        },
    )
    def Invoice(number, description, amount):
        return (
            Heading("Invoice ", number, level=1, class_name="invoice-title"),
            Paragraph(description, ": ", amount),
        )

    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    engine = fullbleed.PdfEngine(font_files=[str(font)])
    invoice = Invoice("INV-1042", "Consulting", "USD 1,200.00")
    Path("invoice.pdf").write_bytes(invoice.render_pdf(engine))
    ```

In the component example, `Invoice(...)` receives ordinary Python arguments. `@Document(styles=...)`
attaches the stylesheet to its result. The heading's
`class_name="invoice-title"` matches the `.invoice-title` rule; the HTML/CSS
example uses the same class and values.

Run it and open the resulting file:

```bash
python hello.py
python -m fullbleed inspect pdf invoice.pdf --json
```

For a PNG preview of the finalized PDF, continue to the [font and preview walkthrough](first-pdf.md).

Continue with [reusable components, lists, and styles](../guides/python-components.md)
or the [designed HTML/CSS invoice](../guides/invoices.md). The separate
[component alpha](../guides/component-preview-11.md) adds portable component
styles, themes, named parts, and styled/unstyled HTML export. It has its own
explicit installation instructions; the examples above use the stable
`fullbleed.ui` API. The [release-status guide](../guides/component-status.md)
explains the distinction and the remaining stabilization work.

## Start with a complete project

For a component-based report with vendored assets and verification output, run these commands in a new directory:

```bash
mkdir my-report
cd my-report
python -m fullbleed init .
python report.py
```

Open `output/report.pdf`. The project includes Python components, CSS, bundled Inter, Bootstrap assets, a PNG preview, and structured diagnostics. Read its `SCAFFOLDING.md` before reorganizing the project.

For an invoice with editable sample data:

```bash
python -m fullbleed new local invoice my-invoice
python my-invoice/report.py
```

Open `my-invoice/output/invoice.pdf`. Edit `my-invoice/data.json` to change the
company, customer, dates, and line items, then rerun the script. Edit the HTML
and CSS in `my-invoice/templates` to change the design. The starter calculates
amounts, embeds Inter, and writes PNG previews. Its README explains decimal
rounding and the standard-library `${placeholder}` template syntax.

For an account statement or an accessibility-first document:

```bash
python -m fullbleed new local statement my-statement
python my-statement/report.py
python -m fullbleed new local accessible my-accessible-document
python my-accessible-document/report.py
```

The statement also has editable `data.json`. The accessible starter uses Python
components and writes its PDF, previews, and internal validation reports into
`my-accessible-document/output`. Those checks support authoring and debugging;
they do not establish independent PDF/UA certification.

## Bring your own HTML and CSS

```bash
python -m fullbleed render --html invoice.html --css invoice.css --out invoice.pdf
```

Use explicit local assets. See [supported CSS and known gaps](../css-coverage.md) when adapting an existing template.

If your HTML already contains `<style>` elements, see
[render a complete HTML document](../guides/complete-html.md). Fullbleed 2.5.26
adds embedded stylesheet support, including print-media rules and page settings.

Printing labels or signs? [Set custom paper sizes in CSS](../guides/custom-paper-sizes.md)
with a complete shelf-card project and checks of the actual PDF dimensions.

[Examples and generated PDFs](../examples.md) · [Web framework examples](../guides/web-frameworks.md) · [Python API](../engine/pdf-engine.md) · [CLI reference](../cli/commands.md)

Ask a question or share a document in [GitHub Discussions](https://github.com/fullbleed-engine/fullbleed-official/discussions/6).
