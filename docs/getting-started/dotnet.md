---
title: Generate PDFs from C# and .NET with HTML and CSS
description: Install FullBleed.DotNet from NuGet, render a PDF from C#, and run a designed invoice with explicit fonts and PNG previews. No browser or Python runtime is needed for native rendering.
---
# Generate PDFs from C# and .NET

[`FullBleed.DotNet`](https://www.nuget.org/packages/FullBleed.DotNet/0.1.6)
brings Fullbleed's Rust rendering engine into a .NET process. Use static HTML
and CSS to create invoices, reports, and variable-data documents. Native
rendering needs neither Python nor a browser.

## Install and render your first PDF

With the .NET 10 SDK installed:

```bash
dotnet new console -n InvoiceDemo --framework net10.0
cd InvoiceDemo
dotnet add package FullBleed.DotNet --version 0.1.6
```

Replace `Program.cs` with:

```csharp
using FullBleed.DotNet;

using var engine = new FullBleedEngine(new FullBleedEngineOptions
{
    DocumentLanguage = "en-US",
    DocumentTitle = "Invoice INV-1042",
});

var html = "<h1>Invoice INV-1042</h1><p>Consulting: USD 1,200.00</p>";
var css = "@page { size: A4; margin: 20mm; } h1 { color: #175c52; }";
File.WriteAllBytes("invoice.pdf", engine.RenderPdf(html, css));

var inspection = FullBleedEngine.InspectPdf("invoice.pdf");
Console.WriteLine($"Created invoice.pdf: {inspection.PageCount} page(s).");
```

Run `dotnet run` and open `invoice.pdf` in the project directory. You can also
return the bytes from an HTTP handler or write them to your own storage.
The first example uses standard PDF fonts. Their PNG previews now use bundled
outline substitutes, so they work without system fonts. Register explicit font
files for your chosen type design and character coverage; the designed example
below embeds its fonts.

The package's managed library targets `net8.0`; your application can target
`net8.0`, `net9.0`, or `net10.0`. It contains native libraries for Windows x64,
Linux x64, Intel macOS, and Apple Silicon macOS. It pins Fullbleed 2.5.11.
The managed assembly has no third-party NuGet runtime dependencies.

Use .NET 10 LTS for a new application. Microsoft lists November 10, 2026 as
the end of support for .NET 8 and 9 in its
[support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core).
Existing .NET 8 and 9 projects can use the same package and C# API.
The [package verification workflow](https://github.com/fullbleed-engine/fullbleed-dotnet/actions/workflows/ci.yml)
checks the actual runtime and compares fixture PDFs and previews across all
three .NET versions and the four native platforms.

Version 0.1.6 also checks 52 font fixtures across those twelve consumers:
Helvetica, Times and Courier in their regular/bold/italic variants, plus an
embedded-font control, through ordinary and compiled rendering. A separate
Linux check hides system fonts and rejects the blank previews from public
0.1.5. The corrected previews retain the same PDF bytes and embedded-font
controls. These checks cover the retained fixtures, not every font or document.
[Inspect the 0.1.6 evidence](https://github.com/fullbleed-engine/fullbleed-dotnet/releases/tag/v0.1.6).

## Run a designed invoice

The Northstar sample combines explicit fonts, CSS grid, tables, print
dimensions, color, and typographic hierarchy. Its text and business details
are fictional.

[![Northstar invoice rendered from C#, with cream paper, dark green typography, and a large total panel.](../assets/showcase/invoice-dotnet.png)](../assets/showcase/invoice-dotnet.pdf)

[Open the PDF generated from C#](../assets/showcase/invoice-dotnet.pdf).

Version 0.1.5 fixes wrapping after styled inline text and the widths of tracked
labels in flex and inline-block layouts. The release checks 54 layout cases
through ordinary and compiled rendering, including a comparison that rejects
44 defective cases in the previous package. The invoice retains its intended
regular brand face; its corrected spacing is checked against a reviewed PDF
and preview baseline. Review saved outputs when upgrading affected templates.
[Inspect the release evidence](https://github.com/fullbleed-engine/fullbleed-dotnet/releases/tag/v0.1.5).

The earlier [0.1.3 comparison](https://github.com/fullbleed-engine/fullbleed-dotnet/releases/tag/v0.1.3)
measured font compaction from 81,227 to 34,542 bytes for that older output. Those
historical numbers describe a different rendered appearance. Read
[how font compaction works](../guides/pdf-size.md) or the
[font-family upgrade guide](../engine/font-registration.md).

Clone the documentation repository and run the example with .NET 10:

```bash
git clone https://github.com/fullbleed-engine/docs.git fullbleed-docs
cd fullbleed-docs
dotnet run --project examples/dotnet -c Release -- output/northstar
```

Open `output/northstar/invoice.pdf` and `invoice_page1.png`. The sample
includes the HTML, CSS, font files, and their license notices. Rendering
uses those local assets and the prebuilt NuGet package. You do not need a
Rust compiler to run it.

[Read the complete C# sample](https://github.com/fullbleed-engine/docs/tree/main/examples/dotnet)
or [browse the document assets](https://github.com/fullbleed-engine/docs/tree/main/docs/assets/showcase).

## Register fonts and inspect the result

The sample registers every font used by its CSS before rendering:

```csharp
using var engine = new FullBleedEngine(new FullBleedEngineOptions
{
    Assets = Directory.GetFiles("fonts", "*.ttf")
        .Order(StringComparer.Ordinal)
        .Select(path => FullBleedAsset.FromPath(path, FullBleedAssetKind.Font))
        .ToList(),
});

var result = engine.RenderPdfWithDiagnostics(html, css);
if (result.Diagnostics.MissingGlyphs.Count != 0)
{
    throw new InvalidOperationException("The supplied fonts do not cover every character.");
}
File.WriteAllBytes("invoice.pdf", result.Pdf);

engine.RenderImagePagesToDirectory(html, css, "preview", dpi: 96, stem: "invoice");
```

Keep the font notices when redistributing the assets. The PDF and PNG calls
above are separate render operations; use
`RenderFinalizedPdfImagePagesToDirectory` to preview an existing Fullbleed PDF.
Inspect the rendered pages after changing content or fonts.

## Use the native API or the CLI adapter

`FullBleedEngine` covers rendering, batches, diagnostics, previews, PDF
inspection, template composition, and compiled bindings. For repeated
documents, `BindingMap<T>` projects records through ordinary LINQ selectors.
Use fixed bindings for values with reserved geometry, and reflow bindings
when changing text must wrap or repaginate.

`FullBleedCliClient` is a separate adapter for an independently installed
Fullbleed Python CLI. It discovers that runtime's capabilities and schemas
and exposes verification, profiles, scaffolding, and other CLI workflows.
Installing the NuGet package alone does not install the Python CLI.

Selecting an output profile is not proof of conformance. Check the actual
document and retain the relevant verification evidence before making an
accessibility, archival, or print-standard claim.

For a web application, download the [ASP.NET Core PDF starter](../guides/aspnet-pdf.md).
For tagged output, use the [C# library-notice starter](../guides/csharp-tagged-pdf.md)
with PDF/UA profiles and independent validation.
It includes a download page, styled invoice, private responses, and checks against
the published application artifact.

[.NET API reference](https://github.com/fullbleed-engine/fullbleed-dotnet/blob/v0.1.6/docs/api.md)
· [LINQ and variable-data example](https://github.com/fullbleed-engine/fullbleed-dotnet/tree/v0.1.6/samples/FullBleed.DotNet.LinqVdp)
· [CSS coverage](../css-coverage.md)
· [More document designs](../examples.md)
· [Report a .NET issue](https://github.com/fullbleed-engine/fullbleed-dotnet/issues)
