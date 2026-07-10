import test from "node:test";
import assert from "node:assert/strict";

import {
  buildDailyPanel,
  buildEfficiencyPanel,
  buildFirstPromptPanel,
  buildModelsPanel,
  buildProjectsPanel,
  buildToolsPanel,
  buildWrappedPanel,
  buildWriteReadPanel,
  chartHeight,
  closePanelHelp,
  deriveHarnessBreakdown,
  deriveOverviewCards,
  displayHarness,
  formatDelta,
  harnessColors,
  PANEL_HELP,
  panelRangeLabels,
  projectHoverTitle,
  resolveWindowBounds,
  sortedHarnesses,
  sumAligned,
  summarizeChartPanel,
  togglePanelHelp,
  tooltipTitleFromLabelTitles,
  transitionViewState,
  weightedSeries,
  writeShare,
} from "../src/stockroom/dashboard/static/dashboard-core.mjs";

const COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#f43f5e",
  "#06b6d4",
  "#8b5cf6",
  "#ec4899",
  "#84cc16",
];

const selected = ["claude-code", "cursor"];
const colors = {
  "claude-code": COLORS[0],
  cursor: COLORS[1],
};

function assertDataset(panel, label, data) {
  const dataset = panel.datasets.find((item) => item.label === label);
  assert.ok(dataset, `missing ${label} dataset`);
  assert.deepEqual(dataset.data, data);
}

test("sorts arbitrary harnesses and cycles stable positional colors", () => {
  const raw = ["zeta", "alpha", "alpha", "nine", "beta", "eta", "gamma", "iota", "delta", "theta"];
  assert.deepEqual(sortedHarnesses(raw), [
    "alpha",
    "beta",
    "delta",
    "eta",
    "gamma",
    "iota",
    "nine",
    "theta",
    "zeta",
  ]);
  assert.deepEqual(harnessColors(raw), {
    alpha: COLORS[0],
    beta: COLORS[1],
    delta: COLORS[2],
    eta: COLORS[3],
    gamma: COLORS[4],
    iota: COLORS[5],
    nine: COLORS[6],
    theta: COLORS[7],
    zeta: COLORS[0],
  });
});

test("derives generic display labels from raw harness keys", () => {
  assert.equal(displayHarness("claude-code"), "Claude Code");
  assert.equal(displayHarness("cursor_cli"), "Cursor Cli");
  assert.equal(displayHarness("  future--harness  "), "Future Harness");
  assert.equal(displayHarness(null), "Unknown");
});

test("aggregates selected aligned series without mutating inputs", () => {
  const source = {
    cursor: [1, "2", null],
    "claude-code": [3, 4],
    ignored: [100, 100, 100],
  };
  const before = structuredClone(source);
  assert.deepEqual(sumAligned(source, selected, 4), [4, 6, 0, 0]);
  assert.deepEqual(source, before);
});

test("computes weighted averages with zero-observation guards", () => {
  const averages = { cursor: [10, 99], "claude-code": [4, 2] };
  const counts = { cursor: [1, 0], "claude-code": [3, 0] };
  assert.deepEqual(weightedSeries(averages, counts, selected), [5.5, 0]);
});

test("derives mode-independent overview cards and selected deltas", () => {
  const overview = {
    distinct_projects: 2,
    prev_distinct_projects: 1,
    per_harness: {
      cursor: {
        sessions: 2,
        messages: 6,
        projects: 2,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 1,
      },
      "claude-code": {
        sessions: 1,
        messages: 3,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 2,
        prev_projects: 0,
      },
    },
  };
  assert.deepEqual(deriveOverviewCards(overview, selected), [
    {
      key: "sessions",
      label: "Sessions",
      value: 3,
      delta: { text: "+200%", trend: "up" },
    },
    {
      key: "messages",
      label: "Messages",
      value: 9,
      delta: { text: "+125%", trend: "up" },
    },
    {
      key: "projects",
      label: "Projects",
      value: 2,
      delta: { text: "+100%", trend: "up" },
    },
    {
      key: "average",
      label: "Avg Msgs / Session",
      value: 3,
      delta: { text: "-25%", trend: "down" },
    },
  ]);
  assert.equal(deriveOverviewCards({ per_harness: {} }, [])[3].value, 0);
});

