using System.Security.Cryptography;
using System.Text.Json;
using FullBleed.DotNet;

var profileName = "ua1";
var output = "output";
for (var i = 0; i < args.Length; i++)
{
    if (args[i] is "--help" or "-h")
    {
        Console.WriteLine("dotnet run -- [--profile ua1|ua2] [--out directory]");
        return;
    }
    if (args[i] is not ("--profile" or "--out") || i + 1 == args.Length)
        throw new ArgumentException("Use --profile ua1|ua2 or --out directory. See --help.");
    var option = args[i++];
    if (option == "--profile") profileName = args[i];
    else output = args[i];
}
var profile = profileName switch
{
    "ua1" => PdfProfile.PdfUa1,
    "ua2" => PdfProfile.PdfUa2,
    _ => throw new ArgumentException("The profile must be ua1 or ua2."),
};
var assets = Path.Combine(AppContext.BaseDirectory, "Assets");
var html = File.ReadAllText(Path.Combine(assets, "notice.html"));
var css = File.ReadAllText(Path.Combine(assets, "notice.css"));
using var engine = new FullBleedEngine(new FullBleedEngineOptions
{
    PdfProfile = profile,
    DocumentLanguage = "en-US",
    DocumentTitle = "Your next chapter: Riverton Library workshop",
    Assets = [
        FullBleedAsset.FromPath(Path.Combine(assets, "Inter-Variable.ttf"), FullBleedAssetKind.Font),
        FullBleedAsset.FromPath(Path.Combine(assets, "DMSerifDisplay-Regular.ttf"), FullBleedAssetKind.Font),
        FullBleedAsset.FromPath(Path.Combine(assets, "route.svg"), FullBleedAssetKind.Svg, "route.svg"),
    ],
});

var result = engine.RenderPdfWithDiagnostics(html, css);
if (result.Diagnostics.MissingGlyphs.Count != 0)
    throw new InvalidOperationException("The supplied fonts do not cover every character. Inspect MissingGlyphs before distributing the PDF.");
Directory.CreateDirectory(output);
var pdfPath = Path.GetFullPath(Path.Combine(output, "notice.pdf"));
File.WriteAllBytes(pdfPath, result.Pdf);
var inspection = FullBleedEngine.InspectPdf(pdfPath);
var previews = engine.RenderFinalizedPdfImagePagesToDirectory(pdfPath, Path.Combine(output, "preview"), dpi: 120, stem: "notice");
var report = new
{
    profile = profileName,
    runtime = Environment.Version.ToString(),
    framework = AppContext.TargetFrameworkName,
    runtimeRid = System.Runtime.InteropServices.RuntimeInformation.RuntimeIdentifier,
    engine = FullBleedEngine.GetNativeFeatures(),
    pdfSha256 = Convert.ToHexString(SHA256.HashData(result.Pdf)).ToLowerInvariant(),
    inspection,
    diagnostics = result.Diagnostics,
    previews,
    scope = "Rendering and structural inspection. Run an independent PDF/UA validator and review content and reading order before delivery.",
};
File.WriteAllText(Path.Combine(output, "render.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"Created {pdfPath}: {inspection.PageCount} page(s), {profileName}. Previews and render.json are in {Path.GetFullPath(output)}.");
