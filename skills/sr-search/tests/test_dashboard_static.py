"""Static contracts for the fully offline dashboard document and assets."""

from html.parser import HTMLParser
from pathlib import Path


STATIC_ROOT = Path(__file__).parents[1] / "src" / "stockroom" / "dashboard" / "static"


class _DocumentParser(HTMLParser):
    """Collect tags, attributes, and visible text without browser dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())


def _document() -> tuple[str, _DocumentParser]:
    source = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    parser = _DocumentParser()
    parser.feed(source)
    return source, parser


def test_dashboard_document_has_semantic_controls_panels_and_fallbacks() -> None:
    """The packaged page exposes the complete accessible single-pane shell."""
    source, parser = _document()
    tags = [tag for tag, _attrs in parser.elements]
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    assert "<!doctype html>" in source.lower()
    assert "stockroom dashboard" in " ".join(parser.text).lower()
    assert "main" in tags
    assert by_id["harness-selector"][0] == "details"
    assert by_id["mode-selector"][0] == "fieldset"
    assert by_id["status"][1].get("aria-live") == "polite"
    assert by_id["error"][1].get("role") == "alert"
    for element_id in [
        "kpi-grid",
        "daily-panel",
        "projects-panel",
        "tools-panel",
        "write-read-panel",
        "efficiency-panel",
        "models-panel",
        "first-prompt-panel",
        "recent-sessions",
        "wrapped-panel",
    ]:
        assert element_id in by_id
    assert "table" in tags
    assert tags.count("th") >= 6
    canvases = [attrs for tag, attrs in parser.elements if tag == "canvas"]
    assert len(canvases) == 7
    assert all(canvas.get("role") == "img" for canvas in canvases)
    assert all(canvas.get("aria-label") for canvas in canvases)


def test_dashboard_resources_are_local_and_loaded_in_dependency_order() -> None:
    """Every resource is local; Chart.js and markdown-it load before the module."""
    source, parser = _document()
    references = [
        attrs[name]
        for _tag, attrs in parser.elements
        for name in ("src", "href")
        if attrs.get(name)
    ]
    assert references
    assert all(
        not reference.startswith(("http://", "https://", "//"))
        for reference in references
    )
    lowered = source.lower()
    assert "http://" not in lowered
    assert "https://" not in lowered
    chart_position = source.index('src="chart-4.5.1.umd.min.js"')
    markdown_position = source.index('src="markdown-it-14.1.0.min.js"')
    adapter_position = source.index('src="dashboard.mjs"')
    assert chart_position < adapter_position
    assert markdown_position < adapter_position
    scripts = [
        attrs for tag, attrs in parser.elements if tag == "script" and attrs.get("src")
    ]
    assert [script["src"] for script in scripts] == [
        "chart-4.5.1.umd.min.js",
        "markdown-it-14.1.0.min.js",
        "dashboard.mjs",
    ]
    assert scripts[2].get("type") == "module"
    assert (STATIC_ROOT / "markdown-it-14.1.0.min.js").is_file()


def test_dashboard_adapter_imports_authored_modules() -> None:
    """The effects adapter imports core, data, and session helpers."""
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert 'from "./dashboard-core.mjs"' in adapter
    assert 'from "./dashboard-data.mjs"' in adapter
    assert 'from "./dashboard-session.mjs"' in adapter


def test_session_pane_exposes_navigation_export_and_turn_landmarks() -> None:
    """Session inspection pane has back, copy-link, export, and turns regions."""
    source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    assert "metrics-pane" in by_id
    assert "session-pane" in by_id
    assert (
        by_id["session-pane"][1].get("hidden") is not None
        or "hidden" in by_id["session-pane"][1]
    )
    assert by_id["session-back"][0] == "button"
    assert by_id["session-copy-link"][0] == "button"
    assert by_id["session-export-md"][0] == "button"
    assert by_id["session-export-json"][0] == "button"
    assert "session-meta" in by_id
    assert "session-turns" in by_id
    assert "session-error" in by_id
    assert ".session-row" in source
    assert "cursor: pointer" in source
    assert "markdownit({ html: false" not in source  # init lives in JS, not HTML
    assert "html: false" in (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "linkify: false" in (STATIC_ROOT / "dashboard.mjs").read_text(
        encoding="utf-8"
    )


def test_dashboard_top_controls_expose_date_range_and_segmented_mode() -> None:
    """Date-range presets and Aggregate/Compare read as exclusive segmented controls."""
    _source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    assert by_id["date-range-selector"][0] == "fieldset"
    assert by_id["mode-selector"][0] == "fieldset"
    assert "segmented" in (by_id["date-range-selector"][1].get("class") or "").split()
    assert "segmented" in (by_id["mode-selector"][1].get("class") or "").split()

    date_radios = [
        attrs
        for tag, attrs in parser.elements
        if tag == "input"
        and attrs.get("type") == "radio"
        and attrs.get("name") == "date-range"
    ]
    assert [radio.get("value") for radio in date_radios] == [
        "default",
        "7d",
        "30d",
        "90d",
        "1y",
    ]
    assert sum(1 for radio in date_radios if "checked" in radio) == 1
    assert "checked" in next(
        radio for radio in date_radios if radio.get("value") == "default"
    )

    mode_radios = [
        attrs
        for tag, attrs in parser.elements
        if tag == "input"
        and attrs.get("type") == "radio"
        and attrs.get("name") == "mode"
    ]
    assert [radio.get("value") for radio in mode_radios] == ["aggregate", "compare"]
    assert sum(1 for radio in mode_radios if "checked" in radio) == 1


def test_write_read_chart_aria_describes_ratio_not_absolute_volumes() -> None:
    """Write/Read canvas fallback copy matches ratio semantics."""
    _source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    _tag, attrs = by_id["write-read-chart"]
    label = (attrs.get("aria-label") or "").lower()
    assert "ratio" in label or "share" in label
    assert "tool calls chart" not in label


def test_info_controls_only_on_efficiency_and_first_prompt_panels() -> None:
    """Help chrome is limited to Session Efficiency and First-Prompt Quality."""
    source, parser = _document()
    info_buttons = [
        attrs
        for tag, attrs in parser.elements
        if tag == "button" and "panel-info" in (attrs.get("class") or "").split()
    ]
    assert len(info_buttons) == 2
    assert all(btn.get("type") == "button" for btn in info_buttons)
    assert all(btn.get("aria-expanded") == "false" for btn in info_buttons)
    assert all(btn.get("aria-controls") for btn in info_buttons)
    assert all(btn.get("aria-label") for btn in info_buttons)

    efficiency_start = source.index('id="efficiency-panel"')
    efficiency_end = source.index('id="models-panel"')
    first_start = source.index('id="first-prompt-panel"')
    first_end = source.index('id="recent-sessions"')
    efficiency_chunk = source[efficiency_start:efficiency_end]
    first_chunk = source[first_start:first_end]
    assert 'class="panel-info"' in efficiency_chunk
    assert 'class="panel-info"' in first_chunk
    assert 'id="efficiency-help"' in efficiency_chunk
    assert 'id="first-prompt-help"' in first_chunk

    for panel_id in (
        "daily-panel",
        "projects-panel",
        "tools-panel",
        "write-read-panel",
        "models-panel",
    ):
        start = source.index(f'id="{panel_id}"')
        rest = source[start + 1 :]
        next_panel = rest.find('class="panel')
        chunk = source[start : start + 1 + (next_panel if next_panel != -1 else 800)]
        assert "panel-info" not in chunk
