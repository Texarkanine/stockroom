# Decision: Markdown Library & HTML Safety

## Context

**What:** Which JS markdown library to vendor into `dashboard/static/`, in what load shape, and how to handle HTML/XSS when rendering message bodies.

**Why it matters:** Locks REUSE annotations, `index.html` load order, render API used by the session view, and whether we need a second sanitizer dependency. Wrong choice either pulls an extension ecosystem we explicitly rejected or leaves `innerHTML` unsafe against hostile content inside ingested transcripts.

**Constraints:**
- Fully offline — vendor verbatim; no CDN
- Basic markdown only — no Mermaid, footnotes, or plugin ecosystem
- No front-end package manager / bundler at runtime
- Prefer Chart.js precedent (pinned filename, UMD script tag, REUSE MIT override)
- Operator escape hatch for richer rendering is **export**, not in-dashboard extensions
- Transcript text is not fully trusted (agents may have fetched hostile HTML/markdown)

## Options Evaluated

- **A — marked (UMD)**: Fast, simple `marked.parse()`, mirrors Chart.js UMD load; does **not** sanitize HTML output by default ([marked docs](https://github.com/markedjs/marked/))
- **B — markdown-it (UMD), no plugins, `html: false`**: CommonMark-oriented; extensions are opt-in plugins we simply omit; `html: false` escapes raw HTML in source without a second library ([markdown-it](https://github.com/markdown-it/markdown-it))
- **C — snarkdown**: ~1KB minimal parser; incomplete for code fences / reliable CommonMark; no HTML sanitization ([snarkdown](https://github.com/developit/snarkdown))
- **D — marked + DOMPurify**: Strong sanitization; two vendored artifacts and two REUSE pins for a local dashboard

## Analysis

| Criterion | A marked | B markdown-it | C snarkdown | D marked+DOMPurify |
|-----------|----------|---------------|-------------|---------------------|
| Basic MD fidelity | High | High (CommonMark) | Too low | High |
| No-extensions fit | Good (limited plugins) | Best (plugins opt-in, unused) | N/A | Good |
| XSS without 2nd lib | Weak | Strong (`html: false`) | Weak | Strong (2 libs) |
| Chart.js-like vendoring | Excellent | Excellent | Excellent | Heavier |
| Operator "basic only" | OK | Best | Underpowered | Overbuilt |

Key insights:
- Extension temptation is a process risk with markdown-it, but we control it by vendoring one file and never loading plugins — stronger than fighting marked's GFM defaults later
- Hostile content in *stored transcripts* is a real XSS vector even on loopback; `html: false` buys safety without DOMPurify
- snarkdown fails the "code fences / lists / headings" bar implied by basic reconstruction

## Decision

**Selected**: Option B — vendored **markdown-it** UMD, configured with `html: false`, no plugins, linkify/typographer off (CommonMark-leaning)
**Rationale:** Single dependency that matches "basic markdown, no extensions," provides HTML escaping without a sanitizer package, and vendors like Chart.js
**Tradeoff:** Slightly more API ceremony than `marked.parse()`; accepted

## Implementation Notes

- Vendor a pinned minified UMD build as e.g. `markdown-it-<version>.min.js` under `dashboard/static/`
- Load via `<script>` **before** the dashboard ES module (same order pattern as Chart.js)
- Init once: `window.markdownit({ html: false, linkify: false, typographer: false })` — do not enable tables/footnotes plugins
- Render message bodies with `md.render(text)` into a dedicated content element; keep role/meta chrome outside markdown
- REUSE.toml: MIT override for the exact artifact path + licensing test mirror of Chart.js
- Technology validation in plan: download the pinned UMD, confirm `window.markdownit` + `render('# hi')` under Node or a tiny HTML smoke — no npm runtime
- Document in code comment: richer rendering → use export, do not add plugins
