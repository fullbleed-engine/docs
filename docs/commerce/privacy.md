---
title: Fullbleed Commerce privacy
description: How the Fullbleed Commerce Shopify development preview processes order data, private PDF links, usage records, and privacy requests.
---

# Fullbleed Commerce privacy

Updated October 4, 2026.

**Development preview:** the hosted Shopify app currently accepts synthetic
test stores only. It is not open to production merchants. This notice describes
that preview and will be updated before a production launch.

Fullbleed Commerce is maintained by Keenan Finkelstein in the United States.
Contact [keenan@fullbleed.dev](mailto:keenan@fullbleed.dev) about privacy, access,
correction, deletion, or support.

This notice covers the hosted Shopify integration. The separate
[free WooCommerce plugin](../guides/woocommerce.md) renders locally in the
merchant's browser without sending orders to a Fullbleed service.

## Information used to create documents

When authorized store staff request an order summary or packing slip, or enable
a Shopify Flow action, the app reads the selected order from Shopify. It
processes order identifiers, items, prices, totals, and billing and shipping
names and addresses in server memory to generate the requested PDF.
**The application database does not store order contents or generated PDFs.**

The app stores your Shopify authorization session and credentials so it can
perform authorized requests. It also stores seller branding and preferences,
and the HTML, CSS, and embedded logos you save in Template studio. Use template
fields for customer information instead of pasting customer details into a
saved template.

The app checks your subscription and billing period with Shopify. Shopify
handles plan selection and payment; Fullbleed does not collect payment-card
details. We use app data to provide documents, authenticate access, operate
automation, enforce plan allowances, respond to privacy requests, and diagnose
service failures. We do not sell customer data or use it for advertising.

## Automation and private links

Automation records contain your store, order and action-run identifiers,
document verification hashes, template revisions, job status, timestamps, and
download counts. Job history does not contain customer names, addresses, or
PDF contents.

Private PDF links expire and can be revoked by the merchant. Opening a valid
link rechecks app access and regenerates the unchanged order and template in
memory. **Anyone holding the complete link can download its document while the
link remains valid.** Share it only with the intended recipient. Downloaded
copies remain on the receiving device; revoking a link does not delete them.

Plan usage records contain your store, billing-period dates, order identifiers,
and successful processing times. An order counts once per billing period,
including previews, automation, and downloads. Failed work does not count.

## Retention and deletion

### Access history

The Shopify preview includes **Access history**, available to authenticated
store staff even without a paid plan. It records requests for order lists,
document previews and PDFs, automation activity, privacy exports and access
history itself. It also records Flow document preparation and private-link
downloads. An attended hosted test verified these records, privacy deletion,
uninstall and backup restoration using synthetic store data. The preview is
stopped between attended tests and remains closed to production merchants.

Each entry contains the store, action, time, outcome and relevant order, job or
privacy-request reference. Staff requests include the staff ID from the verified
Shopify session. Automated requests use a Flow run or document job identifier;
a private link does not identify the person holding it. The history excludes
customer names, addresses, document contents, full download links, tokens and
IP addresses. A collection read records the action without listing every
customer or order returned.

Entries expire after 30 days. Customer erasure removes matching order and
associated privacy-export references sooner; marking a privacy request handled
removes references to that export. Uninstall and shop erasure remove all of the
store's access history. Generic collection-read entries contain no customer
reference and follow the 30-day policy. Encrypted recovery copies follow the
restoration and deletion process below.

### Application records

| Information | Retention in the live application database |
| --- | --- |
| Authorization, branding, and saved templates | Until replaced or deleted where the app offers that action, or until an authenticated uninstall or shop-erasure notification is processed. |
| Automation job history | 30 days. Customer erasure revokes affected links and clears order references and verification hashes. Empty action-run records can remain for up to 30 days to prevent delayed retries from recreating a document. |
| Plan usage | The billing period plus 30 days. Customer erasure removes affected order references while retaining the period's aggregate count. Uninstall and shop erasure remove all of the store's usage records. |
| Outstanding customer-data exports | Until the merchant marks the request handled or Shopify requests erasure. Overdue requests remain visible and require action. |
| Completed or erased privacy-request receipts | 30 days after completion or erasure, without the live export, customer identity hashes, or order references. |
| Access history | 30 days, with earlier deletion of the corresponding order, privacy-export or store references as described above. |

Cleanup runs at startup and hourly while the app is running. An outage or a
paused preview can delay removal. Authenticated uninstall and shop-erasure
notifications clear the store's live sessions, preferences, templates,
automation, usage, privacy-request records, and access history. Encrypted recovery copies have
the separate retention described below.

## Customer privacy requests

When Shopify sends a customer-data request, Fullbleed captures an encrypted
export of retained automation and order-usage metadata, including the customer
ID or email supplied to identify the request. Requested order references and
keyed identity hashes support subsequent deletion.

The export also includes retained access history for the requested orders,
without staff identifiers or unrelated-store records.

Authorized store staff can download the export from **Privacy requests**
without a paid plan, then respond through the store's privacy process.
Fullbleed does not email these exports. The app displays the 30-day response
deadline and flags overdue requests. Marking a request handled immediately
clears its live export, identity hashes, and order references.

Customers should contact the store that collected their order information to
request access, correction, or deletion. Merchants can also contact
[keenan@fullbleed.dev](mailto:keenan@fullbleed.dev) for assistance with data held
by Fullbleed. Please do not email access tokens, complete private PDF links, or
payment details.

## Hosting, logs, and recovery copies

The preview runs on Railway in the United States. Its application database
uses a private service volume. Recovery copies are encrypted with a separate
key and stored in a private US West bucket. Shopify supplies the authorized
order data and handles app authentication, Flow, and billing.

The hosting service records connection metadata such as IP address, browser
user agent, request path, time, and response status, along with application
diagnostics. These records support security and troubleshooting. Railway's
current plan exposes seven days of logs; this is **not a guarantee of physical
deletion after seven days**, because its documentation says a plan upgrade can
restore older logs. See [Railway's logging documentation](https://docs.railway.com/observability/logs)
and [privacy policy](https://railway.com/legal/privacy). The app does not add
advertising trackers or storefront tracking scripts. Shopify authentication
and the hosting platform operate their own necessary session and connection
mechanisms.

Database backups become ineligible for restoration after seven days and are
scheduled for removal after eight days. Encrypted erasure and completion
instructions remain for 35 days so restoring an older backup does not revive
cleared data. Those instructions contain store and order references and keyed
customer identifiers, not customer names, addresses, or export contents.

Recovery cleanup runs at startup and hourly while the app is online, so an
outage can delay physical removal. Restoration reapplies later erasure
instructions, clears authorization sessions, and pauses automation before the
database is used. The running hosted service creates verified backups daily;
no daily backup runs while the preview is stopped.

Independent key recovery, operator notifications, and production rollout still
require verification before launch. No production customer records are
accepted in this preview.
