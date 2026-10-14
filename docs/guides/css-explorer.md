---
title: Browse Fullbleed's CSS comparison results
description: Search all 1,662 CSS fixtures tested with the published Fullbleed 2.5.22 wheel. Inspect original verdicts, reference images and generated PDFs, including failures and disputed references.
hide:
  - toc
---

# See what the CSS tests render

Find a layout or CSS feature, compare the printed pages, and download the actual
Fullbleed PDF. This is a maintainer-run comparison of the **published Fullbleed
2.5.22 Linux wheel** against the pinned, independent IronPress corpus.

**The comparison gate fails.** Passing fixtures meet the comparator's policy;
they do not establish complete CSS support or pixel-identical output. Failures
and disputed references retain their original labels. [Read the method and
limits](css-corpus.md).

<link rel="stylesheet" href="../../assets/css-corpus/explorer.css">
<div id="css-explorer" class="css-explorer" data-index="../../assets/css-corpus/2.5.22/index.json">
  <p id="ce-loading" role="status">Loading the fixture index…</p>
  <div id="ce-controls" hidden>
    <p id="ce-provenance" class="ce-links"></p>
    <div class="ce-filters">
      <label for="ce-search">Search fixtures<input id="ce-search" type="search" placeholder="Try grid, counters, or border-image" autocomplete="off"></label>
      <label for="ce-category">CSS category<select id="ce-category"><option value="">All categories</option></select></label>
      <label for="ce-verdict">Verdict<select id="ce-verdict"><option value="">All verdicts</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option><option value="REFERENCE-DISPUTED">REFERENCE-DISPUTED</option></select></label>
    </div>
    <p id="ce-counts" class="ce-counts"></p>
    <p id="ce-results-status" role="status" aria-live="polite"></p>
    <section id="ce-detail" class="ce-detail" aria-labelledby="ce-detail-title" tabindex="-1" hidden></section>
    <div id="ce-results" class="ce-results"></div>
    <nav class="ce-pagination" aria-label="Fixture result pages"><button id="ce-previous" type="button">Previous</button><span id="ce-page"></span><button id="ce-next" type="button">Next</button></nav>
  </div>
</div>
<script src="../../assets/css-corpus/explorer.js" defer></script>

<noscript>The interactive filters require JavaScript. The <a href="../css-corpus/">evidence guide</a> also links to the complete downloadable report.</noscript>

## Read a result

- **PASS:** the fixture meets the unchanged upstream comparison policy.
- **FAIL:** a comparison or rendering check failed. Inspect the actual pages;
  the label alone does not identify the cause or establish missing content.
- **REFERENCE-DISPUTED:** the candidate differs from a reference marked disputed
  by the upstream corpus. These cases are not counted as passes.

The reference's own status is shown separately, including when a fixture with a
disputed reference receives a PASS verdict. The images use the original report's
rasterization, and each PDF download preserves the tested bytes.
Reference notes are upstream review text; mentions of IronPress in those notes
describe that project's reference review.

The corpus uses static HTML/CSS and explicit assets. Its results do not establish
support for every CSS feature, arbitrary websites, browser JavaScript,
accessibility standards, or PDF conformance. Try representative data and your
own fonts in the [HTML/CSS playground](../playground.md) before choosing a layout.
