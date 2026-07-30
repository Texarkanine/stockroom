"""In-memory diagnostic HTML for dashboard static/document misses.

Rendered from string constants loaded with the dashboard process so a deleted
plugin tree cannot remove the recovery page. MVP: one generic page — no
shim-vs-replace classifier. Short rundown only; detail lives in the online manual.
"""

_TROUBLESHOOTING = (
    "https://texarkanine.github.io/stockroom/user-guide/troubleshooting/"
)
_RECOVERY_SECTION = f"{_TROUBLESHOOTING}#dashboard-ui-will-not-load"

_DIAGNOSTIC_HTML = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>stockroom dashboard — recovery</title>
<style>
  :root {{
    color-scheme: light dark;
    background: #f6f7fb;
    color: #171923;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      background: #10111a;
      color: #f5f6fa;
    }}
  }}
  body {{
    font-family: ui-sans-serif, system-ui, sans-serif;
    line-height: 1.5;
    max-width: 40rem;
    margin: 2rem auto;
    padding: 0 1.25rem;
  }}
</style>
</head>
<body>
  <h1>stockroom dashboard<h1>
  <h2>could not load this page</h2>
  <p>
    If you think this is a mistake and this page actually should have loaded,
  <p>
  <ol>
    <li>
      <strong>Heal from the harness.</strong>
      Open the harness you use (e.g. Cursor or Claude Code), start a <strong>new chat</strong>, and
      <strong>run <code>/sr-dashboard</code></strong>. Let it finish, then reload this page.
    </li>
    <li>
      <strong>If <code>stockroom</code> is still missing or refuses:</strong>
      in a chat, run <code>/sr-initialize</code> and ask it to
      restore the on-path shim and get the dashboard serving again.
    </li>
  </ol>
  <p class="hint">
    Full walkthrough:
    <a href="{_RECOVERY_SECTION}">Dashboard UI will not load</a>
    ·
    <a href="{_TROUBLESHOOTING}">Troubleshooting</a>
  </p>
</body>
</html>
"""


def render_diagnostic_html() -> str:
    """Return a self-contained HTML diagnostic page (ordered remedies + docs links)."""
    return _DIAGNOSTIC_HTML
