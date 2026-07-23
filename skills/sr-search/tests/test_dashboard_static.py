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
        "skills-nested-panel",
        "models-conversation-panel",
        "models-message-panel",
        "model-trends-panel",
        "efficiency-panel",
        "first-prompt-panel",
        "write-read-panel",
        "recent-sessions",
        "wrapped-panel",
    ]:
        assert element_id in by_id
    assert "models-panel" not in by_id
    assert "table" in tags
    assert tags.count("th") >= 6
    canvases = [attrs for tag, attrs in parser.elements if tag == "canvas"]
    assert len(canvases) == 10
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


def test_skill_chart_is_sunburst_only() -> None:
    """One skills panel (nested sunburst); stacked/tools-like mockups removed."""
    _source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    assert "skills-nested-panel" in by_id
    assert "skills-stacked-panel" not in by_id
    assert "skills-tools-like-panel" not in by_id
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "buildSkillsNestedPanel" in adapter
    assert "buildSkillsStackedPanel" not in adapter
    assert "buildSkillsToolsLikePanel" not in adapter


def test_lower_chart_panels_order_and_panel_wide_widths() -> None:
    """Operator grid: model bars, model trends, efficiency/first-prompt, write-read."""
    source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    models_conversation = source.index('id="models-conversation-panel"')
    models_message = source.index('id="models-message-panel"')
    model_trends = source.index('id="model-trends-panel"')
    efficiency = source.index('id="efficiency-panel"')
    first_prompt = source.index('id="first-prompt-panel"')
    write_read = source.index('id="write-read-panel"')
    assert (
        models_conversation
        < models_message
        < model_trends
        < efficiency
        < first_prompt
        < write_read
    )
    assert "panel-wide" in (by_id["model-trends-panel"][1].get("class") or "").split()
    assert "panel-wide" in (by_id["write-read-panel"][1].get("class") or "").split()
    assert (
        "panel-wide" not in (by_id["first-prompt-panel"][1].get("class") or "").split()
    )
    assert 'class="panel" id="first-prompt-panel"' in source
    assert "Top Models (by conversation)" in source
    assert "Top Models (by message)" in source
    assert "Model Usage over Time" in source


def test_session_pane_exposes_navigation_export_and_turn_landmarks() -> None:
    """Session inspection pane has copy-link, export, and turns — no custom back."""
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
    assert "session-back" not in by_id
    assert "session-back" not in source
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


def test_sessions_list_pane_and_metrics_sessions_chrome() -> None:
    """Sessions panel title, list pane landmarks, per-page radios, and FOUC."""
    source, parser = _document()
    by_id = {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }
    assert "Sessions" in parser.text
    assert "Recent Sessions" not in parser.text
    assert by_id["recent-sessions-title"][0] == "h2"
    assert "sessions-pane" in by_id
    assert (
        by_id["sessions-pane"][1].get("hidden") is not None
        or "hidden" in by_id["sessions-pane"][1]
    )
    assert by_id["per-page-selector"][0] == "fieldset"
    assert "segmented" in (by_id["per-page-selector"][1].get("class") or "").split()
    per_page = [
        attrs
        for tag, attrs in parser.elements
        if tag == "input"
        and attrs.get("type") == "radio"
        and attrs.get("name") == "per-page"
    ]
    assert [radio.get("value") for radio in per_page] == ["25", "50", "100", "all"]
    assert "checked" in next(radio for radio in per_page if radio.get("value") == "50")
    assert "sessions-pagination-top" in by_id
    assert "sessions-pagination-bottom" in by_id
    assert "sessions-page-numbers-top" in by_id
    assert "sessions-page-numbers-bottom" in by_id
    assert "sessions-list-rows" in by_id
    assert "page-heading" in by_id
    assert by_id["warehouse-home"][0] == "a"
    assert by_id["warehouse-home"][1].get("href") == "/"
    assert 'data-view = "sessions"' in source or 'dataset.view = "sessions"' in source
    assert 'html[data-view="sessions"] #metrics-pane' in source
    assert ".sessions-more-row" in source
    assert ".sessions-page-numbers" in source


def test_session_pane_toolbar_and_bubble_layout_contracts() -> None:
    """Session pane wires view toggles and turn/tool structure used by JS."""
    source = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    assert ".session-turn-user" in source
    assert ".session-turn-assistant" in source
    assert 'data-view = "session"' in source or 'dataset.view = "session"' in source
    assert 'html[data-view="session"] #metrics-pane' in source
    assert 'html[data-view="session"] #sessions-pane' in source
    assert ".session-tool" in source
    assert ".session-tool[open] summary" in source
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "session-turn-user" in adapter
    assert "session-turn-assistant" in adapter
    assert "applyViewChrome" in adapter
    assert "documentTitleForView" in adapter


def test_session_ui_uses_shared_token_display_module() -> None:
    """Session chrome mounts tokens through dashboard-tokens (one shared surface)."""
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "mountTokenDisplay" in adapter
    assert 'from "./dashboard-tokens.mjs"' in adapter
    assert (STATIC_ROOT / "dashboard-tokens.mjs").is_file()


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
    efficiency_end = source.index('id="first-prompt-panel"')
    first_start = source.index('id="first-prompt-panel"')
    first_end = source.index('id="recent-sessions"')
    efficiency_chunk = source[efficiency_start:efficiency_end]
    first_chunk = source[first_start:first_end]
    assert 'class="panel-info"' in efficiency_chunk
    assert 'class="panel-info"' in first_chunk
    assert 'id="efficiency-help"' in efficiency_chunk
    assert 'id="first-prompt-help"' in first_chunk
    assert ">Last 30 days<" in first_chunk
    assert "Average session length by prompt detail" not in first_chunk

    for panel_id in (
        "daily-panel",
        "projects-panel",
        "tools-panel",
        "skills-nested-panel",
        "models-conversation-panel",
        "models-message-panel",
        "model-trends-panel",
        "write-read-panel",
    ):
        start = source.index(f'id="{panel_id}"')
        rest = source[start + 1 :]
        next_panel = rest.find('class="panel')
        chunk = source[start : start + 1 + (next_panel if next_panel != -1 else 800)]
        assert "panel-info" not in chunk


def test_dashboard_adapter_wires_model_panel_builders() -> None:
    """Adapter imports dual-grain builders and references new chart element ids."""
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "assignModelColors" in adapter
    assert "buildModelsConversationPanel" in adapter
    assert "buildModelsMessagePanel" in adapter
    assert "buildModelTrendsPanel" in adapter
    assert "buildModelsPanel" not in adapter
    assert 'renderChart(\n    "models-conversation"' in adapter
    assert 'renderChart(\n    "models-message"' in adapter
    assert 'renderChart(\n    "model-trends"' in adapter
    assert "snapshot.models?.by_conversation" in adapter
    assert "snapshot.models?.by_message" in adapter
    assert "snapshot.model_trends" in adapter
    assert "by_message?.models" in adapter
    assert "omitZeroTooltip" in adapter
