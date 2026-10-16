# Fullbleed component design preview

This experimental preview is pinned to `f88cced0fd44cba2e4a0ff74ee1c33f3477fe469`.
Its API is not in the published Fullbleed 2.5.26 wheel on PyPI. Names and behavior
may change. This project contains Python examples and a pinned wheel installer.

You need CPython 3.10+ and internet access. The installer downloads a matching
prebuilt wheel from the GitHub preview for supported Windows, macOS and Linux
platforms. That installation does not require Rust or native build tools.
Use an isolated virtual environment:

```console
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. From this folder, run:

```console
python -m pip install --force-reinstall -r requirements-preview.txt
python first_pdf.py
python examples/component_recipes/main.py --output output
python edit_tasks.py --output output/edits
```

The requirements file selects only the exact preview assets linked in
`wheels.html`, checks their hashes and does not consult PyPI. This snapshot
retains version metadata 2.5.26, so `--force-reinstall` replaces an existing
package with that version inside this environment. The source commit and hashes
identify the preview; version metadata alone does not.

If no listed wheel matches your platform, use
`python -m pip install --force-reinstall -r requirements-source.txt` instead.
That optional path builds the same source commit and requires Rust/Cargo plus
your platform's native build tools.

Open `summary.pdf` for the standalone first example, then `output/invoice.pdf`
and `output/report.pdf`. The invoice and report use the same imported kit.
The other script renders five editing tasks and captures one expected layout
error before rendering the repair. All example data is fictional.

| Change | Where to start |
| --- | --- |
| Make a first PDF with one local component | `first_pdf.py`; no theme or part declarations required |
| Reuse and rebrand components | `shared_components()` in `edit_tasks.py`; change the theme with `with_values` |
| Add a formatted column | `extra_column()`; each `Column` owns its header and cell function |
| Change paper size | `paper_change()`; geometry belongs to `Page` |
| Connect CSS classes and instance overrides | `selector_styles()`; `class_name` labels a node, `Document(styles=...)` supplies rules |
| Diagnose a block that cannot paginate | `layout_repair()`; inspect the error and remove the clipping constraint |
| Change the imported components | `examples/component_recipes/kit.py` |
| Change invoice/report composition | `examples/component_recipes/documents.py` |
| Change the sample records | `examples/components/data.json` |

`node.required_tokens` describes the explicit theme references in constructed
content. `document.required_tokens` includes its text and selector styles.
`class_name` is a literal CSS class label; it does not load styling. Attach rules
through `Document(styles=...)`. Normal class rules can override reusable defaults;
explicit instance overrides have inline precedence. Use component-owned style
values, root overrides and advertised parts for the normal component workflow.

`document.prepare(renderer)` checks one native layout and returns a snapshot for
PDF output and layout previews. The simple `document.render_pdf(renderer)` method
uses this internally. Font files are bundled with Fullbleed and selected explicitly.

This is not a browser renderer. Layout previews are not a conformance check of
the final PDF. Oversized table rowspans, page-tall cell images and non-top-aligned
oversized cells remain unsupported. Component errors cover identified native
constraints, not every possible overflow. Static token/part-name completion and
independent usability evaluation are still open.

Try one editing task before reading its implementation. In the
[design discussion](https://github.com/fullbleed-engine/fullbleed-official/discussions/86),
share the task, what you expected, and any point where you needed generated HTML,
an internal selector or undocumented behavior. Include a small synthetic input;
please remove customer data from examples.

[Implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/f88cced0fd44cba2e4a0ff74ee1c33f3477fe469/docs/component-authoring-design.md)
· [Runnable API guide](https://github.com/fullbleed-engine/fullbleed-official/blob/f88cced0fd44cba2e4a0ff74ee1c33f3477fe469/examples/component_recipes/README.md)