test("projects delta uses prev_distinct_projects not summed prev_projects", () => {
  const overview = {
    distinct_projects: 2,
    prev_distinct_projects: 2,
    per_harness: {
      cursor: {
        sessions: 1,
        messages: 2,
        projects: 1,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 2,
      },
      "claude-code": {
        sessions: 1,
        messages: 2,
        projects: 1,
        prev_sessions: 1,
        prev_messages: 2,
        prev_projects: 2,
      },
    },
  };
  const prevSum =
    overview.per_harness.cursor.prev_projects +
    overview.per_harness["claude-code"].prev_projects;
  assert.ok(prevSum > overview.prev_distinct_projects);
  const projects = deriveOverviewCards(overview, selected).find(
    (card) => card.key === "projects",
  );
  assert.deepEqual(projects, {
    key: "projects",
    label: "Projects",
    value: 2,
    delta: { text: "No change", trend: "neutral" },
  });
});

test("missing prev_distinct_projects degrades through formatDelta guards", () => {
  const overview = {
    distinct_projects: 2,
    per_harness: {
      cursor: {
        sessions: 1,
        messages: 1,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 0,
        prev_projects: 5,
      },
      "claude-code": {
        sessions: 1,
        messages: 1,
        projects: 1,
        prev_sessions: 0,
        prev_messages: 0,
        prev_projects: 5,
      },
    },
  };
  const projects = deriveOverviewCards(overview, selected).find(
    (card) => card.key === "projects",
  );
  assert.deepEqual(projects.delta, { text: "New", trend: "up" });
  assert.deepEqual(
    deriveOverviewCards({ distinct_projects: 0, prev_distinct_projects: null }, [])
      .find((card) => card.key === "projects").delta,
    { text: "No change", trend: "neutral" },
  );
});

test("derives per-harness KPI breakdown proportions", () => {
  const overview = {
    per_harness: {
      cursor: { sessions: 3, messages: 9, projects: 2 },
      "claude-code": { sessions: 1, messages: 2, projects: 1 },
    },
  };
  assert.deepEqual(deriveHarnessBreakdown(overview, selected, "sessions"), [
    {
      harness: "claude-code",
      label: "Claude Code",
      value: 1,
      share: 25,
    },
    { harness: "cursor", label: "Cursor", value: 3, share: 75 },
  ]);
  assert.deepEqual(deriveHarnessBreakdown(overview, selected, "average"), [
    {
      harness: "claude-code",
      label: "Claude Code",
      value: 2,
      share: 40,
    },
    { harness: "cursor", label: "Cursor", value: 3, share: 60 },
  ]);
  assert.deepEqual(
    deriveHarnessBreakdown({ per_harness: { cursor: {} } }, ["cursor"], "messages"),
    [{ harness: "cursor", label: "Cursor", value: 0, share: 0 }],
  );
});

test("formats percentage deltas including new and neutral values", () => {
  assert.deepEqual(formatDelta(125, 100), { text: "+25%", trend: "up" });
  assert.deepEqual(formatDelta(80, 100), { text: "-20%", trend: "down" });
  assert.deepEqual(formatDelta(2, 0), { text: "New", trend: "up" });
  assert.deepEqual(formatDelta(0, 0), { text: "No change", trend: "neutral" });
  assert.deepEqual(formatDelta(null, "bad"), { text: "No change", trend: "neutral" });
});

test("derives deterministic chart heights from label counts", () => {
  assert.equal(chartHeight(0), 240);
  assert.equal(chartHeight(3), 240);
  assert.equal(chartHeight(10), 340);
  assert.equal(chartHeight("bad"), 240);
});

