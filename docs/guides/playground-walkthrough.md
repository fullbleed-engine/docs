---
title: Customize an invoice in the playground
description: "Watch a short Fullbleed walkthrough: edit an invoice with HTML and CSS, download the PDF, and run the exported Node.js project locally."
---

# Customize an invoice in the playground

Start with the Northstar invoice in the [free playground](../playground.md).
Change its recipient and heading color, download the PDF, then take the editable
project into your own workflow. No account is needed to try it.

<video id="invoice-walkthrough" controls preload="none" playsinline width="1920" height="1080" style="display:block;width:100%;height:auto;aspect-ratio:16/9" poster="../../assets/walkthroughs/invoice-20261102/poster.png" aria-label="Customize a Fullbleed invoice with HTML and CSS" aria-describedby="invoice-walkthrough-note">
  <source src="../../assets/walkthroughs/invoice-20261102/walkthrough.mp4" type="video/mp4">
  <track kind="captions" src="../../assets/walkthroughs/invoice-20261102/captions.vtt" srclang="en" label="English">
  Your browser cannot play this video. Read the transcript below or download the MP4.
</video>
<p id="invoice-walkthrough-note">A silent walkthrough with on-screen instructions and optional English captions. <a href="#transcript">Read the transcript</a> or <a href="../../assets/walkthroughs/invoice-20261102/walkthrough.mp4" download>download the MP4</a>.</p>

## Transcript

The recording uses the fictional **Northstar invoice** example.

1. Open the [playground](../playground.md) and wait for the first PDF preview.
2. In the **HTML** editor, change `Maple &amp; Finch` to `Willow &amp; Finch`.
3. Select **CSS** and add this rule at the end:

    ```css
    .invoice h1 { color: #b14d2e; }
    ```

4. Choose **Render PDF**. The preview now shows the new recipient and a terracotta
   **INVOICE** heading.
5. Choose **Download PDF** to save the finished invoice.
6. Expand **Files and projects**, select **Node.js**, and choose **Download project**.
   You can also choose Python when exporting your own project.

## Continue locally

Use **Node.js 22 or newer**. Extract the Node.js project ZIP and open a terminal in
the extracted folder. Run:

```bash
npm ci --ignore-scripts
npm run render
```

The renderer writes `output/document.pdf` and `output/preview/page-1.png`.
Edit `input.html` or `style.css`, then run `npm run render` again.
The ZIP includes the fonts, licenses, dependency lockfile, and renderer.

For application data and reusable templates, continue with the
[Node.js quickstart](../getting-started/node.md). For a Python export, follow the
commands in [Keep building](../playground.md#keep-building).
