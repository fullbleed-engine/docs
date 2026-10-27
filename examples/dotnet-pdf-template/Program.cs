using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using FullBleed.DotNet;
using FullBleed.DotNet.UI;
using Fullbleed.PdfTemplate;
using static FullBleed.DotNet.UI.Components;

try
{
    if (args is ["--help"] or ["-h"])
    {
        Console.WriteLine("dotnet run -- [--data records.json] [--template template.pdf] [--out output]\n" +
            "dotnet run -- build-template --out revised-template.pdf");
        return 0;
    }
    var buildTemplate = args.FirstOrDefault() == "build-template";
    var options = Parse(args.Skip(buildTemplate ? 1 : 0).ToArray(), buildTemplate);
    var assets = Path.Combine(AppContext.BaseDirectory, "Assets");
    var font = Path.Combine(assets, "Inter-Variable.ttf");
    if (buildTemplate)
    {
        var path = Path.GetFullPath(options["--out"]);
        RequireNewPath(path);
        using var builder = new FullBleedEngine(new FullBleedEngineOptions
        {
            Assets = [FullBleedAsset.FromPath(font, FullBleedAssetKind.Font)],
        });
        var backgroundRender = builder.RenderPdfWithDiagnostics(File.ReadAllText(Path.Combine(assets, "template.html")),
            File.ReadAllText(Path.Combine(assets, "template.css")));
        if (backgroundRender.Diagnostics.MissingGlyphs.Count != 0)
            throw new InvalidDataException("The template font is missing required glyphs.");
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllBytes(path, backgroundRender.Pdf);
        Console.WriteLine(path);
        return 0;
    }

    var output = Path.GetFullPath(options.GetValueOrDefault("--out", "output"));
    RequireNewPath(output);
    var template = Path.GetFullPath(options.GetValueOrDefault("--template", Path.Combine(assets, "template.pdf")));
    var records = CertificateRecords.Load(options.GetValueOrDefault("--data", Path.Combine(assets, "data.json")));
    var inspection = FullBleedEngine.InspectPdf(template);
    if (inspection.Encrypted || inspection.PageCount != 1)
        throw new InvalidDataException("Use a readable, unencrypted, one-page template.");
    var original = File.ReadAllBytes(template);
    var document = new Document(records.Select(Overlay))
    {
        Title = "Common Ground certificates",
        Language = "en-US",
        IncludeComponentStyles = false,
        Styles = StyleSheet.FromCss(File.ReadAllText(Path.Combine(assets, "overlay.css"))),
    };
    using var engine = new FullBleedEngine(new FullBleedEngineOptions
    {
        DocumentTitle = document.Title,
        DocumentLanguage = document.Language,
        Assets = [FullBleedAsset.FromPath(font, FullBleedAssetKind.Font)],
    });
    var rendered = document.RenderPdfWithDiagnostics(engine);
    if (rendered.Diagnostics.MissingGlyphs.Count != 0)
        throw new InvalidDataException("Inter is missing required glyphs. Register a suitable font and update overlay.css.");
    if (!rendered.Pdf.SequenceEqual(document.RenderPdf(engine)))
        throw new InvalidOperationException("Repeated overlay output changed.");
    Directory.CreateDirectory(output);
    var overlay = Path.Combine(output, "overlay.pdf");
    File.WriteAllBytes(overlay, rendered.Pdf);
    File.WriteAllText(Path.Combine(output, "overlay.html"), document.ToHtml());
    File.WriteAllText(Path.Combine(output, "overlay.css"), document.ToCss());
    if (FullBleedEngine.InspectPdf(overlay).PageCount != records.Count)
        throw new InvalidDataException("Expected one overlay page per record. Review overlay.css.");
    var composition = new ComposeOptions
    {
        Templates = [new ComposeTemplate("certificate", template)],
        Plan = Enumerable.Range(0, records.Count).Select(page => new ComposePage("certificate", 0, page)).ToList(),
        AnnotationMode = ComposeAnnotationMode.None,
    };
    File.WriteAllText(Path.Combine(output, "plan.json"), JsonSerializer.Serialize(composition, new JsonSerializerOptions { WriteIndented = true }));
    var pdf = Path.Combine(output, "certificates.pdf");
    var repeat = Path.Combine(output, "certificates-repeat.pdf");
    var result = FullBleedEngine.ComposePdf(overlay, pdf, composition);
    FullBleedEngine.ComposePdf(overlay, repeat, composition);
    if (result.PagesWritten != records.Count || !File.ReadAllBytes(pdf).SequenceEqual(File.ReadAllBytes(repeat)) ||
        !original.SequenceEqual(File.ReadAllBytes(template)))
        throw new InvalidOperationException("Page count, repeatability or template preservation failed.");
    var previews = engine.RenderFinalizedPdfImagePagesToDirectory(pdf, output, dpi: 110, stem: "certificate");
    if (previews.Paths.Count != records.Count)
        throw new InvalidOperationException("Expected one final PDF preview per record.");
    var previewRecords = new List<object>();
    for (var index = 0; index < previews.Paths.Count; index++)
    {
        var filename = $"page-{index + 1}.png";
        var path = Path.Combine(output, filename);
        File.Move(previews.Paths[index], path);
        previewRecords.Add(new { file = filename, sha256 = Hash(path) });
    }
    var report = new
    {
        schema = "fullbleed.dotnet.pdf_template.v1",
        packageVersion = FullBleedEngine.GetNativeFeatures().BindingVersion,
        records = records.Count, pages = result.PagesWritten,
        templateSha256 = Hash(template), templateUnchanged = true,
        overlaySha256 = Hash(overlay), pdfSha256 = Hash(pdf), fontSha256 = Hash(font),
        missingGlyphs = rendered.Diagnostics.MissingGlyphs.Count, deterministicRepeat = true,
        annotationMode = "none", previews = previewRecords,
        scope = "One static template plus one component-authored overlay per record. Ordinary noninteractive PDFs; no AcroForm, signature, tagging or standards-conformance claim.",
    };
    File.WriteAllText(Path.Combine(output, "render.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine(JsonSerializer.Serialize(report));
    return 0;
}
catch (Exception error) when (error is ArgumentException or InvalidDataException or IOException or UnauthorizedAccessException or JsonException or FullBleedException)
{
    Console.Error.WriteLine(error.Message);
    return 2;
}

static Element Overlay(CertificateRecord record)
{
    var nameLength = record.Name.EnumerateRunes().Count();
    return Section(
        Paragraph(record.Name).WithClass("name", nameLength > 28 ? "long" : nameLength > 19 ? "medium" : null),
        Paragraph(record.Workshop).WithClass("workshop", record.Workshop.EnumerateRunes().Count() > 40 ? "long" : null),
        Paragraph(record.DateLabel).WithClass("date"),
        Paragraph(record.CertificateId).WithClass("id", record.CertificateId.Length > 16 ? "long" : null)
    ).WithClass("certificate");
}

static Dictionary<string, string> Parse(string[] arguments, bool buildTemplate)
{
    var allowed = buildTemplate ? new[] { "--out" } : ["--data", "--template", "--out"];
    var parsed = new Dictionary<string, string>();
    for (var index = 0; index < arguments.Length; index += 2)
    {
        if (!allowed.Contains(arguments[index]) || index + 1 >= arguments.Length || string.IsNullOrWhiteSpace(arguments[index + 1]) ||
            !parsed.TryAdd(arguments[index], arguments[index + 1]))
            throw new ArgumentException("Use --data, --template and --out once each with a path; use --help for examples.");
    }
    if (buildTemplate && !parsed.ContainsKey("--out"))
        throw new ArgumentException("build-template requires --out with a new PDF path.");
    return parsed;
}

static void RequireNewPath(string path)
{
    if (File.Exists(path) || Directory.Exists(path))
        throw new IOException("Choose a new output path; existing files and folders are preserved.");
}

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
