# Release notes that travel

**NORTHSTAR ENGINEERING · FIELD GUIDE 07 · FICTIONAL SAMPLE**

An engineering brief should survive the journey from a repository to a review
meeting. Keep the source in Markdown, give it a considered print stylesheet,
and publish a PDF that carries the same content into the room.

![Markdown flows through HTML and CSS into a PDF.](images/publishing.svg)

## Keep the source readable

Write the update where the work happens. Headings establish a reading order;
lists make decisions easy to scan. A table gives owners and reviewers a common
reference. The stylesheet handles type, spacing, rules, and page geometry.

> Make the document easy to edit, then make the result worth reading.

This sample uses **bold emphasis**, *italic emphasis*, and `inline code`.
It also keeps ~~the old release name~~ the revised name visible in a change log.

| Deliverable | Owner | Review evidence |
| --- | --- | --- |
| Release brief | Documentation | Headings and links checked |
| Migration notes | Engineering | Code examples reviewed |
| Distribution copy | Release lead | Final PDF opened |

## Turn the brief into a PDF

The project has two jobs: the Markdown parser creates HTML, and Fullbleed lays
out the pages. The parser is a dependency of this example. The PDF engine stays
independent of the content format used by your application.

```python
from markdown_it import MarkdownIt

parser = MarkdownIt("js-default", {"linkify": False})
html = parser.render("# Release 07\n\nReady for review.")
# Pass this HTML and your print stylesheet to Fullbleed.
```

The complete script also registers the fonts and local images. It writes the
PDF, the HTML/CSS inputs, a glyph report, and PNG previews of the finalized PDF.
The example's monospace font is included under its own open font license.

### Review before sharing

1. Open the PDF and check every page, including the last one.
2. Confirm that code indentation, tables, and local images are readable.
3. Check the recorded glyph report and the input/output hashes.
4. Keep the Markdown, stylesheet, and referenced assets with the published copy.

A successful command is one part of review. New content can create long lines,
wide tables, and unexpected page breaks. Treat a changed template as a reason
to look at the output again.

## Adapt the design

Edit `print.css` to change the paper size, margins, heading scale, table colors,
or code treatment. Keep local image references next to the document:

```markdown
![Publishing workflow](images/publishing.svg)
```

For a team workflow, commit the source with the application and run the same
command in a release job. Supply the content from your existing toolchain;
the rendering step does not execute fenced code or fetch remote images.

The [Fullbleed Markdown guide](https://docs.fullbleed.dev/guides/markdown-pdf/)
explains the starter, supported syntax, and customization points.

---

*Northstar Engineering is a fictional organization. This brief demonstrates
ordinary PDF generation and does not claim PDF/A or PDF/UA conformance.*
