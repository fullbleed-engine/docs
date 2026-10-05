# Fullbleed PDF downloads in ASP.NET Core

A .NET 10 Minimal API that generates a fictional Northstar invoice from bundled HTML, CSS, and fonts. Uses the public `FullBleed.DotNet` 0.1.4 NuGet package (engine 2.5.8).

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore -- --urls http://127.0.0.1:5080
```

Open http://127.0.0.1:5080 and choose **Download sample PDF**.

## Edit and preview

Edit `Assets/invoice.html` and `Assets/invoice.css`. Fonts and OFL license notices are in `Assets/fonts`.

```sh
dotnet run -c Release -- --preview output
```

Inspect `output/invoice.pdf` and `output/invoice_page1.png`. Copy the PNG to `Assets/invoice.png` to update the download page, then restart the app. The preview is rendered from the final PDF, not a browser screenshot.

## Publish

```sh
dotnet publish -c Release --no-restore -o output/publish
dotnet output/publish/FullbleedWeb.dll --urls http://127.0.0.1:5080
```

Keep the whole publish directory: it contains native libraries, templates, fonts, and notices. Install the .NET 10 ASP.NET Core runtime on the server. The NuGet package includes win-x64, linux-x64 (glibc), osx-x64, and osx-arm64 binaries. This starter's Windows/Linux checks do not establish support for Alpine/musl, ARM Linux, trimming, Native AOT, single-file publishing, or a particular hosting provider.

## Before connecting customer records

The single fixture is intentionally public. Add your application's authentication and an account-scoped invoice query before serving real data. Escape data inserted into HTML (for example, `WebUtility.HtmlEncode`); keep templates and asset paths under application control. Do not expose an arbitrary HTML rendering API.

PDF responses, including errors, use `private, no-store` and `nosniff`. Each request creates and disposes its own native engine. One render may run per process; overlapping requests receive `503` with `Retry-After: 2`, without a waiting queue. This is not a per-customer usage limit or a distributed limiter.

Native rendering is synchronous. A disconnected request is checked before and after rendering, but cannot cancel an in-progress native call. A hard time/memory limit requires an isolated worker process or job service. This example does not implement taxes, invoice numbering, payments, PDF standards conformance, or application authorization.

See the [complete guide and verification evidence](https://docs.fullbleed.dev/guides/aspnet-pdf/).