test("defaults discovered harnesses and rejects an empty selection", () => {
  const initial = {
    harnesses: [],
    selected: [],
    mode: "aggregate",
    dateRange: "default",
    window: null,
  };
  const discovered = transitionViewState(initial, {
    type: "discover",
    harnesses: ["cursor", "claude-code", "cursor"],
  });
  assert.deepEqual(discovered, {
    state: {
      harnesses: ["claude-code", "cursor"],
      selected: ["claude-code", "cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    effect: "render",
  });
  const refused = transitionViewState(
    {
      harnesses: ["cursor"],
      selected: ["cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    { type: "toggle", harness: "cursor" },
  );
  assert.deepEqual(refused, {
    state: {
      harnesses: ["cursor"],
      selected: ["cursor"],
      mode: "aggregate",
      dateRange: "default",
      window: null,
    },
    effect: "none",
  });
});

test("distinguishes mode redraws from selection refetches", () => {
  const state = {
    harnesses: ["claude-code", "cursor"],
    selected: ["claude-code", "cursor"],
    mode: "aggregate",
    dateRange: "default",
    window: null,
  };
  assert.equal(
    transitionViewState(state, { type: "mode", mode: "compare" }).effect,
    "render",
  );
  assert.equal(
    transitionViewState(state, { type: "toggle", harness: "cursor" }).effect,
    "refetch",
  );
  assert.equal(
    transitionViewState(state, { type: "mode", mode: "aggregate" }).effect,
    "none",
  );
});

test("date-range changes refetch and identical presets are no-ops", () => {
  const now = new Date("2026-07-10T18:00:00.000Z");
  const state = {
    harnesses: ["cursor"],
    selected: ["cursor"],
    mode: "aggregate",
    dateRange: "default",
    window: null,
  };
  const changed = transitionViewState(state, {
    type: "daterange",
    preset: "7d",
    now,
  });
  assert.equal(changed.effect, "refetch");
  assert.equal(changed.state.dateRange, "7d");
  assert.deepEqual(changed.state.window, resolveWindowBounds("7d", now));
  assert.equal(changed.state.mode, "aggregate");

  const same = transitionViewState(changed.state, {
    type: "daterange",
    preset: "7d",
    now,
  });
  assert.equal(same.effect, "none");
  assert.equal(same.state.dateRange, "7d");

  const backToDefault = transitionViewState(changed.state, {
    type: "daterange",
    preset: "default",
    now,
  });
  assert.equal(backToDefault.effect, "refetch");
  assert.equal(backToDefault.state.dateRange, "default");
  assert.equal(backToDefault.state.window, null);

  const modeStillRenderOnly = transitionViewState(changed.state, {
    type: "mode",
    mode: "compare",
  });
  assert.equal(modeStillRenderOnly.effect, "render");
  assert.equal(modeStillRenderOnly.state.dateRange, "7d");
  assert.deepEqual(modeStillRenderOnly.state.window, changed.state.window);
});

test("resolveWindowBounds omits default and computes ISO since/until for presets", () => {
  const now = new Date("2026-07-10T18:00:00.000Z");
  assert.equal(resolveWindowBounds("default", now), null);
  assert.equal(resolveWindowBounds("nope", now), null);

  const week = resolveWindowBounds("7d", now);
  assert.equal(week.until, "2026-07-10T18:00:00.000Z");
  assert.equal(week.since, "2026-07-03T18:00:00.000Z");

  const year = resolveWindowBounds("1y", now);
  assert.equal(year.until, "2026-07-10T18:00:00.000Z");
  assert.equal(year.since, "2025-07-10T18:00:00.000Z");

  assert.equal(resolveWindowBounds("30d", now).since, "2026-06-10T18:00:00.000Z");
  assert.equal(resolveWindowBounds("90d", now).since, "2026-04-11T18:00:00.000Z");
});

test("panelRangeLabels keep per-panel defaults and share preset window copy", () => {
  const defaults = panelRangeLabels("default");
  assert.equal(defaults.overviewAria, "Thirty-day overview");
  assert.equal(defaults.daily, "Last 14 days");
  assert.equal(defaults.projects, "Last 30 days");
  assert.equal(defaults.tools, "Last 30 days");
  assert.equal(defaults.writeRead, "Last 12 weeks");
  assert.equal(defaults.efficiency, "Last 30 days");
  assert.equal(defaults.models, "Last 30 days");
  assert.equal(
    defaults.firstPrompt,
    "Average session length by prompt detail · 30 days",
  );

  const week = panelRangeLabels("7d");
  assert.equal(week.overviewAria, "Last 7 days overview");
  assert.equal(week.daily, "Last 7 days");
  assert.equal(week.projects, "Last 7 days");
  assert.equal(week.tools, "Last 7 days");
  assert.equal(week.writeRead, "Last 7 days");
  assert.equal(week.efficiency, "Last 7 days");
  assert.equal(week.models, "Last 7 days");
  assert.equal(
    week.firstPrompt,
    "Average session length by prompt detail · Last 7 days",
  );

  const year = panelRangeLabels("1y");
  assert.equal(year.overviewAria, "Last 1 year overview");
  assert.equal(year.daily, "Last 1 year");
  assert.equal(
    year.firstPrompt,
    "Average session length by prompt detail · Last 1 year",
  );
});

test("builds aggregate and compare daily activity models", () => {
  const payload = {
    labels: ["2026-01-01", "2026-01-02"],
    sessions: { cursor: [1, 2], "claude-code": [3, 0] },
  };
  const aggregate = buildDailyPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "bar");
  assert.equal(aggregate.stacked, false);
  assertDataset(aggregate, "Sessions", [4, 2]);
  const compare = buildDailyPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Claude Code", [3, 0]);
  assertDataset(compare, "Cursor", [1, 2]);
});

test("builds aggregate and compare project models", () => {
  const payload = {
    projects: ["stockroom", "other"],
    sessions: { cursor: [2, 0], "claude-code": [1, 4] },
  };
  const aggregate = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.indexAxis, "y");
  assertDataset(aggregate, "Sessions", [3, 4]);
  const compare = buildProjectsPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Cursor", [2, 0]);
});

test("projectHoverTitle returns id only when display differs", () => {
  assert.equal(projectHoverTitle("stockroom", "home-me-stockroom"), "home-me-stockroom");
  assert.equal(projectHoverTitle("slug", "slug"), null);
  assert.equal(projectHoverTitle("slug", null), null);
  assert.equal(projectHoverTitle(null, "slug"), "slug");
});

test("buildProjectsPanel prefers friendly labels and sets labelTitles", () => {
  const payload = {
    projects: ["home-me-stockroom", "other-slug"],
    labels: ["stockroom", "other-slug"],
    sessions: { cursor: [2, 1], "claude-code": [0, 0] },
  };
  const panel = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.deepEqual(panel.labels, ["stockroom", "other-slug"]);
  assert.deepEqual(panel.labelTitles, ["home-me-stockroom", null]);
  assertDataset(panel, "Sessions", [2, 1]);
});

test("buildProjectsPanel falls back to projects when labels missing", () => {
  const payload = {
    projects: ["only-id"],
    sessions: { cursor: [1], "claude-code": [0] },
  };
  const panel = buildProjectsPanel(payload, selected, "aggregate", colors);
  assert.deepEqual(panel.labels, ["only-id"]);
  assert.deepEqual(panel.labelTitles, [null]);
});

test("tooltipTitleFromLabelTitles surfaces slug when present", () => {
  assert.equal(
    tooltipTitleFromLabelTitles(["home-me-stockroom", null], 0, "stockroom"),
    "home-me-stockroom",
  );
  assert.equal(tooltipTitleFromLabelTitles(["home-me-stockroom", null], 1, "other"), "other");
  assert.equal(tooltipTitleFromLabelTitles(undefined, 0, "friendly"), "friendly");
});

test("PANEL_HELP documents efficiency and first-prompt buckets", () => {
  assert.match(PANEL_HELP.efficiency, /abandoned/i);
  assert.match(PANEL_HELP.efficiency, /short/i);
  assert.match(PANEL_HELP.efficiency, /medium/i);
  assert.match(PANEL_HELP.efficiency, /long/i);
  assert.match(PANEL_HELP.efficiency, /≤\s*2|<=\s*2|1–2|1-2|0–2|0-2/i);
  assert.match(PANEL_HELP["first-prompt"], /short/i);
  assert.match(PANEL_HELP["first-prompt"], /medium/i);
  assert.match(PANEL_HELP["first-prompt"], /detailed/i);
  assert.match(PANEL_HELP["first-prompt"], /average|avg/i);
  assert.match(PANEL_HELP["first-prompt"], /100|500/);
});

test("togglePanelHelp opens one, re-toggles closed, and switches panels", () => {
  assert.equal(togglePanelHelp(null, "efficiency"), "efficiency");
  assert.equal(togglePanelHelp("efficiency", "efficiency"), null);
  assert.equal(togglePanelHelp("efficiency", "first-prompt"), "first-prompt");
  assert.equal(closePanelHelp(), null);
});

test("buildWrappedPanel marathon exposes subtitleTitle when name differs from id", () => {
  const cells = buildWrappedPanel({
    totals: { sessions: 1, messages: 5, span: { start: null, end: null, days: 0 } },
    distinct_projects: 1,
    busiest_harness: { name: null, pct: 0 },
    best_streak: { days: 0, start: null, end: null },
    marathon_session: {
      messages: 5,
      project_name: "stockroom",
      project_id: "home-me-stockroom",
      harness: "cursor",
    },
    peak_hour: { hour: null, count: 0 },
    top_tool: { name: null, calls: 0 },
  });
  const marathon = cells.find((cell) => cell.key === "marathon");
  assert.equal(marathon.subtitleTitle, "home-me-stockroom");
  const same = buildWrappedPanel({
    totals: { sessions: 0, messages: 0, span: {} },
    distinct_projects: 0,
    busiest_harness: {},
    best_streak: {},
    marathon_session: {
      messages: 1,
      project_name: "p1",
      project_id: "p1",
      harness: "cursor",
    },
    peak_hour: {},
    top_tool: {},
  }).find((cell) => cell.key === "marathon");
  assert.equal(same.subtitleTitle, null);
});

test("builds aggregate doughnut and compare tool models", () => {
  const payload = {
    tools: ["Read", "Write"],
    calls: { cursor: [3, 1], "claude-code": [2, 4] },
  };
  const aggregate = buildToolsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.kind, "doughnut");
  assertDataset(aggregate, "Calls", [5, 5]);
  const compare = buildToolsPanel(payload, selected, "compare", colors);
  assert.equal(compare.kind, "bar");
  assert.equal(compare.indexAxis, "y");
  assertDataset(compare, "Claude Code", [2, 4]);
});

test("writeShare returns zero on zero denominator and finite ratios otherwise", () => {
  assert.equal(writeShare(0, 0), 0);
  assert.equal(writeShare(0, 4), 0);
  assert.equal(writeShare(3, 1), 0.75);
  assert.equal(writeShare(2, 2), 0.5);
});

test("builds aggregate write-share ratio line with zeros for idle buckets", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12", "2026-01-19"],
    writes: { cursor: [2, 0, 0], "claude-code": [1, 0, 0] },
    reads: { cursor: [4, 0, 5], "claude-code": [0, 0, 0] },
  };
  const panel = buildWriteReadPanel(payload, selected, "aggregate", colors);
  assert.equal(panel.kind, "line");
  assert.equal(panel.stacked, false);
  assert.equal(panel.empty, false);
  assert.equal(panel.yMax, 1);
  assert.equal(panel.datasets.length, 1);
  // week0: (2+1)/(2+1+4+0)=3/7; week1: 0/0 → 0; week2: 0/(0+5)=0
  assertDataset(panel, "Write share", [3 / 7, 0, 0]);
});

