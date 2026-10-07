# Tagged library notice in C#

A .NET 10 console starter that renders a fictional library workshop notice with
FullBleed.DotNet. Edit the bundled HTML, CSS, route illustration and fonts to
make your own document. Keep the font license notices with redistributed fonts.

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore -- --profile ua1 --out output/ua1
dotnet run -c Release --no-restore -- --profile ua2 --out output/ua2
```

Each output directory contains `notice.pdf`, native previews of the finalized
PDF, and `render.json` with its hash, inspection and rendering diagnostics.
The application fails if its supplied fonts leave missing glyphs. Output is
generated inside the .NET process using the package's native Rust library.

`PdfUa1` and `PdfUa2` select the output profile. A profile selection and the
built-in structural inspection do not establish accessibility for your content.
Run an independent PDF/UA validator against the exact final PDF and retain its
report. Review reading order, heading levels, table headers, contrast, image
descriptions and the usefulness of the content itself before delivery.

The illustration's alternative text describes the same straight corridor as
the visible route. If you change the illustration, update both its description
and caption. `example.org/workshops` is printed sample text, not an interactive
PDF link. All event details and access provisions in this example are fictional.

To deploy the console application, keep its complete publish output:

```sh
dotnet publish -c Release --no-restore -o output/publish
dotnet output/publish/AccessibleNotice.dll --profile ua1 --out output/published
```

The publish directory includes native libraries, templates, fonts and notices.
Use the matching .NET 10 runtime. The package provides Windows x64, Linux x64
(glibc), Intel macOS and Apple Silicon macOS binaries. Review the rendered
pages after changing content, dimensions or assets.
