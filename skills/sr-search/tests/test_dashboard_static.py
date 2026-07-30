"""Packaging and accessibility contracts for the offline dashboard document."""

from html.parser import HTMLParser
from pathlib import Path


STATIC_ROOT = Path(__file__).parents[1] / "src" / "stockroom" / "dashboard" / "static"


class _DocumentParser(HTMLParser):
    """Collect tags and attributes without browser dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.elements.append((tag, dict(attrs)))


def _document() -> tuple[str, _DocumentParser]:
    source = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    parser = _DocumentParser()
    parser.feed(source)
    return source, parser


def _by_id(parser: _DocumentParser) -> dict[str, tuple[str, dict[str, str | None]]]:
    return {
        attrs["id"]: (tag, attrs) for tag, attrs in parser.elements if attrs.get("id")
    }


def _radios(parser: _DocumentParser, name: str) -> list[dict[str, str | None]]:
    return [
        attrs
        for tag, attrs in parser.elements
        if tag == "input" and attrs.get("type") == "radio" and attrs.get("name") == name
    ]


def test_dashboard_resources_are_local_and_load_before_adapter() -> None:
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

    scripts = [
        attrs for tag, attrs in parser.elements if tag == "script" and attrs.get("src")
    ]
    assert [script["src"] for script in scripts] == [
        "chart-4.5.1.umd.min.js",
        "markdown-it-14.1.0.min.js",
        "dashboard.mjs",
    ]
    assert scripts[2].get("type") == "module"
    for name in scripts[0]["src"], scripts[1]["src"], scripts[2]["src"]:
        assert name is not None
        assert (STATIC_ROOT / name).is_file()


def test_dashboard_shell_exposes_accessible_status_and_charts() -> None:
    """Status/error live regions and chart canvases carry accessibility roles."""
    _source, parser = _document()
    by_id = _by_id(parser)
    assert by_id["harness-selector"][0] == "details"
    assert by_id["mode-selector"][0] == "fieldset"
    assert by_id["status"][1].get("aria-live") == "polite"
    assert by_id["error"][1].get("role") == "alert"

    canvases = [attrs for tag, attrs in parser.elements if tag == "canvas"]
    assert canvases
    assert all(canvas.get("role") == "img" for canvas in canvases)
    assert all(canvas.get("aria-label") for canvas in canvases)

    info_buttons = [
        attrs
        for tag, attrs in parser.elements
        if tag == "button" and "panel-info" in (attrs.get("class") or "").split()
    ]
    assert info_buttons
    assert all(btn.get("type") == "button" for btn in info_buttons)
    assert all(btn.get("aria-expanded") == "false" for btn in info_buttons)
    assert all(btn.get("aria-controls") for btn in info_buttons)
    assert all(btn.get("aria-label") for btn in info_buttons)


def test_dashboard_segmented_controls_expose_stable_values() -> None:
    """Date-range, Aggregate/Compare, and per-page radios keep their value contracts."""
    _source, parser = _document()
    by_id = _by_id(parser)

    assert by_id["date-range-selector"][0] == "fieldset"
    assert by_id["mode-selector"][0] == "fieldset"
    assert by_id["per-page-selector"][0] == "fieldset"
    assert "segmented" in (by_id["date-range-selector"][1].get("class") or "").split()
    assert "segmented" in (by_id["mode-selector"][1].get("class") or "").split()
    assert "segmented" in (by_id["per-page-selector"][1].get("class") or "").split()

    date_radios = _radios(parser, "date-range")
    assert [radio.get("value") for radio in date_radios] == [
        "default",
        "7d",
        "30d",
        "90d",
        "1y",
        "all",
    ]
    assert sum(1 for radio in date_radios if "checked" in radio) == 1
    assert "checked" in next(
        radio for radio in date_radios if radio.get("value") == "default"
    )

    mode_radios = _radios(parser, "mode")
    assert [radio.get("value") for radio in mode_radios] == ["aggregate", "compare"]
    assert sum(1 for radio in mode_radios if "checked" in radio) == 1

    per_page = _radios(parser, "per-page")
    assert [radio.get("value") for radio in per_page] == ["25", "50", "100", "all"]
    assert "checked" in next(radio for radio in per_page if radio.get("value") == "50")


def test_markdown_it_disables_html_and_linkify() -> None:
    """Session markdown rendering must not enable HTML or autolink."""
    adapter = (STATIC_ROOT / "dashboard.mjs").read_text(encoding="utf-8")
    assert "html: false" in adapter
    assert "linkify: false" in adapter


def test_token_breakdown_uses_fixed_positioning() -> None:
    """
    Token breakdown must use fixed positioning (not absolute+centered) so it
    cannot expand .table-scroll / .sessions-panel into a scrollbar (#91).
    """
    source = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    start = source.index(".token-breakdown {")
    end = source.index("}", start)
    block = source[start:end]
    assert "position: fixed" in block
    assert "translateY(-50%)" not in block
