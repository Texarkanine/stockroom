# Task: contributing-localdev-guide

* Task ID: contributing-localdev-guide
* Complexity: Level 3
* Type: enhancement (docs + optional tooling)

Bring Contributing to user-guide quality with a complete install → local checkout exclusive → verify → back path. Park Architecture/Advanced leftovers as rough notes only.

## Open Questions (planning)

- [ ] **Enter/exit automation & Contributing IA** — Should the localdev round-trip be prose recipes, Makefile targets, and/or scripts? How should Contributing pages be structured around that decision?
  - Ambiguous because: Makefile already has partial pieces (`torch`, `localdev`, `shim`) but no enter/exit orchestration or undo; warehouse history shows operators repeatedly assembling ad-hoc sequences (`--takeover`, rsync, reload) and asking for undo; scripts would reduce footguns but risk becoming a third install UX (forbidden for end users).
  - Constraints: end users stay on `sr-initialize`/marketplace; Contributing presentation-quality; Architecture/Advanced notes-only; finished Home/user-guide untouched except necessary cross-links.
