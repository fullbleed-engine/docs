# C# component invoice

Compose a print document with ordinary C# methods, typed records, LINQ and style
objects. No HTML authoring, Python, browser or Rust compiler is required.

Install the .NET 10 SDK, extract this directory, then run:

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore -- output
```

Open `output/invoice.pdf` and `output/invoice_page1.png`. The program also writes
diagnostics and separate generated HTML/CSS. FullBleed.DotNet is pinned to 0.2.0,
using engine 2.5.22. Native libraries support Windows x64, Linux x64, Intel macOS
and Apple Silicon macOS. The library also supports .NET 8 and 9.

Edit the records in `InvoiceDocument.Example`, reuse `Field` and `ItemRow`, or
change `BaseStyles`. In `Program.cs`, try
`InvoiceDocument.Example with { Paid = true, Accent = "#245541" }`.
Items, totals and paid/unpaid messages are derived from that data. All sample
business details are fictional.

`WithClass("notice")` adds a label to an element. A `.notice` selector in a
`StyleSheet` supplies declarations; attach the sheet to `Document.Styles`.
`WithStyle(...)` applies inline declarations. Methods return immutable values;
keep the returned value when composing styles. Class names do not load styles
or scope them to a C# method. The guide has worked examples:
https://docs.fullbleed.dev/guides/csharp-components/#class-names-and-styles

The two font files are explicitly registered and use the included SIL Open Font
License notices. Keep those notices with redistributed fonts. Project code uses
the MIT license. `upstream.json` records the exact C# sample and asset sources.
