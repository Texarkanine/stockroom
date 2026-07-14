# Licensing

Stockroom uses [REUSE](https://reuse.software/) for licensing, allowing multiple licenses to be assigned & attributed throughout the codebase.

## Licensing Intent

| Target | What | License |
| --- | --- | --- |
| Default | Code, docs, memory-bank, and everything else | [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.en.html) |
| Prompt/Skill Text | `skills/**/SKILL.md` and `skills/**/references/**` only | [Public Prompt License (PPL-S)](https://shipfail.github.io/public-prompt-license/) |
| Vendored Chart.js / markdown-it | Exact upstream dashboard artifacts | MIT (reiteratd from upstream) |
| `.cursor/**` | Vendored agent tooling | None Specified (check upstream) |

## Checks

Is every file licensed?

```bash
make reuse
```

What license does a file fall under?

```bash
reuse spdx | grep -A 5 <path>
```

e.g. 

```
$ reuse spdx | grep -A 5 skills/sr-search/src/stockroom/dashboard/static/chart-4.5.1.umd.min.js
FileName: ./skills/sr-search/src/stockroom/dashboard/static/chart-4.5.1.umd.min.js
SPDXID: SPDXRef-67d5565acf332d4d6accfe56e67873b1
FileChecksum: SHA1: cb555814104cfb8bf88e4d1b21033b495c3c5a77
LicenseConcluded: NOASSERTION
LicenseInfoInFile: MIT
FileCopyrightText: <text>SPDX-FileCopyrightText: 2014-2025 Chart.js Contributors</text>
```

Prefer path aggregates in `REUSE.toml` over per-file SPDX headers when adding many new files.