test("builds compare write-share ratio lines per harness", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12"],
    writes: { cursor: [2, 0], "claude-code": [1, 0] },
    reads: { cursor: [2, 0], "claude-code": [3, 4] },
  };
  const panel = buildWriteReadPanel(payload, selected, "compare", colors);
  assert.equal(panel.datasets.length, 2);
  assert.equal(panel.empty, false);
  assert.equal(panel.yMax, 1);
  // orderedSelection sorts: claude-code, cursor
  assertDataset(panel, "Claude Code", [0.25, 0]);
  assertDataset(panel, "Cursor", [0.5, 0]);
  assert.equal(panel.datasets[0].borderColor, colors["claude-code"]);
  assert.equal(panel.datasets[1].borderColor, colors.cursor);
});

test("marks write-read panel empty when every bucket has no tool activity", () => {
  const payload = {
    labels: ["2026-01-05", "2026-01-12"],
    writes: { cursor: [0, 0], "claude-code": [0, 0] },
    reads: { cursor: [0, 0], "claude-code": [0, 0] },
  };
  const panel = buildWriteReadPanel(payload, selected, "aggregate", colors);
  assert.equal(panel.empty, true);
  assert.deepEqual(panel.datasets[0].data, [0, 0]);
});

test("builds aggregate and compare efficiency models", () => {
  const payload = {
    buckets: ["abandoned", "short"],
    sessions: { cursor: [1, 2], "claude-code": [3, 4] },
  };
  const aggregate = buildEfficiencyPanel(payload, selected, "aggregate", colors);
  assertDataset(aggregate, "Sessions", [4, 6]);
  const compare = buildEfficiencyPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Cursor", [1, 2]);
});

