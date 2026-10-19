---
title: Browse Fullbleed's CSS comparison results
description: Search all 1,662 CSS fixtures tested with the published Fullbleed 2.5.34 wheel. Inspect original verdicts, reference images and generated PDFs, including failures and disputed references.
hide:
  - toc
---

# See what the CSS tests render

Find a layout or CSS feature, compare the printed pages, and download the actual
Fullbleed PDF. The default view shows a maintainer-run comparison of the **published Fullbleed
2.5.34 Linux wheel** against the pinned, independent IronPress corpus.

Choose a package version to inspect its own results. Shared case links keep the
selected version, filters and fixture. You can also [open the historical 2.5.22
results](css-explorer.md?version=2.5.22) or read their
[evidence record](css-corpus.md#latest-published-wheel-2522).

**The comparison gate fails.** Passing fixtures meet the comparator's policy;
they do not establish complete CSS support or pixel-identical output. Failures
and disputed references retain their original labels. [Read the method and
limits](css-corpus.md).

<link rel="stylesheet" href="../../assets/css-corpus/explorer-v2.css?v=27dbf42a99ab">
<div id="css-explorer" class="css-explorer" data-index="../../assets/css-corpus/2.5.34/index.json" data-versions="../../assets/css-corpus/versions.json?v=2.5.34">
  <p id="ce-loading" role="status">Loading the fixture index…</p>
  <div id="ce-controls" hidden>
    <p id="ce-provenance" class="ce-links"></p>
    <div class="ce-version"><label for="ce-version">Package version</label><select id="ce-version"></select></div>
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
<script src="../../assets/css-corpus/explorer-v2.js?v=208c9fae54c1"></script>

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
