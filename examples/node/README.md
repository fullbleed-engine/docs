# Designed invoices and reports from Node.js

This fictional Northstar Studio invoice uses Fullbleed's Node package 0.9.0,
which bundles the Fullbleed 2.5.46 engine and Inter, DM Serif Display, and Bebas
Neue fonts. You need Node.js 22 or newer; no Python or Rust installation is needed.

```bash
npm ci --ignore-scripts
npm run render
```

Open `output/invoice/invoice.pdf` and `output/invoice/page-1.png`. Change the
`customer` value in `render.mjs`; the script escapes it before insertion into HTML.
Edit `invoice.html` and `invoice.css` for your own layout and data.

The same project includes the three-page Common Ground report:

```bash
npm run render:report
```

Open `output/report/report.pdf` and its `page-1.png` through `page-3.png` previews.
Edit `report.html` and `report.css` to use your own layout and data. Both designs
use fictional data.

The lockfile pins Fullbleed 0.9.0 from npm and its integrity hash.
The package renders locally; it does not upload documents to a service.

The sample and engine are MIT licensed. The package retains the bundled font
licenses. See the [Node guide](https://docs.fullbleed.dev/getting-started/node/)
for API options and the verification scope.