test("builds all-model aggregate and compare models", () => {
  const payload = {
    models: Array.from({ length: 10 }, (_, index) => `model-${index}`),
    sessions: {
      cursor: Array(10).fill(1),
      "claude-code": Array(10).fill(2),
    },
  };
  const aggregate = buildModelsPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.labels.length, 10);
  assert.equal(aggregate.height, 340);
  assertDataset(aggregate, "Sessions", Array(10).fill(3));
  const compare = buildModelsPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, true);
  assertDataset(compare, "Claude Code", Array(10).fill(2));
});

test("builds weighted aggregate and grouped compare first-prompt models", () => {
  const payload = {
    labels: ["short", "detailed"],
    avg_msgs: { cursor: [10, 8], "claude-code": [4, 2] },
    n: { cursor: [1, 0], "claude-code": [3, 2] },
  };
  const aggregate = buildFirstPromptPanel(payload, selected, "aggregate", colors);
  assert.equal(aggregate.stacked, false);
  assertDataset(aggregate, "Avg messages", [5.5, 2]);
  const compare = buildFirstPromptPanel(payload, selected, "compare", colors);
  assert.equal(compare.stacked, false);
  assertDataset(compare, "Cursor", [10, 8]);
  assertDataset(compare, "Claude Code", [4, 2]);
});

