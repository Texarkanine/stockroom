---
task_id: release-quality-docs
date: 2026-07-12
complexity_level: 2
---

# Reflection: release-quality-docs (rework 6 — troubleshooting deep-links)

## Summary

Rewrote the troubleshooting catalog as heading-per-symptom sections ordered like the user-guide nav; converted torch failure remedies to headings; added thin Stuck? back-links from guide pages.

## Insights

### Technical
- Material turns `/` in headings into `--` in fragment ids (`#cursor-hooks--auto-dashboard-never-fire`) — verify generated anchors under strict build.

### Process
- Nothing notable

### Million-Dollar Question

Nothing notable — dedicated heading catalog + torch sibling remains the right shape.
