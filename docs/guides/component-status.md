---
title: Python component release status and stabilization
description: Choose the stable Fullbleed Python component API or its opt-in 2.6 alpha. See what is verified and what remains before the new API becomes stable.
---

# Python component release status

Reviewed **20 October 2026**. Fullbleed's released Python component API is
available today. The newer API remains an opt-in alpha.

| Channel | Install | Authoring surface |
| --- | --- | --- |
| Stable **2.5.34** | `python -m pip install fullbleed` | HTML/CSS rendering and the existing `fullbleed.ui` components |
| Alpha **2.6.0a11** | `python -m pip install --pre "fullbleed==2.6.0a11"` | New authoring values under `fullbleed.ui.experimental` |

Start with the [Python quickstart](../getting-started/quickstart.md) for either
HTML/CSS or stable components. Both examples produce the same invoice.
The [stable component guide](python-components.md) explains function components,
children, `class_name`, inline styles and attached stylesheets.

The alpha adds component-owned styles, named customization parts, column-based
tables, static Bootstrap helpers, repeating page bands, and HTML export with or
without styles. Its [current preview guide](component-preview-11.md) includes
installation instructions and a complete source kit.

## Decision: retain the alpha

The alpha is **merged into `master` and published on PyPI**. It is not an
unmerged prototype. Merging it makes the implementation available for development;
it does not make the new API a stable compatibility promise. Ordinary
`pip install fullbleed` continues to select the stable channel.

The current release has substantial rendered-output evidence, including paired
HTML/CSS and component showcases, saved PDFs, styled/unstyled HTML, page-band
checks, typing checks and browser layout checks. The
[alpha 11 release](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a11)
records the exact package and fixture evidence. Passing those checks establishes
the tested behavior; it does not settle how the API should evolve for its callers.

Three stabilization gates remain:

| Gate | Current position | What closes it |
| --- | --- | --- |
| Public namespace and migration | `fullbleed.ui.Document` is a decorator; the experimental `Document` is a document value with explicit page, theme and renderer ownership. `to_legacy` bridges individual nodes. | Choose and document the supported stable import path, preserve existing imports, and qualify whole-document migration examples covering styles, geometry, metadata and renderer configuration. |
| Components from independent kits | Theme tokens are document-wide. Two kits using `token("accent")` share one value. Missing bindings raise `theme.missing`; explicit kit prefixes allow separate palettes. | Settle and qualify a documented kit-dependency convention with two independently authored kits: defaults, required values, conflicting names and local overrides must be clear without inspecting implementation details. A new scoping mechanism is not automatically required. |
| Authoring and customization feedback | Maintainer-authored fixtures cover the intended edits, but retained independent author feedback is still missing. | Have independent authors rebrand a document, reuse a component, add a table column, change page size and diagnose a layout failure. Record where internal selectors or undocumented knowledge are needed, then resolve those contract gaps. |

These are bounded API decisions, not a requirement to implement every CSS feature
before a stable release. The earlier
[implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/master/docs/component-authoring-design.md)
and [design follow-up](https://github.com/fullbleed-engine/fullbleed-official/blob/master/docs/component-authoring-next-iteration.md)
retain their dated findings. This page records the current release decision.

## What you can rely on now

- Existing `fullbleed.ui` imports remain supported. They are not deprecated by the alpha.
- `class_name` adds a literal class; a matching stylesheet supplies its appearance.
  See the [stable styling examples](python-components.md#class-names-and-styles)
  or the [alpha styling walkthrough](component-preview-11.md).
- The preview exports styled and unstyled HTML. Bootstrap components are static
  in both HTML and PDF; no Bootstrap JavaScript is included.
- Token names are explicit, document-wide dependencies. For current reusable
  kits, use concrete defaults or supply the complete documented theme with
  distinct prefixes where meanings differ.
- Native PDF pagination and continuous browser HTML are different output
  contexts. The [preview's verification scope](component-preview-11.md#verification-and-scope)
  records the tested cases and limits.

JavaScript and .NET packages have their own versions and API coverage. Their
component APIs do not inherit the Python alpha's stability label or imply
cross-language feature parity.
