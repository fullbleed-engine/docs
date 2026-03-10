# Accessibility Coverage

Fullbleed targets two accessibility standards:

- **WCAG 2.0 Level AA** — Web Content Accessibility Guidelines
- **Section 508 (E205)** — U.S. federal procurement standard for electronic documents

## WCAG 2.0 AA Coverage

### Perceivable (Principle 1)

| Guideline | Criterion | Coverage | Notes |
|-----------|-----------|----------|-------|
| 1.1 Text Alternatives | 1.1.1 Non-text Content | ✅ | `alt` attributes on `<img>`, decorative image handling |
| 1.2 Time-based Media | 1.2.1–1.2.5 | N/A | Not applicable to PDF documents |
| 1.3 Adaptable | 1.3.1 Info and Relationships | ✅ | Semantic HTML → PDF tag structure |
| 1.3 Adaptable | 1.3.2 Meaningful Sequence | ✅ | Reading order trace + cross-check |
| 1.3 Adaptable | 1.3.3 Sensory Characteristics | ✅ | Verified in a11y report |
| 1.4 Distinguishable | 1.4.1 Use of Color | ⚠️ Manual | Requires visual review |
| 1.4 Distinguishable | 1.4.3 Contrast (Minimum) | ⚠️ Manual | Requires visual review |
| 1.4 Distinguishable | 1.4.4 Resize Text | ✅ | Tagged PDF supports reflow |
| 1.4 Distinguishable | 1.4.5 Images of Text | ✅ | Engine uses real text, not images |

### Operable (Principle 2)

| Guideline | Criterion | Coverage | Notes |
|-----------|-----------|----------|-------|
| 2.1 Keyboard Accessible | 2.1.1 Keyboard | ✅ | PDF reader handles navigation via tags |
| 2.4 Navigable | 2.4.1 Bypass Blocks | ✅ | Heading structure provides navigation |
| 2.4 Navigable | 2.4.2 Page Titled | ✅ | `document_title` parameter |
| 2.4 Navigable | 2.4.3 Focus Order | ✅ | Reading order matches visual order |
| 2.4 Navigable | 2.4.6 Headings and Labels | ✅ | Preserved from HTML heading elements |

### Understandable (Principle 3)

| Guideline | Criterion | Coverage | Notes |
|-----------|-----------|----------|-------|
| 3.1 Readable | 3.1.1 Language of Page | ✅ | `document_lang` parameter |
| 3.1 Readable | 3.1.2 Language of Parts | ✅ | `lang` attributes on HTML elements |

### Robust (Principle 4)

| Guideline | Criterion | Coverage | Notes |
|-----------|-----------|----------|-------|
| 4.1 Compatible | 4.1.1 Parsing | ✅ | Valid PDF structure |
| 4.1 Compatible | 4.1.2 Name, Role, Value | ✅ | PDF tag roles from semantic HTML |

## Section 508 (E205) Coverage

Section 508 E205 aligns closely with WCAG 2.0 AA. Fullbleed covers all applicable criteria:

| Requirement | Coverage | Implementation |
|-------------|----------|----------------|
| Tagged PDF structure | ✅ | Automatic from semantic HTML |
| Reading order | ✅ | Cross-checked (render-time vs. extraction) |
| Document title | ✅ | `document_title` parameter |
| Document language | ✅ | `document_lang` parameter |
| Table headers | ✅ | `<th scope="col|row">` → PDF table header tags |
| Image alt text | ✅ | `<img alt="">` → PDF alt text |
| Heading hierarchy | ✅ | `<h1>`–`<h6>` → PDF heading tags |
| List structure | ✅ | `<ul>/<ol>/<li>` → PDF list tags |
| Link text | ✅ | `<a>` → PDF link annotations |
| Color not sole indicator | ⚠️ Manual | Requires visual review |
| Sufficient contrast | ⚠️ Manual | Requires visual review |

## PDF/UA (ISO 14289-1) Alignment

Fullbleed's tagged output aligns with PDF/UA requirements. The `pdfua_seed_verify` check validates 14 structural requirements:

1. Document catalog has MarkInfo
2. MarkInfo is marked
3. Structure tree root exists
4. All content is tagged
5. Tag structure is valid
6. Document has title
7. Title is displayed
8. Language is set
9. Figures have alt text
10. Tables have headers
11. Lists are properly structured
12. Headings are hierarchical
13. Annotations are tagged
14. Fonts are embedded

## What Requires Manual Review

Three aspects of accessibility cannot be verified automatically:

1. **Color contrast** — The engine renders what you specify; it can't judge if your color choices meet WCAG contrast ratios. Use a contrast checker during design.

2. **Color as sole indicator** — If your document uses color alone to convey meaning (red = bad, green = good), that's a content decision the engine can't override.

3. **Reading order correctness** — Fullbleed cross-checks render-time vs. extraction order, but whether the *visual* order matches what a sighted user would expect requires human judgment.

The `a11y_report` flags these as "manual-needed" so you know exactly what to review.

## ADA Title II Deadline

**April 24, 2026**: State and local government web content must be accessible under the ADA Title II final rule. This includes PDFs published on government websites.

Fullbleed's evidence bundles provide the documentation governments need to demonstrate compliance — not just tagged PDFs, but quantified proof with PMR scores, reading order verification, and structural tag checks.

## Next Steps

- [Accessibility Engine →](engine.md) — How to generate accessible PDFs
- [Evidence Bundles →](evidence-bundles.md) — What's in the compliance evidence
- [AI Agent Integration →](../guides/ai-agents.md) — Automated accessible document authoring
