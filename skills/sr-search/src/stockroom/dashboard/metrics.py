"""Mode-agnostic, per-harness metrics for the local dashboard.

The server returns raw harness-keyed series; aggregate/compare rendering and
signature colors belong to the client. Session activity means
``COALESCE(started_at, source_mtime)``: source-authored wall clock where the
harness has it, otherwise the durable transcript-mtime provenance captured by
ingest. Main-session metrics exclude subagents.

Tool classification is intentionally explicit and tunable. Write tools are
``WRITE_TOOLS``; read tools are ``READ_TOOLS``; Shell, task delegation, MCP, and
unknown future tools are neither until deliberately classified.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

from stockroom.truncate import truncate_cell

ACTIVITY_TIME_SQL = "COALESCE(s.started_at, s.source_mtime)"

WRITE_TOOLS = frozenset(
    {"Write", "StrReplace", "Edit", "ApplyPatch", "Delete", "EditNotebook"}
)
READ_TOOLS = frozenset(
    {
        "Read",
        "ReadFile",
        "Grep",
        "Glob",
        "ListDir",
        "ReadLints",
        "rg",
        "SemanticSearch",
    }
)

EFFICIENCY_BUCKETS = ("abandoned", "short", "medium", "long")
FIRST_PROMPT_BUCKETS = ("short", "medium", "detailed")


def parse_timestamp(
    value: str | datetime | None,
    name: str,
) -> datetime | None:
    """Parse one optional ISO-8601 bound without inventing its opposite bound."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid {name}: expected ISO-8601") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_window(
    since: str | datetime | None,
    until: str | datetime | None,
    *,
    default_days: int,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Parse an inclusive/exclusive ISO window, applying a default duration."""
    end = parse_timestamp(until, "until") or now or datetime.now()
    start = parse_timestamp(since, "since") or end - timedelta(days=default_days)
    if start >= end:
        raise ValueError("since must be earlier than until")
    return start, end


def _active_harnesses(
    con: duckdb.DuckDBPyConnection,
    selected: Sequence[str] | None,
) -> list[str]:
    if selected:
        return sorted(set(selected))
    return [
        row[0]
        for row in con.execute(
            "SELECT DISTINCT harness FROM sessions "
            "WHERE harness IS NOT NULL ORDER BY harness"
        ).fetchall()
    ]


def _session_rows(
    con: duckdb.DuckDBPyConnection,
    start: datetime,
    end: datetime,
) -> list[tuple[str, str, str | None, datetime, int]]:
    return con.execute(
        f"SELECT s.harness, s.session_id, s.project_id, {ACTIVITY_TIME_SQL}, "
        "count(m.message_id) "
        "FROM sessions s LEFT JOIN messages m "
        "ON m.harness = s.harness AND m.session_id = s.session_id "
        f"WHERE NOT s.is_subagent AND {ACTIVITY_TIME_SQL} IS NOT NULL "
        f"AND {ACTIVITY_TIME_SQL} >= ? AND {ACTIVITY_TIME_SQL} < ? "
        "GROUP BY s.harness, s.session_id, s.project_id, "
        "s.started_at, s.source_mtime",
        [start, end],
    ).fetchall()


def _is_selected(harness: str, active: set[str]) -> bool:
    return harness in active


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def overview(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return 30-day KPI counts and the equal-length preceding window.

    ``since`` is inclusive and ``until`` exclusive. Harness enumeration is
    all-time, so an installed but idle harness retains a zeroed card. Cursor
    sessions are dated by transcript mtime, an honest last-activity grain.
    """
    start, end = parse_window(since, until, default_days=30)
    width = end - start
    previous_start = start - width
    names = _active_harnesses(con, harnesses)
    active = set(names)

    def _empty() -> dict[str, int]:
        return {
            "sessions": 0,
            "messages": 0,
            "projects": 0,
            "prev_sessions": 0,
            "prev_messages": 0,
            "prev_projects": 0,
        }

    per_harness = {name: _empty() for name in names}
    current_projects = {name: set() for name in names}
    previous_projects = {name: set() for name in names}
    distinct_projects: set[str] = set()
    prev_distinct_projects: set[str] = set()

    for harness, _session_id, project_id, _activity, messages in _session_rows(
        con, start, end
    ):
        if not _is_selected(harness, active):
            continue
        values = per_harness[harness]
        values["sessions"] += 1
        values["messages"] += messages
        if project_id is not None:
            current_projects[harness].add(project_id)
            distinct_projects.add(project_id)

    for harness, _session_id, project_id, _activity, messages in _session_rows(
        con, previous_start, start
    ):
        if not _is_selected(harness, active):
            continue
        values = per_harness[harness]
        values["prev_sessions"] += 1
        values["prev_messages"] += messages
        if project_id is not None:
            previous_projects[harness].add(project_id)
            prev_distinct_projects.add(project_id)

    for name, values in per_harness.items():
        values["projects"] = len(current_projects[name])
        values["prev_projects"] = len(previous_projects[name])

    last_sync = con.execute("SELECT max(updated_at) FROM _sync_state").fetchone()[0]
    return {
        "last_sync": _iso(last_sync),
        "per_harness": per_harness,
        "distinct_projects": len(distinct_projects),
        "prev_distinct_projects": len(prev_distinct_projects),
    }


def _date_labels(start: datetime, end: datetime) -> list[str]:
    current = start.date()
    labels: list[str] = []
    while datetime.combine(current, datetime.min.time()) < end:
        labels.append(current.isoformat())
        current += timedelta(days=1)
    return labels


def _week_start(value: datetime) -> datetime:
    day = value.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def _week_labels(start: datetime, end: datetime) -> list[str]:
    current = _week_start(start)
    final = _week_start(end - timedelta(microseconds=1))
    labels: list[str] = []
    while current <= final:
        labels.append(current.date().isoformat())
        current += timedelta(days=7)
    return labels


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_labels(start: datetime, end: datetime) -> list[str]:
    current = _month_start(start)
    final = _month_start(end - timedelta(microseconds=1))
    labels: list[str] = []
    while current <= final:
        labels.append(current.date().isoformat())
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return labels


def _window_duration_days(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 86400.0


def _trend_granularity(start: datetime, end: datetime) -> str:
    """Choose shared axis buckets for a bounded range-picker window.

    ``<= 30d`` → day, ``<= 90d`` → week, else month.
    """
    days = _window_duration_days(start, end)
    if days <= 30:
        return "day"
    if days <= 90:
        return "week"
    return "month"


def _bucket_labels(start: datetime, end: datetime, granularity: str) -> list[str]:
    if granularity == "day":
        return _date_labels(start, end)
    if granularity == "week":
        return _week_labels(start, end)
    return _month_labels(start, end)


def _activity_bucket(activity: datetime, granularity: str) -> str:
    if granularity == "day":
        return activity.date().isoformat()
    if granularity == "week":
        return _week_start(activity).date().isoformat()
    return _month_start(activity).date().isoformat()


def trends(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return session and write/read time series for the dashboard.

    Unbounded defaults keep the historical dual windows (14 day session bars,
    12 calendar-week tool buckets). Bounded ``since``/``until`` windows share
    one adaptive granularity across both series so the range picker never
    leaves write/read on a coarser axis than session activity.
    """
    effective_end = until or datetime.now()
    if since is None:
        last_included = effective_end - timedelta(microseconds=1)
        daily_start = datetime.combine(
            last_included.date() - timedelta(days=13), datetime.min.time()
        )
        weekly_start = _week_start(last_included) - timedelta(weeks=11)
        daily_end = weekly_end = effective_end
        daily_granularity = "day"
        weekly_granularity = "week"
        daily_labels = _date_labels(daily_start, daily_end)
        weekly_labels = _week_labels(weekly_start, weekly_end)
    else:
        daily_start, daily_end = parse_window(
            since, effective_end, default_days=14, now=effective_end
        )
        weekly_start = daily_start
        weekly_end = daily_end
        daily_granularity = weekly_granularity = _trend_granularity(
            daily_start, daily_end
        )
        daily_labels = weekly_labels = _bucket_labels(
            daily_start, daily_end, daily_granularity
        )

    names = _active_harnesses(con, harnesses)
    active = set(names)

    day_index = {label: index for index, label in enumerate(daily_labels)}
    daily = {name: [0] * len(daily_labels) for name in names}
    for harness, _session_id, _project_id, activity, _messages in _session_rows(
        con, daily_start, daily_end
    ):
        if _is_selected(harness, active):
            bucket = _activity_bucket(activity, daily_granularity)
            daily[harness][day_index[bucket]] += 1

    week_index = {label: index for index, label in enumerate(weekly_labels)}
    writes = {name: [0] * len(weekly_labels) for name in names}
    reads = {name: [0] * len(weekly_labels) for name in names}
    tool_rows = con.execute(
        f"SELECT s.harness, {ACTIVITY_TIME_SQL}, t.tool_name "
        "FROM sessions s JOIN tool_calls t "
        "ON t.harness = s.harness AND t.session_id = s.session_id "
        f"WHERE NOT s.is_subagent AND {ACTIVITY_TIME_SQL} IS NOT NULL "
        f"AND {ACTIVITY_TIME_SQL} >= ? AND {ACTIVITY_TIME_SQL} < ?",
        [weekly_start, weekly_end],
    ).fetchall()
    for harness, activity, tool_name in tool_rows:
        if not _is_selected(harness, active):
            continue
        index = week_index[_activity_bucket(activity, weekly_granularity)]
        if tool_name in WRITE_TOOLS:
            writes[harness][index] += 1
        elif tool_name in READ_TOOLS:
            reads[harness][index] += 1

    return {
        "daily": {
            "granularity": daily_granularity,
            "labels": daily_labels,
            "sessions": daily,
        },
        "weekly": {
            "granularity": weekly_granularity,
            "labels": weekly_labels,
            "writes": writes,
            "reads": reads,
        },
    }


def project_display_name(cwd: str | None, project_id: str | None) -> str | None:
    """Return a friendly leaf name from ``cwd``, else ``project_id``.

    Used by sessions, wrapped, and projects label resolution. Empty or missing
    ``cwd`` falls back to ``project_id`` (which may itself be ``None``).
    """
    if cwd:
        return Path(cwd).name
    return project_id


def _project_label_from_cwds(project_id: str, cwds: set[str]) -> str:
    """Pick a display label when one unique basename exists among ``cwds``."""
    leaves = {project_display_name(cwd, project_id) for cwd in cwds if cwd}
    if len(leaves) == 1:
        return next(iter(leaves))
    return project_id


def _project_cwds(
    con: duckdb.DuckDBPyConnection,
    start: datetime,
    end: datetime,
    project_ids: Sequence[str],
) -> dict[str, set[str]]:
    """Collect non-NULL cwds per project_id in the activity window."""
    if not project_ids:
        return {}
    placeholders = ", ".join("?" for _ in project_ids)
    rows = con.execute(
        f"SELECT s.project_id, s.cwd FROM sessions s "
        f"WHERE NOT s.is_subagent AND s.cwd IS NOT NULL "
        f"AND s.project_id IN ({placeholders}) "
        f"AND {ACTIVITY_TIME_SQL} IS NOT NULL "
        f"AND {ACTIVITY_TIME_SQL} >= ? AND {ACTIVITY_TIME_SQL} < ?",
        [*project_ids, start, end],
    ).fetchall()
    by_project: dict[str, set[str]] = {project_id: set() for project_id in project_ids}
    for project_id, cwd in rows:
        if project_id in by_project and cwd:
            by_project[project_id].add(cwd)
    return by_project


def projects(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Return top projects; Cursor sessions use transcript-mtime last activity."""
    start, end = parse_window(since, until, default_days=30)
    names = _active_harnesses(con, harnesses)
    active = set(names)
    counts: dict[str, dict[str, int]] = {}
    for harness, _session_id, project_id, _activity, _messages in _session_rows(
        con, start, end
    ):
        if not _is_selected(harness, active) or project_id is None:
            continue
        per_harness = counts.setdefault(project_id, {})
        per_harness[harness] = per_harness.get(harness, 0) + 1

    ranked = sorted(
        counts,
        key=lambda project: (-sum(counts[project].values()), project),
    )[:limit]
    cwds_by_project = _project_cwds(con, start, end, ranked)
    labels = [
        _project_label_from_cwds(project_id, cwds_by_project.get(project_id, set()))
        for project_id in ranked
    ]
    return {
        "projects": ranked,
        "labels": labels,
        "sessions": {
            name: [counts[project].get(name, 0) for project in ranked] for name in names
        },
    }


def tools(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Return top tools; Cursor sessions use transcript-mtime last activity."""
    start, end = parse_window(since, until, default_days=30)
    names = _active_harnesses(con, harnesses)
    active = set(names)
    counts: dict[str, dict[str, int]] = {}
    rows = con.execute(
        f"SELECT s.harness, t.tool_name FROM sessions s JOIN tool_calls t "
        "ON t.harness = s.harness AND t.session_id = s.session_id "
        f"WHERE NOT s.is_subagent AND {ACTIVITY_TIME_SQL} IS NOT NULL "
        f"AND {ACTIVITY_TIME_SQL} >= ? AND {ACTIVITY_TIME_SQL} < ?",
        [start, end],
    ).fetchall()
    for harness, tool_name in rows:
        if not _is_selected(harness, active):
            continue
        per_harness = counts.setdefault(tool_name, {})
        per_harness[harness] = per_harness.get(harness, 0) + 1

    ranked = sorted(
        counts,
        key=lambda tool: (-sum(counts[tool].values()), tool),
    )[:limit]
    return {
        "tools": ranked,
        "calls": {
            name: [counts[tool].get(name, 0) for tool in ranked] for name in names
        },
    }


def models(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return session-grain model usage across both schema grains.

    A session uses model M when M occurs in either its session-level ``models``
    list or any child message's ``model``. Repetition within one session counts
    once. Cursor sessions use transcript-mtime last activity for windowing.
    """
    start, end = parse_window(since, until, default_days=30)
    names = _active_harnesses(con, harnesses)
    active = set(names)
    rows = con.execute(
        f"SELECT s.harness, s.session_id, s.models, m.model "
        "FROM sessions s LEFT JOIN messages m "
        "ON m.harness = s.harness AND m.session_id = s.session_id "
        f"WHERE NOT s.is_subagent AND {ACTIVITY_TIME_SQL} IS NOT NULL "
        f"AND {ACTIVITY_TIME_SQL} >= ? AND {ACTIVITY_TIME_SQL} < ?",
        [start, end],
    ).fetchall()
    per_session: dict[tuple[str, str], set[str]] = {}
    for harness, session_id, session_models, message_model in rows:
        if not _is_selected(harness, active):
            continue
        used = per_session.setdefault((harness, session_id), set())
        if session_models:
            used.update(model for model in session_models if model)
        if message_model:
            used.add(message_model)

    counts: dict[str, dict[str, int]] = {}
    for (harness, _session_id), used in per_session.items():
        for model in used:
            per_harness = counts.setdefault(model, {})
            per_harness[harness] = per_harness.get(harness, 0) + 1

    ranked = sorted(
        counts,
        key=lambda model: (-sum(counts[model].values()), model),
    )
    return {
        "models": ranked,
        "sessions": {
            name: [counts[model].get(name, 0) for model in ranked] for name in names
        },
    }


def efficiency(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return efficiency buckets using transcript-mtime activity for Cursor."""
    start, end = parse_window(since, until, default_days=30)
    names = _active_harnesses(con, harnesses)
    active = set(names)
    session_rows = [
        row for row in _session_rows(con, start, end) if _is_selected(row[0], active)
    ]
    message_counts = {
        (harness, session_id): count
        for harness, session_id, _project, _activity, count in session_rows
    }

    def _session_bucket(count: int) -> int:
        if count <= 2:
            return 0
        if count <= 10:
            return 1
        if count <= 40:
            return 2
        return 3

    session_buckets = {name: [0] * len(EFFICIENCY_BUCKETS) for name in names}
    for (harness, _session_id), count in message_counts.items():
        session_buckets[harness][_session_bucket(count)] += 1

    prompt_sums = {name: [0] * len(FIRST_PROMPT_BUCKETS) for name in names}
    prompt_counts = {name: [0] * len(FIRST_PROMPT_BUCKETS) for name in names}
    prompt_rows = con.execute(
        "SELECT harness, session_id, length(text) FROM messages "
        "WHERE ordinal = 0 AND role = 'user' AND text IS NOT NULL"
    ).fetchall()
    for harness, session_id, length in prompt_rows:
        message_count = message_counts.get((harness, session_id))
        if message_count is None:
            continue
        bucket = 0 if length < 100 else 1 if length <= 500 else 2
        prompt_sums[harness][bucket] += message_count
        prompt_counts[harness][bucket] += 1

    averages = {
        name: [
            prompt_sums[name][index] / count if count else 0.0
            for index, count in enumerate(prompt_counts[name])
        ]
        for name in names
    }
    return {
        "buckets": list(EFFICIENCY_BUCKETS),
        "sessions": session_buckets,
        "first_prompt": {
            "labels": list(FIRST_PROMPT_BUCKETS),
            "avg_msgs": averages,
            "n": prompt_counts,
        },
    }


def sessions(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return newest sessions; Cursor ``started`` is last transcript activity."""
    names = _active_harnesses(con, harnesses)
    if not names or limit <= 0:
        return []
    capped_limit = min(limit, 500)
    clauses = [
        "NOT s.is_subagent",
        f"{ACTIVITY_TIME_SQL} IS NOT NULL",
        f"s.harness IN ({', '.join('?' for _ in names)})",
    ]
    params: list[Any] = list(names)
    if since is not None:
        clauses.append(f"{ACTIVITY_TIME_SQL} >= ?")
        params.append(since)
    if until is not None:
        clauses.append(f"{ACTIVITY_TIME_SQL} < ?")
        params.append(until)
    params.append(capped_limit)

    rows = con.execute(
        "WITH recent AS ("
        f"SELECT s.*, {ACTIVITY_TIME_SQL} AS activity FROM sessions s "
        f"WHERE {' AND '.join(clauses)} "
        "ORDER BY activity DESC, s.harness, s.session_id LIMIT ?"
        ") "
        "SELECT r.harness, r.session_id, r.cwd, r.project_id, r.models, "
        "r.activity, m.ordinal, m.role, m.text, m.model "
        "FROM recent r LEFT JOIN messages m "
        "ON m.harness = r.harness AND m.session_id = r.session_id "
        "ORDER BY r.activity DESC, r.harness, r.session_id, m.ordinal",
        params,
    ).fetchall()

    ordered: dict[tuple[str, str], dict[str, Any]] = {}
    model_counts: dict[tuple[str, str], Counter[str]] = {}
    session_models: dict[tuple[str, str], list[str]] = {}
    for (
        harness,
        session_id,
        cwd,
        project_id,
        models_used,
        activity,
        ordinal,
        role,
        text,
        message_model,
    ) in rows:
        key = (harness, session_id)
        ordered.setdefault(
            key,
            {
                "started": activity.isoformat(),
                "harness": harness,
                "project_name": project_display_name(cwd, project_id),
                "project_id": project_id,
                "msgs": 0,
                "model": None,
                "prompt": "",
            },
        )
        session_models[key] = list(models_used or [])
        counts = model_counts.setdefault(key, Counter())
        if ordinal is not None:
            ordered[key]["msgs"] += 1
            if ordinal == 0 and role == "user" and text is not None:
                ordered[key]["prompt"] = truncate_cell(text, "snippet")
            if message_model:
                counts[message_model] += 1

    for key, record in ordered.items():
        counts = model_counts[key]
        if counts:
            record["model"] = sorted(counts, key=lambda name: (-counts[name], name))[0]
        elif session_models[key]:
            record["model"] = session_models[key][0]
    return list(ordered.values())


def wrapped(
    con: duckdb.DuckDBPyConnection,
    harnesses: Sequence[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Return all-time recap rollups, ignoring filters by design.

    Pre-0004 rows not yet re-ingested can lack any activity time. They still
    count toward all-time totals but cannot honestly contribute to span, streak,
    or peak-hour fields until ingest captures ``source_mtime``.
    """
    rows = con.execute(
        f"SELECT s.harness, s.session_id, s.cwd, s.project_id, "
        f"{ACTIVITY_TIME_SQL}, count(m.message_id) "
        "FROM sessions s LEFT JOIN messages m "
        "ON m.harness = s.harness AND m.session_id = s.session_id "
        "WHERE NOT s.is_subagent "
        "GROUP BY s.harness, s.session_id, s.cwd, s.project_id, "
        "s.started_at, s.source_mtime"
    ).fetchall()
    total_sessions = len(rows)
    total_messages = sum(row[5] for row in rows)
    dated = [row for row in rows if row[4] is not None]
    activities = [row[4] for row in dated]
    projects_used = {row[3] for row in rows if row[3] is not None}

    harness_counts = Counter(row[0] for row in rows)
    if harness_counts:
        busiest_name = sorted(
            harness_counts, key=lambda name: (-harness_counts[name], name)
        )[0]
        busiest = {
            "name": busiest_name,
            "pct": round(harness_counts[busiest_name] * 100 / total_sessions, 1),
        }
    else:
        busiest = {"name": None, "pct": 0.0}

    active_days = sorted({activity.date() for activity in activities})
    best_start = best_end = None
    best_length = current_length = 0
    current_start = None
    previous = None
    for day in active_days:
        if previous is not None and day == previous + timedelta(days=1):
            current_length += 1
        else:
            current_start = day
            current_length = 1
        if current_length > best_length:
            best_length = current_length
            best_start = current_start
            best_end = day
        previous = day

    marathon = None
    if rows:
        row = sorted(rows, key=lambda item: (-item[5], item[0], item[1]))[0]
        marathon = {
            "messages": row[5],
            "project_name": project_display_name(row[2], row[3]),
            "project_id": row[3],
            "harness": row[0],
        }

    hour_counts = Counter(activity.hour for activity in activities)
    if hour_counts:
        peak_hour = sorted(hour_counts, key=lambda hour: (-hour_counts[hour], hour))[0]
        peak = {"hour": peak_hour, "count": hour_counts[peak_hour]}
    else:
        peak = {"hour": None, "count": 0}

    tool_row = con.execute(
        "SELECT t.tool_name, count(*) AS calls "
        "FROM tool_calls t JOIN sessions s "
        "ON s.harness = t.harness AND s.session_id = t.session_id "
        "WHERE NOT s.is_subagent "
        "GROUP BY t.tool_name ORDER BY calls DESC, t.tool_name LIMIT 1"
    ).fetchone()
    top_tool = (
        {"name": tool_row[0], "calls": tool_row[1]}
        if tool_row is not None
        else {"name": None, "calls": 0}
    )

    if activities:
        first_day = min(activities).date()
        last_day = max(activities).date()
        span = {
            "start": first_day.isoformat(),
            "end": last_day.isoformat(),
            "days": (last_day - first_day).days + 1,
        }
    else:
        span = {"start": None, "end": None, "days": 0}

    return {
        "totals": {
            "sessions": total_sessions,
            "messages": total_messages,
            "span": span,
        },
        "distinct_projects": len(projects_used),
        "busiest_harness": busiest,
        "best_streak": {
            "days": best_length,
            "start": best_start.isoformat() if best_start else None,
            "end": best_end.isoformat() if best_end else None,
        },
        "marathon_session": marathon,
        "peak_hour": peak,
        "top_tool": top_tool,
    }


ENDPOINTS = {
    "overview": overview,
    "trends": trends,
    "projects": projects,
    "tools": tools,
    "models": models,
    "efficiency": efficiency,
    "sessions": sessions,
    "wrapped": wrapped,
}
