---
title: Python component release status and stabilization
description: Choose the stable Fullbleed Python component API or its opt-in 2.6 alpha. See what is verified and what remains before the new API becomes stable.
---

# Python component release status

Reviewed **26 October 2026**. Fullbleed's released Python component API is
available today. The newer API remains an opt-in alpha.

| Channel | Install | Authoring surface |
| --- | --- | --- |
| Stable **2.5.35** | `python -m pip install fullbleed` | HTML/CSS rendering and the existing `fullbleed.ui` components |
| Alpha **2.6.0a14** | `python -m pip install --pre "fullbleed==2.6.0a14"` | New authoring values under `fullbleed.components`; earlier imports remain supported |

Start with the [Python quickstart](../getting-started/quickstart.md) for either
HTML/CSS or stable components. Both examples produce the same invoice.
The [stable component guide](python-components.md) explains function components,
children, `class_name`, inline styles and attached stylesheets.

The alpha adds component-owned styles, named customization parts, column-based
tables, static Bootstrap helpers, repeating page bands, and HTML export with or
without styles. The [namespace and migration guide](component-preview-12.md)
includes explicit styling examples and a complete kit pinned to alpha 12.
Those authoring paths remain supported in the current alpha.

Alpha 14 adds [native PDF links](pdf-links.md), including section jumps, web
URLs and email links. It also corrects inline opacity and mixed-content table
alignment. The earlier rich-inline initial fixes remain included.

For interactive walkthroughs, [Explore the versioned component notebook](../getting-started/component-notebook.md)
or [Try the current styling notebook](../getting-started/component-styling.md).
Each notebook states its own package pin and includes downloadable output.

## Decision: retain the alpha

The component authoring implementation is **merged into `master`**, and
prerelease packages are published on PyPI. The alpha label describes the API
compatibility promise; merging the implementation does not make that promise
stable. Ordinary `pip install fullbleed` continues to select the stable channel.

The current release has substantial rendered-output evidence, including paired
HTML/CSS and component showcases, saved PDFs, styled/unstyled HTML, page-band
checks, typing checks and browser layout checks. The
[alpha 14 release](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a14)
records the exact package and fixture evidence. Passing those checks establishes
the tested behavior; it does not settle how the API should evolve for its callers.

The namespace and migration gate is qualified in alpha 12. The intended public
path is `fullbleed.components`, with static Bootstrap helpers at
`fullbleed.components.bootstrap`. Earlier imports remain supported. The
[complete migration kit](component-preview-12.md#migrate-a-whole-document)
covers styles, geometry, metadata and renderer configuration, retaining the
same output for both authoring paths. This closes the namespace decision, not
the API's remaining stabilization work.

Two stabilization gates remain:

| Gate | Current position | What closes it |
| --- | --- | --- |
| Components from independent kits | The [kit-composition guide](component-kits.md) qualifies concrete palette factories, explicit prefixed dependencies and local overrides with two maintainer-authored modules. Tokens remain document-wide; the example does not supply independent-kit evidence. | Confirm the documented convention with two independently authored kits: defaults, required values, conflicting names and local overrides must be clear without inspecting implementation details. A new scoping mechanism is not automatically required. |
| Authoring and customization feedback | Maintainer-authored fixtures cover the intended edits, but retained independent author feedback is still missing. | Have independent authors rebrand a document, reuse a component, add a table column, change page size and diagnose a layout failure. Record where internal selectors or undocumented knowledge are needed, then resolve those contract gaps. |

These are bounded API decisions, not a requirement to implement every CSS feature
before a stable release. The earlier
[implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/master/docs/component-authoring-design.md)
and [design follow-up](https://github.com/fullbleed-engine/fullbleed-official/blob/master/docs/component-authoring-next-iteration.md)
retain their dated findings. This page records the current release decision.

To help with the authoring gate, share a small synthetic document and the edit
that was difficult in the [component RFC](https://github.com/fullbleed-engine/fullbleed-official/discussions/86).
Include the installed package version and whether the task required raw HTML
or inspecting internal selectors.

## What you can rely on now

- Existing `fullbleed.ui` imports remain supported. They are not deprecated by the alpha.
- `class_name` adds a literal class; a matching stylesheet supplies its appearance.
  See the [stable styling examples](python-components.md#class-names-and-styles)
  or the [alpha styling walkthrough](component-preview-12.md#write-a-component-with-its-own-styles).
- The preview exports styled and unstyled HTML. Bootstrap components are static
  in both HTML and PDF; no Bootstrap JavaScript is included.
- Token names are explicit, document-wide dependencies. For current reusable
  kits, use concrete defaults or supply the complete documented theme with
  distinct prefixes where meanings differ.
- Native PDF pagination and continuous browser HTML are different output
  contexts. The [preview's verification scope](component-preview-12.md#verification-and-scope)
  records the tested cases and limits.

JavaScript and .NET packages have their own versions and API coverage. Their
component APIs do not inherit the Python alpha's stability label or imply
cross-language feature parity.
