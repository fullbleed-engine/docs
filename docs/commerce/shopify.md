---
title: Shopify PDF automation preview
description: See Fullbleed Commerce turn saved visual or HTML/CSS templates into order documents through Shopify Flow, with a recorded synthetic-store walkthrough.
---

# Shopify PDF automation preview

Design an order document once, then prepare it from your order workflow.
Fullbleed Commerce combines a visual and HTML/CSS template editor with native
Shopify Flow actions for order summaries and packing slips.

!!! note "Development preview"
    This app is being tested on synthetic orders. It is not available for
    production stores or approved for the Shopify App Store. Hosting stops
    between attended tests. The walkthrough demonstrates the working preview;
    it does not demonstrate a paid merchant purchase.

## Watch the workflow

The four-minute recording shows installation, a saved custom template, brand
settings, a manual test of an existing Flow workflow, document activity, and
pausing automation. It uses an existing development-store test plan. English
instructions are included in the video; idle intervals are removed and playback
is 1.3 times the recorded speed.

<video controls preload="metadata" playsinline width="1600" height="900" style="width:100%;height:auto" poster="../../assets/commerce/shopify-automations.png" aria-label="Fullbleed Commerce synthetic-store walkthrough with English captions">
  <source src="../../assets/commerce/fullbleed-commerce-walkthrough.mp4" type="video/mp4">
  <p><a href="../../assets/commerce/fullbleed-commerce-walkthrough.mp4">Download the walkthrough video</a>.</p>
</video>

[Download the MP4](../assets/commerce/fullbleed-commerce-walkthrough.mp4).

## Customize the document

In **Template studio**, choose an order summary or packing slip. Drag blocks,
edit text, insert order fields, and style the layout. Switch to **HTML / CSS**
to paste or adjust a template. Preview it with a recent order before saving.
Each document type has its own saved template.

**Brand settings** supplies the seller name and contact lines, Studio, Contrast
or Quiet design, A4 or Letter paper, accent color, and closing note. Saved custom
templates keep their own CSS.

The verified workflow produced these synthetic documents:

- [Custom order summary PDF](../assets/commerce/shopify-custom-order-summary.pdf)
  — a visual text edit and CSS accent change applied to the saved template.
- [Contrast packing slip PDF](../assets/commerce/shopify-contrast-packing-slip.pdf)
  — recipient details, item quantities and packing checkboxes, without prices.

## Connect Shopify Flow

1. Preview and save your templates, then enable **Flow automation** in Fullbleed.
2. Create an **Order created** workflow in Shopify Flow.
3. Add **Create order summary link** and **Create packing slip link**, each
   using the triggering order.
4. Pass each action's `downloadUrl` and `expiresAt` to your chosen following
   steps. The demonstrated recipe saves four private order metafields for staff.
5. Test with a synthetic order and confirm the complete Flow run, both expiry
   times, and both downloads before using a delivery destination.

The [complete recipe](https://github.com/fullbleed-engine/fullbleed-commerce/blob/main/shopify/recipes/order-documents.md)
includes the field definitions, access settings, and variable mapping. The
recorded workflow was already configured and was manually retried to verify the
new saved template. It completed seven actions: two document preparations, four
field updates, and one diagnostic log.

## Know what a ready link means

Fullbleed renders and verifies the document before returning its private link.
The browser downloads in this check matched the preparation hashes. A manual
reprint using the same saved template produced the same PDF. The order counted
once in its billing period.

Links expire after 24 hours by default. Changing the order or template invalidates
them; pausing automation revokes active links. Anyone with a complete link can
download while it is valid, so share it only with the intended recipient. Fullbleed
does not send customer emails, collect order payments, or mark orders fulfilled.

Order summaries are not fiscal invoices. The preview rejects edited, cancelled
or refunded orders, more than 250 items, and unsupported characters.

See the [privacy notice](privacy.md),
[Commerce source and verification](https://github.com/fullbleed-engine/fullbleed-commerce),
or [generate a PDF directly with Node.js](../getting-started/node.md).
