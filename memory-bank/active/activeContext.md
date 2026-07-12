# Active Context

## Current Task: release-quality-docs
**Phase:** BUILD - COMPLETE

## What Was Done
- Quickstart self-contained (marketplace via txrk9-agent-plugins; third-party toggle + screenshot; `sr-initialize`)
- `install.md` → `installed-layout.md` (plugin payload + runtime home; no second ritual)
- Local/dev load moved to `docs/contributing/development.md#local-plugin-load`
- Link cascade: README, CONTRIBUTING, troubleshooting, using-skills, torch, advanced, sr-initialize, techContext, systemPatterns
- Gates: `make docs-build` PASS; `make reuse` PASS

## Files modified
- `/home/mobaxterm/git/stockroom/docs/user-guide/quickstart.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/installed-layout.md` (new)
- `/home/mobaxterm/git/stockroom/docs/user-guide/install.md` (deleted)
- `/home/mobaxterm/git/stockroom/docs/user-guide/.pages`
- `/home/mobaxterm/git/stockroom/docs/contributing/development.md`
- `/home/mobaxterm/git/stockroom/docs/contributing/torch.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/troubleshooting.md`
- `/home/mobaxterm/git/stockroom/docs/user-guide/using-skills.md`
- `/home/mobaxterm/git/stockroom/docs/advanced/index.md`
- `/home/mobaxterm/git/stockroom/README.md`
- `/home/mobaxterm/git/stockroom/CONTRIBUTING.md`
- `/home/mobaxterm/git/stockroom/skills/sr-initialize/SKILL.md`
- `/home/mobaxterm/git/stockroom/memory-bank/systemPatterns.md`
- `/home/mobaxterm/git/stockroom/memory-bank/techContext.md`

## Key decisions
- Optional Quickstart → Installed layout pointer (discovery only; ritual stays self-contained)
- Fixed WIP relative links under troubleshooting (`../contributing`, `../advanced`)

## Deviations
- Also fixed `contributor-guide` path refs in skill + persistent memory bank (needed for accuracy after rename; small scope expansion)

## Next Step
- QA review (autonomous for L2)
