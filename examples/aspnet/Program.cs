if (args is ["--preview", var directory])
{
    using var renderer = new InvoiceRenderer();
    renderer.WritePreview(directory);
    return;
}

var builder = WebApplication.CreateBuilder(new WebApplicationOptions
{
    Args = args,
    ContentRootPath = AppContext.BaseDirectory,
});
builder.Services.AddSingleton<InvoiceRenderer>();

var app = builder.Build();
app.Use(async (context, next) =>
{
    context.Response.Headers.XContentTypeOptions = "nosniff";
    if (context.Request.Path.StartsWithSegments("/invoices"))
    {
        context.Response.Headers.CacheControl = "private, no-store";
    }
    await next(context);
});

app.MapGet("/", () => Results.Content(
    File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Assets", "home.html")), "text/html"));
app.MapGet("/invoice.png", () => Results.File(
    Path.Combine(AppContext.BaseDirectory, "Assets", "invoice.png"), "image/png"));
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapGet("/invoices/{id}/pdf", IResult (
    string id, InvoiceRenderer renderer, HttpContext context, ILogger<InvoiceRenderer> logger) =>
{
    // Only a fictional fixture is public. Replace this with authentication and
    // an account-scoped lookup BEFORE accepting real invoice identifiers.
    if (!string.Equals(id, "NS-1042", StringComparison.Ordinal))
    {
        return Results.NotFound(new { error = "Invoice not found." });
    }
    context.RequestAborted.ThrowIfCancellationRequested();
    try
    {
        if (!renderer.TryRender(out var pdf))
        {
            context.Response.Headers.RetryAfter = "2";
            return Results.Problem(statusCode: 503, title: "PDF renderer is busy. Try again shortly.");
        }
        // Native rendering is synchronous: cancellation cannot interrupt it.
        context.RequestAborted.ThrowIfCancellationRequested();
        return Results.File(pdf, "application/pdf", fileDownloadName: "invoice-NS-1042.pdf");
    }
    catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
    {
        throw;
    }
    catch (Exception error)
    {
        // Do not put templates, document data, or filesystem paths in responses/logs.
        logger.LogError("Invoice PDF generation failed ({ErrorType}).", error.GetType().Name);
        return Results.Problem(statusCode: 500, title: "The invoice PDF could not be generated.");
    }
});

app.Run();
