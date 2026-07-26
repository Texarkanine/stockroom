
# Documentation Site

Human docs live under [`docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs).

The documentation site is built with [properdocs](https://properdocs.org/) (a fork of [mkdocs](https://www.mkdocs.org/)) and Material for MkDocs.

1. Configuration: [`./properdocs.yaml`](https://github.com/Texarkanine/stockroom/blob/main/properdocs.yaml)
2. Content: [`./docs/`](https://github.com/Texarkanine/stockroom/tree/main/docs)
3. Dependencies: [`./pyproject.toml`](https://github.com/Texarkanine/stockroom/blob/main/pyproject.toml)

## Development Loop

1. `make docs` to start the local preview server
	* If you are doing heavy refactoring and causing many broken links, it may be helpful to run in non-strict mode: `uv run properdocs serve --no-strict`. CI will be strict, though.
2. Edit the markdown files in `docs/`

### Changing Dependencies

The root `pyproject.toml` uses the `docs` dependency group to specify the dependencies for the documentation site.

There's nothing special here; just normal [uv](https://docs.astral.sh/uv/) usage. Once you modify the root `pyproject.toml`'s dependency spec, just run `uv sync --group docs && uv lock`.

## Relevant Make Targets

| Target | Role |
| --- | --- |
| `docs` | Local preview (`properdocs serve`) |
| `docs-build` | Strict build — matches docs CI |

Config: [`properdocs.yaml`](https://github.com/Texarkanine/stockroom/blob/main/properdocs.yaml). Contributing nav order is controlled by [`docs/contributing/.pages`](https://github.com/Texarkanine/stockroom/blob/main/docs/contributing/.pages).

## Publishing

CI builds with `properdocs build --strict` on every PR (`.github/workflows/docs.yaml`). Deploy runs on a published GitHub Release or a manual `workflow_dispatch`.
