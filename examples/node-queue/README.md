# Queue six PDF invoices in Node.js

This fictional batch uses Fullbleed's Node package 0.4.1 and its pinned 2.5.22
engine. Node.js 22 or newer is required. The npm package includes the engine and
fonts; rendering needs no Python, Rust, browser, or system-font installation.

```sh
npm ci --ignore-scripts
npm run render
```

Open `output/queued-invoices/NS-1042.pdf` through `NS-1047.pdf`, and the first
invoice's PNG preview. Change the six customer names in `render.mjs`, or edit
`invoice.html` and `invoice.css`. Customer names are escaped before insertion.
All example data is fictional.

The shared queue uses two active slots and four waiting slots. The six requests
fit in that admission limit. Extra simultaneous requests reject with
`QUEUE_FULL`; submit later work after accepted jobs settle or return a busy
response to a caller. The queue counts jobs rather than capping total memory.

For a server, create one queue at application scope and reuse it across requests.
The example closes its queue only after the batch finishes. `close()` cancels
unfinished jobs and waits for worker/process cleanup. Durable job storage and
retry policy belong in the surrounding application.

See https://docs.fullbleed.dev/guides/node-render-queue/ for deadlines,
cancellation, shutdown, and process isolation.

The project is MIT licensed. Font licenses ship with the installed dependency.
