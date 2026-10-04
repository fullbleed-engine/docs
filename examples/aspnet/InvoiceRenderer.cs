using System.Security.Cryptography;
using System.Text.Json;
using FullBleed.DotNet;

public sealed class InvoiceRenderer : IDisposable
{
    private static readonly string Assets = Path.Combine(AppContext.BaseDirectory, "Assets");
    private readonly SemaphoreSlim renderGate = new(1, 1);

    public bool TryRender(out byte[] pdf)
    {
        pdf = [];
        if (!renderGate.Wait(0))
        {
            return false;
        }
        try
        {
            pdf = Render();
            return true;
        }
        finally
        {
            // Release when rendering finishes, before sending bytes to a slow client.
            renderGate.Release();
        }
    }

    public void Dispose() => renderGate.Dispose();

    private static FullBleedEngine CreateEngine() => new(new FullBleedEngineOptions
    {
        DocumentLanguage = "en-US",
        DocumentTitle = "Northstar Studio - Invoice NS-1042",
        Assets = Directory.GetFiles(Path.Combine(Assets, "fonts"), "*.ttf")
            .Order(StringComparer.Ordinal)
            .Select(path => FullBleedAsset.FromPath(path, FullBleedAssetKind.Font))
            .ToList(),
    });

    public byte[] Render()
    {
        // No native engine handle is shared between requests.
        using var engine = CreateEngine();
        var result = engine.RenderPdfWithDiagnostics(
            File.ReadAllText(Path.Combine(Assets, "invoice.html")),
            File.ReadAllText(Path.Combine(Assets, "invoice.css")));
        if (result.Diagnostics.MissingGlyphs.Count != 0)
        {
            throw new InvalidOperationException("The registered fonts do not cover the invoice text.");
        }
        return result.Pdf;
    }

    public void WritePreview(string directory)
    {
        var output = Path.GetFullPath(directory);
        Directory.CreateDirectory(output);
        var pdf = Render();
        var path = Path.Combine(output, "invoice.pdf");
        File.WriteAllBytes(path, pdf);
        using var engine = CreateEngine();
        var inspection = FullBleedEngine.InspectPdf(path);
        var previews = engine.RenderFinalizedPdfImagePagesToDirectory(path, output, dpi: 96, stem: "invoice");
        var report = new
        {
            runtime = Environment.Version.ToString(),
            pages = inspection.PageCount,
            missingGlyphs = 0,
            pdfSha256 = Convert.ToHexStringLower(SHA256.HashData(pdf)),
            previewFiles = previews.Paths.Select(Path.GetFileName),
        };
        var json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(Path.Combine(output, "preview.json"), json + "\n");
        Console.WriteLine(json);
    }
}
