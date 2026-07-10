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
    """Every resource is local and Chart.js loads before the module adapter."""
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
    adapter_position = source.index('src="dashboard.mjs"')
    assert chart_position < adapter_position
    scripts = [
        attrs for tag, attrs in parser.elements if tag == "script" and attrs.get("src")
    ]
    assert [script["src"] for script in scripts] == [
        "chart-4.5.1.umd.min.js",
        "dashboard.mjs",
    ]
    assert scripts[1].get("type") == "module"


def test_dashboard_adapter_imports_authored_modules() -> None:
    """The effects adapter imports core and data without extra HTML script tags."""
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert 'from "./dashboard-core.mjs"' in adapter
    assert 'from "./dashboard-data.mjs"' in adapter


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
