"""In-memory diagnostic HTML for dashboard static/document misses.

Rendered from string constants loaded with the dashboard process so a deleted
plugin tree cannot remove the recovery page. MVP: one generic page — no
shim-vs-replace classifier.
"""

_TROUBLESHOOTING = (
    "https://texarkanine.github.io/stockroom/user-guide/troubleshooting/"
)

_DIAGNOSTIC_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>stockroom dashboard — recovery</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: ui-sans-serif, system-ui, sans-serif;
    line-height: 1.5;
    max-width: 40rem;
    margin: 2rem auto;
    padding: 0 1.25rem;
  }}
  h1 {{ font-size: 1.35rem; font-weight: 650; margin-bottom: 0.5rem; }}
  ol {{ padding-left: 1.25rem; }}
  li {{ margin: 0.65rem 0; }}
  code {{ font-size: 0.92em; }}
  a {{ color: inherit; }}
  .hint {{ opacity: 0.85; margin-top: 1.5rem; font-size: 0.95rem; }}
</style>
</head>
<body>
  <h1>stockroom dashboard could not load this page</h1>
  <p>
    This listener is up, but it could not serve the UI (missing assets, stale
    process after a plugin update, or a path that does not exist). Try the
    remedies below <strong>in order</strong> — start with the shim, not
    <code>--replace</code>.
  </p>
  <ol>
    <li>
      <strong>Heal the on-path shim / open a new session.</strong>
      In Cursor or Claude Code, start a new chat so session-start can run
      <code>shim rectify</code> (full ensure + rebake). If you already have
      <code>stockroom</code> on <code>PATH</code>, you can also run:
      <br><code>stockroom shim rectify --owner cursor</code>
      (use <code>--owner claude</code> for Claude Code).
    </li>
    <li>
      <strong>Restore the engine environment.</strong>
      Path-only heal skips env sync. If imports or Torch are broken, run
      <code>stockroom shim ensure-env</code>, or re-run the
      <code>sr-initialize</code> skill.
    </li>
    <li>
      <strong>Replace a stale dashboard process.</strong>
      Only after the shim points at a live engine:
      <br><code>stockroom dashboard --replace</code>
    </li>
  </ol>
  <p class="hint">
    Manual:
    <a href="{_TROUBLESHOOTING}">{_TROUBLESHOOTING}</a>
    ·
    <a href="{_TROUBLESHOOTING}#dashboard">Dashboard</a>
    ·
    <a href="{_TROUBLESHOOTING}#stockroom-command-not-found">command not found / shim</a>
    ·
    <a href="{_TROUBLESHOOTING}#engine-env-cannot-import-locked-deps">engine env</a>
  </p>
</body>
</html>
"""


def render_diagnostic_html() -> str:
    """Return a self-contained HTML diagnostic page (ordered remedies + docs links)."""
    return _DIAGNOSTIC_HTML