test("builds exactly eight factual wrapped cells with nullable fallbacks", () => {
  const payload = {
    totals: {
      sessions: 12,
      messages: 80,
      span: { start: "2026-01-01", end: "2026-01-05", days: 5 },
    },
    distinct_projects: 3,
    busiest_harness: { name: "claude-code", pct: 58.3 },
    best_streak: { days: 3, start: "2026-01-01", end: "2026-01-03" },
    marathon_session: {
      messages: 20,
      project_name: "stockroom",
      harness: "cursor",
    },
    peak_hour: { hour: 14, count: 4 },
    top_tool: { name: "ReadFile", calls: 30 },
  };
  const cells = buildWrappedPanel(payload);
  assert.equal(cells.length, 8);
  assert.deepEqual(cells.map((cell) => cell.label), [
    "Total Sessions",
    "Total Messages",
    "Distinct Projects",
    "Busiest Harness",
    "Best Streak",
    "Marathon Session",
    "Peak Hour",
    "Top Tool",
  ]);
  assert.equal(cells[3].value, "Claude Code");
  assert.equal(cells[7].value, "ReadFile");
  const empty = buildWrappedPanel({});
  assert.equal(empty.length, 8);
  assert.equal(empty[0].value, "0");
  assert.equal(empty[3].value, "—");
  assert.equal(empty[5].value, "—");
  assert.equal(
    buildWrappedPanel({ peak_hour: { hour: null, count: 0 } })[6].value,
    "—",
  );
});

