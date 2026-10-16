# Fullbleed component design preview

This is a source preview pinned to `d686153b392a5cb5f5316624bf6b9401e7bcf951`.
The experimental API is not in the published Fullbleed 2.5.25 wheel. Names and
behavior may change. This project contains examples, not the native engine.

You need Python 3.10+, Rust/Cargo, your platform's native build tools, and internet
access for the source installation. Use a new virtual environment:

```console
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. From this folder, run:

```console
python -m pip install -r requirements-preview.txt
python examples/component_recipes/main.py --output output
python edit_tasks.py --output output/edits
```

The first installation builds the engine and can take several minutes. Git is
not required: the requirement downloads the exact source archive. The candidate's
package metadata says 2.5.25; the pinned commit identifies this preview.

Open `output/invoice.pdf` and `output/report.pdf`. Both use the same imported kit.
The other script renders four editing tasks and captures one expected layout
error before rendering the repair. All example data is fictional.

| Change | Where to start |
| --- | --- |
| Reuse and rebrand components | `shared_components()` in `edit_tasks.py`; change the theme with `with_values` |
| Add a formatted column | `extra_column()`; each `Column` owns its header and cell function |
| Change paper size | `paper_change()`; geometry belongs to `Page` |
| Diagnose a block that cannot paginate | `layout_repair()`; inspect the error and remove the clipping constraint |
| Change the imported components | `examples/component_recipes/kit.py` |
| Change invoice/report composition | `examples/component_recipes/documents.py` |
| Change the sample records | `examples/components/data.json` |

`node.required_tokens` describes the explicit theme references in constructed
content. `document.required_tokens` includes its text styles. `class_name` is a
literal CSS class label; it does not load styling. Use style values, root overrides
and advertised parts for the normal component workflow.

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

[Implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/d686153b392a5cb5f5316624bf6b9401e7bcf951/docs/component-authoring-design.md)
· [Runnable API guide](https://github.com/fullbleed-engine/fullbleed-official/blob/d686153b392a5cb5f5316624bf6b9401e7bcf951/examples/component_recipes/README.md)
