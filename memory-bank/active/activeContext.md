# Active Context

## Current Task: xdg-base-directory-layout
**Phase:** PLAN - IN-PROGRESS (routing to creative for open questions)

## What Was Done
- Intent clarified; Level 3 classified; ephemeral MB files created
- Component scan: path ownership concentrated in `warehouse.home_dir()`; `schedule._log_path` / install derive from that home; `doctor.probe_facts` reports no warehouse-home facts today; docs/memory bank / O1 still say `~/.stockroom/`
- Identified two open questions: directory layout shape (single tree vs XDG data/state split); legacy migration strategy (auto / explicit / defer)

## Next Step
- Creative phase: resolve Q1 (layout shape), then Q2 (migration strategy); return to plan to finalize implementation