test("formats wrapped span and streak dates with short local dates", () => {
  const formatter = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const start = formatter.format(new Date("2026-01-01T00:00:00"));
  const end = formatter.format(new Date("2026-01-05T00:00:00"));
  const streakEnd = formatter.format(new Date("2026-01-03T00:00:00"));
  const cells = buildWrappedPanel({
    totals: {
      sessions: 1,
      messages: 1,
      span: { start: "2026-01-01", end: "2026-01-05", days: 5 },
    },
    best_streak: { days: 3, start: "2026-01-01", end: "2026-01-03" },
  });
  assert.equal(cells[0].subtitle, `5 days · ${start} – ${end}`);
  assert.equal(cells[4].subtitle, `${start} – ${streakEnd}`);
});

test("summarizes aggregate panel measured content", () => {
  const model = {
    kind: "bar",
    labels: ["stockroom", "other"],
    datasets: [{ label: "Sessions", data: [3, 4] }],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Sessions by project", "aggregate", model),
    "Sessions by project. Aggregate view. Sessions: stockroom 3, other 4.",
  );
});

test("summarizes compare panel per-harness measured content", () => {
  const model = {
    kind: "bar",
    labels: ["stockroom", "other"],
    datasets: [
      { label: "Claude Code", data: [1, 4] },
      { label: "Cursor", data: [2, 0] },
    ],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Sessions by project", "compare", model),
    "Sessions by project. Compare view. Claude Code: stockroom 1, other 4; Cursor: stockroom 2, other 0.",
  );
});

test("summarizes empty panel without inventing values", () => {
  const model = {
    kind: "bar",
    labels: ["a", "b"],
    datasets: [{ label: "Sessions", data: [0, 0] }],
    empty: true,
  };
  assert.equal(
    summarizeChartPanel("Daily session activity", "aggregate", model),
    "Daily session activity. Aggregate view. No data in this period.",
  );
});

test("summarizes write-share ratio panel including idle zeros", () => {
  const model = {
    kind: "line",
    labels: ["2026-01-05", "2026-01-12"],
    datasets: [{ label: "Write share", data: [0.5, 0] }],
    empty: false,
  };
  assert.equal(
    summarizeChartPanel("Weekly write share", "aggregate", model),
    "Weekly write share. Aggregate view. Write share: 2026-01-05 0.5, 2026-01-12 0.",
  );
});

test("summarizeChartPanel leaves the input model unchanged", () => {
  const model = {
    kind: "bar",
    labels: ["one"],
    datasets: [{ label: "Sessions", data: [2] }],
    empty: false,
  };
  const before = structuredClone(model);
  summarizeChartPanel("Sessions by project", "aggregate", model);
  assert.deepEqual(model, before);
});

test("keeps every pure transformation input unchanged", () => {
  const payload = {
    projects: ["one"],
    sessions: { cursor: [1], "claude-code": [2] },
  };
  const before = structuredClone(payload);
  buildProjectsPanel(payload, selected, "compare", colors);
  deriveOverviewCards(
    {
      distinct_projects: 1,
      prev_distinct_projects: 0,
      per_harness: {
        cursor: {
          sessions: 1,
          messages: 1,
          projects: 1,
          prev_sessions: 0,
          prev_messages: 0,
          prev_projects: 0,
        },
      },
    },
    ["cursor"],
  );
  assert.deepEqual(payload, before);
});
