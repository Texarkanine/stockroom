"""Repo-root GitHub issue forms + PR template contract.

Asserts the committed ``.github/`` contributor templates stay load-bearing
for triage (doctor-first bug form, blank issues, Area routing) and release
(conventional-commit PR title), without depending on the GitHub UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ISSUE_TEMPLATE_DIR = Path(".github/ISSUE_TEMPLATE")
BUG_FORM = ISSUE_TEMPLATE_DIR / "bug_report.yml"
FEATURE_FORM = ISSUE_TEMPLATE_DIR / "feature_request.yml"
CONFIG_YML = ISSUE_TEMPLATE_DIR / "config.yml"
PR_TEMPLATE = Path(".github/pull_request_template.md")

AREA_OPTIONS = {
    "Install / setup",
    "Hooks / harness",
    "Shim / PATH",
    "Ingest / schedule",
    "Search (SQL)",
    "Semantic / torch",
    "Dashboard",
    "Docs",
    "Other",
}

TROUBLESHOOTING_URL = (
    "https://texarkanine.github.io/stockroom/user-guide/troubleshooting/"
)


def _load_yaml(repo_root: Path, relative: Path) -> Any:
    path = repo_root / relative
    assert path.is_file(), f"missing template file: {relative}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _body_ids(form: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in form.get("body") or []:
        item_id = item.get("id")
        if item_id:
            ids.append(item_id)
    return ids


def _field_by_id(form: dict[str, Any], field_id: str) -> dict[str, Any]:
    for item in form.get("body") or []:
        if item.get("id") == field_id:
            return item
    raise AssertionError(f"form body missing field id={field_id!r}")


def _required_dropdown_options(form: dict[str, Any], field_id: str) -> set[str]:
    field = _field_by_id(form, field_id)
    assert field.get("type") == "dropdown"
    assert (field.get("validations") or {}).get("required") is True
    options = field.get("attributes", {}).get("options") or []
    return set(options)


def test_config_allows_blank_issues_and_links_troubleshooting(repo_root: Path) -> None:
    """config.yml keeps blank issues open and steers RTM to troubleshooting."""
    config = _load_yaml(repo_root, CONFIG_YML)
    assert config.get("blank_issues_enabled") is True
    links = config.get("contact_links") or []
    assert links, "expected at least one contact_links entry"
    urls = {link.get("url") for link in links}
    assert TROUBLESHOOTING_URL in urls


def test_bug_and_feature_forms_parse_with_names(repo_root: Path) -> None:
    """Both issue forms exist, parse as YAML, and declare a name + body."""
    bug = _load_yaml(repo_root, BUG_FORM)
    feature = _load_yaml(repo_root, FEATURE_FORM)
    assert bug.get("name")
    assert feature.get("name")
    assert isinstance(bug.get("body"), list) and bug["body"]
    assert isinstance(feature.get("body"), list) and feature["body"]


def test_bug_form_requires_doctor_probe_before_narrative(repo_root: Path) -> None:
    """Bug form's first required textarea is doctor probe, before expected/actual."""
    bug = _load_yaml(repo_root, BUG_FORM)
    body = bug["body"]
    first_required_textarea = None
    narrative_ids = {"expected", "actual"}
    for item in body:
        if item.get("type") != "textarea":
            continue
        if not (item.get("validations") or {}).get("required"):
            continue
        first_required_textarea = item
        break
    assert first_required_textarea is not None
    doctor = first_required_textarea
    label = (doctor.get("attributes") or {}).get("label", "")
    description = (doctor.get("attributes") or {}).get("description", "")
    blob = f"{label}\n{description}".lower()
    assert "stockroom doctor" in blob
    assert "probe" in blob
    assert doctor.get("id") == "doctor"

    ids = _body_ids(bug)
    assert ids.index("doctor") < ids.index("expected")
    assert ids.index("doctor") < ids.index("actual")
    for nid in narrative_ids:
        field = _field_by_id(bug, nid)
        assert (field.get("validations") or {}).get("required") is True


def test_both_forms_require_area_dropdown(repo_root: Path) -> None:
    """Bug and feature forms route via the same required Area options."""
    bug = _load_yaml(repo_root, BUG_FORM)
    feature = _load_yaml(repo_root, FEATURE_FORM)
    assert _required_dropdown_options(bug, "area") == AREA_OPTIONS
    assert _required_dropdown_options(feature, "area") == AREA_OPTIONS


def test_bug_form_requires_harness_dropdown(repo_root: Path) -> None:
    """Bug form asks which harness (Cursor / Claude / CLI-only)."""
    bug = _load_yaml(repo_root, BUG_FORM)
    options = _required_dropdown_options(bug, "harness")
    assert "Cursor" in options
    assert "Claude Code" in options
    assert any("CLI" in opt for opt in options)


def test_bug_form_has_presubmit_checkboxes(repo_root: Path) -> None:
    """Bug form surfaces troubleshooting / torch / Cursor-plugins hints."""
    bug = _load_yaml(repo_root, BUG_FORM)
    checks = _field_by_id(bug, "presubmit")
    assert checks.get("type") == "checkboxes"
    labels = "\n".join(
        opt.get("label", "")
        for opt in (checks.get("attributes") or {}).get("options") or []
    ).lower()
    assert "troubleshooting" in labels
    assert "torch" in labels or "sr-initialize" in labels
    assert "third-party" in labels or "plugins" in labels


def test_feature_form_does_not_require_doctor(repo_root: Path) -> None:
    """Feature requests must not tax reporters with doctor output."""
    feature = _load_yaml(repo_root, FEATURE_FORM)
    body_text = yaml.dump(feature).lower()
    assert "stockroom doctor" not in body_text
    assert "doctor" not in _body_ids(feature)


def test_pr_template_pins_conventional_commit_and_ci(repo_root: Path) -> None:
    """PR template exists and pins release-please title types + make ci.

    release-please only cuts a release for ``feat`` / ``fix``. Docs publish
    on release, so ``docs`` is not an allowed type. ``chore`` is the
    no-release escape hatch.
    """
    path = repo_root / PR_TEMPLATE
    assert path.is_file(), f"missing {PR_TEMPLATE}"
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "conventional" in lowered
    assert "changelog" in lowered
    assert "make ci" in lowered
    assert "`feat`" in text and "`fix`" in text and "`chore`" in text
    assert "`docs`" not in text
    assert "release" in lowered
