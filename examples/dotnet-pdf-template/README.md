# Personalize an existing PDF with C#

Use a designed PDF as the background and place component-authored text over it
for each JSON record. The Common Ground certificate is fictional. The project
includes the background's editable HTML/CSS and its ready-to-use PDF.

With the .NET 10 SDK installed:

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore -- --out output
```

Open `output/certificates.pdf` and the three `page-*.png` previews. These show
the final composed PDF. `render.json` records the package version, input and
output hashes, missing-glyph check, repeated output, and preserved template.
The project pins FullBleed.DotNet 0.2.4. Native rendering needs no Python,
browser, rendering service, or system-font installation.

## Change the records and styling

Edit `Assets/data.json`, then choose a new output folder:

```sh
dotnet run -c Release --no-restore -- --out output-edited
```

Names allow 48 Unicode characters, workshop titles 80, and certificate IDs 20.
IDs accept ASCII letters, digits, periods, underscores, and hyphens. Dates use
`YYYY-MM-DD`. The project normalizes text, rejects invalid records, escapes
component text, checks font coverage, and uses smaller type for longer fields.
Review the final pages after editing data or layout.

`Overlay` in `Program.cs` builds each page with `Section` and `Paragraph`.
`WithClass("name")` labels a paragraph; the `.name` rule in `Assets/overlay.css`
supplies its appearance. The outer `Document.Styles` attaches that stylesheet.
Edit its rules to change field positions, colors, font sizes, and spacing.

## Change the background

The supplied page is 792 by 612 points (US Letter landscape). Positions in
`Assets/overlay.css` start at the top-left; one inch is 72 points. Keep the
overlay transparent so it does not cover the artwork.

Edit `Assets/template.html` and `Assets/template.css`, then rebuild to a new PDF:

```sh
dotnet run -c Release --no-restore -- build-template --out revised-template.pdf
dotnet run -c Release --no-restore -- --template revised-template.pdf --out output-revised
```

You can also supply another readable, unencrypted, unsigned, one-page PDF.
Use an unrotated page and adjust the CSS page size and field positions to fit.
The application checks readability, encryption, and page count; it does not
automatically check page geometry or align fields. Existing output paths and
the source PDF are preserved.

This composes static PDF content. It does not discover or fill AcroForm fields,
replace existing text, preserve digital signatures, or make the result tagged
or accessible. Source annotations are omitted. Use a template without
interactive content. The repeat check applies within one installed runtime,
not across engine versions.

Code and artwork are MIT licensed. The bundled Inter font retains its SIL Open
Font License in `Assets/Inter-OFL.txt`.
